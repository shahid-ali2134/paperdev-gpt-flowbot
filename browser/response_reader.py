from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Page

from browser.ui_selectors import ASSISTANT_RESPONSE_SELECTORS


logger = logging.getLogger(__name__)


class ResponseReader:
    def __init__(self, page: Page) -> None:
        self.page = page

    async def latest_response_text(self) -> str:
        for selector in ASSISTANT_RESPONSE_SELECTORS:
            loc = self.page.locator(selector)
            try:
                count = await loc.count()
                if count:
                    text = await loc.nth(count - 1).inner_text(timeout=3000)
                    if text.strip():
                        return text.strip()
            except Exception:
                logger.debug("Response selector failed: %s", selector, exc_info=True)
        return ""

    async def wait_until_stable(self, stable_seconds: float = 1.0, timeout_seconds: float = 180.0) -> str:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        last_text = ""
        last_change = asyncio.get_running_loop().time()
        while asyncio.get_running_loop().time() < deadline:
            text = await self.latest_response_text()
            if text != last_text:
                last_text = text
                last_change = asyncio.get_running_loop().time()
            elif text and asyncio.get_running_loop().time() - last_change >= stable_seconds:
                return text
            await asyncio.sleep(1)
        logger.warning("Timed out waiting for response text to stabilize.")
        return last_text
