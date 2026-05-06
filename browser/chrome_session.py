from __future__ import annotations

import logging
from pathlib import Path

from playwright.async_api import BrowserContext, Page, async_playwright


logger = logging.getLogger(__name__)


class ChromeSession:
    def __init__(
        self,
        profile_dir: Path,
        channel: str | None = "chrome",
        executable_path: str | None = None,
        headless: bool = False,
    ) -> None:
        self.profile_dir = profile_dir
        self.channel = channel
        self.executable_path = executable_path
        self.headless = headless
        self._playwright = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def start_browser(self) -> Page:
        if self.context and self.page:
            return self.page
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        launch_args = {
            "user_data_dir": str(self.profile_dir),
            "headless": self.headless,
            "viewport": {"width": 1440, "height": 1000},
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if self.executable_path:
            launch_args["executable_path"] = self.executable_path
        elif self.channel:
            launch_args["channel"] = self.channel
        self.context = await self._playwright.chromium.launch_persistent_context(**launch_args)
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        logger.info("Chrome automation profile started at %s", self.profile_dir)
        return self.page

    async def close_browser(self) -> None:
        if self.context:
            await self.context.close()
            self.context = None
            self.page = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
