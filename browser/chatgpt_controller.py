from __future__ import annotations

import asyncio
import logging
import re

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from browser.chrome_session import ChromeSession
from browser.response_reader import ResponseReader
from browser.ui_selectors import (
    CHATGPT_MAIN_INPUT_SELECTORS,
    NEW_CHAT_BUTTON_NAMES,
    SEND_BUTTON_SELECTORS,
    STOP_BUTTON_NAMES,
)


logger = logging.getLogger(__name__)


class ChatGPTController:
    def __init__(self, chrome: ChromeSession, chatgpt_url: str) -> None:
        self.chrome = chrome
        self.chatgpt_url = chatgpt_url
        self.page: Page | None = None

    async def start_browser(self) -> Page:
        self.page = await self.chrome.start_browser()
        return self.page

    async def open_chatgpt(self, chat_url: str | None = None) -> None:
        page = await self.start_browser()
        target_url = chat_url or self.chatgpt_url
        if not self._same_page(page.url, target_url):
            await page.goto(target_url, wait_until="commit", timeout=30000)
            await self._find_prompt_input(timeout_ms=8000)
        await self._ensure_logged_in_hint()

    async def _ensure_logged_in_hint(self) -> None:
        page = self._page()
        login = page.get_by_role("button", name="Log in")
        try:
            if await login.count():
                logger.warning("ChatGPT login button detected. Log in manually in the opened browser.")
        except Exception:
            logger.debug("Could not detect ChatGPT login status.", exc_info=True)

    async def create_new_chat(self) -> None:
        page = self._page()
        for name in NEW_CHAT_BUTTON_NAMES:
            button = page.get_by_role("button", name=name)
            try:
                if await button.count():
                    await button.first.click(timeout=5000)
                    await self._find_prompt_input(timeout_ms=3000)
                    return
            except Exception:
                logger.debug("New chat button failed: %s", name, exc_info=True)
        await page.goto(self.chatgpt_url, wait_until="commit", timeout=30000)
        await self._find_prompt_input(timeout_ms=3000)

    async def send_prompt(self, prompt_text: str) -> None:
        page = self._page()
        input_box = await self._find_prompt_input(timeout_ms=1000)
        try:
            await input_box.click(timeout=3000)
            await input_box.fill(prompt_text, timeout=5000)
        except Exception:
            await input_box.click(timeout=3000)
            await page.keyboard.insert_text(prompt_text)
        for selector in SEND_BUTTON_SELECTORS:
            button = page.locator(selector).first
            try:
                if await button.count():
                    await button.click(timeout=1000)
                    return
            except Exception:
                logger.debug("Send button selector failed: %s", selector, exc_info=True)
        await page.keyboard.press("Enter")

    async def wait_for_response_complete(self) -> None:
        page = self._page()
        for name in STOP_BUTTON_NAMES:
            try:
                stop_button = page.get_by_role("button", name=name)
                if await stop_button.count():
                    await stop_button.first.wait_for(state="detached", timeout=180000)
                    return
            except PlaywrightTimeoutError:
                logger.warning("Timed out waiting for stop button to disappear.")
            except Exception:
                logger.debug("Stop button strategy failed: %s", name, exc_info=True)
        await ResponseReader(page).wait_until_stable()

    async def read_latest_response(self) -> str:
        return await ResponseReader(self._page()).latest_response_text()

    async def get_current_chat_url(self) -> str:
        return self._page().url

    async def rename_current_chat(self, new_name: str) -> None:
        page = self._page()
        await self._open_sidebar_if_available()

        if await self._open_current_conversation_menu():
            await self._click_rename_menu_item()
            await self._fill_rename_dialog(new_name)
            return

        if await self._open_any_conversation_menu():
            await self._click_rename_menu_item()
            await self._fill_rename_dialog(new_name)
            return

        raise RuntimeError("Could not find ChatGPT rename controls. Selectors may need updating.")

    async def close_browser(self) -> None:
        await self.chrome.close_browser()

    async def _find_prompt_input(self, timeout_ms: int = 1000):
        page = self._page()
        combined_selector = ", ".join(CHATGPT_MAIN_INPUT_SELECTORS)
        combined = page.locator(combined_selector).first
        try:
            await combined.wait_for(state="visible", timeout=timeout_ms)
            return combined
        except Exception:
            logger.debug("Combined prompt input selector failed.", exc_info=True)

        fallback_timeout = min(timeout_ms, 500)
        for selector in CHATGPT_MAIN_INPUT_SELECTORS:
            loc = page.locator(selector).first
            try:
                await loc.wait_for(state="visible", timeout=fallback_timeout)
                return loc
            except Exception:
                logger.debug("Prompt input selector failed: %s", selector, exc_info=True)
        raise RuntimeError("Could not find ChatGPT prompt input. Update browser/ui_selectors.py.")

    @staticmethod
    def _same_page(current_url: str, target_url: str) -> bool:
        current = current_url.rstrip("/")
        target = target_url.rstrip("/")
        if current == target:
            return True
        current_chat = ChatGPTController._conversation_id_from_url(current)
        target_chat = ChatGPTController._conversation_id_from_url(target)
        if target_chat:
            return bool(current_chat and current_chat == target_chat)
        return bool(current.startswith("https://chatgpt.com") and target == "https://chatgpt.com")

    async def _fill_rename_dialog(self, new_name: str) -> None:
        page = self._page()

        # The ChatGPT rename action usually focuses an inline title input.
        focused = await page.evaluate(
            """() => {
                const el = document.activeElement;
                if (!el) return "";
                const tag = el.tagName.toLowerCase();
                if (tag === "input" || tag === "textarea" || el.isContentEditable) return tag;
                return "";
            }"""
        )
        if focused:
            await page.keyboard.press("Control+A")
            await page.keyboard.insert_text(new_name)
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.5)
            return

        inputs = page.locator(
            'input[type="text"]:visible, input:not([type]):visible, [contenteditable="true"]:visible'
        )
        count = await inputs.count()
        for index in range(count - 1, -1, -1):
            box = inputs.nth(index)
            try:
                test_id = await box.get_attribute("data-testid", timeout=1000)
                aria = await box.get_attribute("aria-label", timeout=1000)
                if test_id == "prompt-textarea" or (aria and "message" in aria.lower()):
                    continue
                await box.click(timeout=3000)
                await box.fill(new_name, timeout=5000)
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.5)
                return
            except Exception:
                logger.debug("Rename input failed.", exc_info=True)
        raise RuntimeError("Could not fill ChatGPT rename dialog.")

    async def _open_sidebar_if_available(self) -> None:
        page = self._page()
        for name in ("Open sidebar", "Show sidebar", "Expand sidebar"):
            try:
                button = page.get_by_role("button", name=name)
                if await button.count():
                    await button.first.click(timeout=3000)
                    await asyncio.sleep(0.5)
                    return
            except Exception:
                logger.debug("Sidebar open button failed: %s", name, exc_info=True)

    async def _open_current_conversation_menu(self) -> bool:
        page = self._page()
        conversation_id = self._conversation_id_from_url(page.url)
        if not conversation_id:
            return False

        selectors = [
            f'a[href*="/c/{conversation_id}"]',
            f'a[href*="{conversation_id}"]',
        ]
        for selector in selectors:
            try:
                link = page.locator(selector).last
                if not await link.count():
                    continue
                await link.scroll_into_view_if_needed(timeout=5000)
                await link.hover(timeout=5000)
                container = link.locator(
                    "xpath=ancestor::*[self::li or self::div][.//a][1]"
                )
                menu_buttons = container.locator(
                    'button[aria-label*="Open conversation options"], '
                    'button[aria-label*="More"], '
                    'button:has-text("..."), '
                    'button:has-text("⋯")'
                )
                if await menu_buttons.count():
                    await menu_buttons.last.click(timeout=5000)
                    await asyncio.sleep(0.3)
                    return True
                clicked = await page.evaluate(
                    """(conversationId) => {
                        const link = [...document.querySelectorAll('a[href*="/c/"], a[href*="/chat/"]')]
                          .find((a) => a.href.includes(conversationId));
                        if (!link) return false;
                        const container = link.closest('li') || link.parentElement;
                        if (!container) return false;
                        const buttons = [...container.querySelectorAll('button')];
                        const menu = buttons.find((button) => {
                          const label = (button.getAttribute('aria-label') || '').toLowerCase();
                          return label.includes('conversation') || label.includes('more') || label.includes('options');
                        }) || buttons[buttons.length - 1];
                        if (!menu) return false;
                        menu.click();
                        return true;
                    }""",
                    conversation_id,
                )
                if clicked:
                    await asyncio.sleep(0.3)
                    return True
            except Exception:
                logger.debug("Current conversation menu strategy failed: %s", selector, exc_info=True)
        return False

    async def _open_any_conversation_menu(self) -> bool:
        page = self._page()
        selectors = [
            'button[aria-label*="Open conversation options"]',
            'button[aria-label*="More"]',
            '[data-testid="conversation-options-button"]',
        ]
        for selector in selectors:
            try:
                buttons = page.locator(selector)
                count = await buttons.count()
                if count:
                    await buttons.last.click(timeout=5000)
                    await asyncio.sleep(0.3)
                    return True
            except Exception:
                logger.debug("Any conversation menu strategy failed: %s", selector, exc_info=True)
        return False

    async def _click_rename_menu_item(self) -> None:
        page = self._page()
        candidates = [
            page.get_by_role("menuitem", name=re.compile(r"^rename$", re.IGNORECASE)),
            page.get_by_role("button", name=re.compile(r"^rename$", re.IGNORECASE)),
            page.get_by_text("Rename", exact=True),
        ]
        for candidate in candidates:
            try:
                if await candidate.count():
                    await candidate.first.click(timeout=5000)
                    await asyncio.sleep(0.3)
                    return
            except Exception:
                logger.debug("Rename menu item failed.", exc_info=True)
        raise RuntimeError("Could not click ChatGPT Rename menu item.")

    @staticmethod
    def _conversation_id_from_url(url: str) -> str:
        match = re.search(r"/c/([A-Za-z0-9-]+)", url)
        return match.group(1) if match else ""

    def _page(self) -> Page:
        if not self.page:
            raise RuntimeError("Browser is not started.")
        return self.page
