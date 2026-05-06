from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    discord_bot_token: str
    discord_guild_id: int | None
    chrome_channel: str | None
    chrome_executable_path: str | None
    output_root: Path
    browser_profile_dir: Path
    app_storage_dir: Path
    chatgpt_url: str
    headless: bool

    def __init__(self) -> None:
        self.discord_bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
        guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        self.discord_guild_id = int(guild_id) if guild_id.isdigit() else None
        self.chrome_channel = os.getenv("CHROME_CHANNEL", "chrome").strip() or None
        self.chrome_executable_path = os.getenv("CHROME_EXECUTABLE_PATH", "").strip() or None
        self.output_root = Path(os.getenv("PAPERDEV_OUTPUT_ROOT", r"F:\Upwork"))
        self.browser_profile_dir = self._resolve_project_path(
            os.getenv("PAPERDEV_BROWSER_PROFILE_DIR", "browser_profile/PaperDevProfile")
        )
        self.app_storage_dir = self._resolve_project_path(
            os.getenv("PAPERDEV_APP_STORAGE_DIR", "app_storage")
        )
        self.chatgpt_url = os.getenv("CHATGPT_URL", "https://chatgpt.com/").strip()
        self.headless = os.getenv("PAPERDEV_HEADLESS", "false").lower() in {"1", "true", "yes"}

    @staticmethod
    def _resolve_project_path(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else BASE_DIR / path


settings = Settings()
