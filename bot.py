from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import discord
from discord import app_commands

from browser.chatgpt_controller import ChatGPTController
from browser.chrome_session import ChromeSession
from config import BASE_DIR, settings
from core.command_router import CommandRouter
from core.memory_manager import MemoryManager
from core.paper_workspace import PaperWorkspaceManager
from core.prompt_builder import PromptBuilder


def configure_logging() -> None:
    logs_dir = settings.app_storage_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "paperdev.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )


class PaperDevBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.router: CommandRouter | None = None

    async def setup_hook(self) -> None:
        workspace = PaperWorkspaceManager(settings.output_root)
        memory = MemoryManager(settings.app_storage_dir / "memory.json")
        prompts = PromptBuilder(BASE_DIR / "prompts")
        chrome = ChromeSession(
            profile_dir=settings.browser_profile_dir,
            channel=settings.chrome_channel,
            executable_path=settings.chrome_executable_path,
            headless=settings.headless,
        )
        chatgpt = ChatGPTController(chrome, settings.chatgpt_url)
        self.router = CommandRouter(workspace, memory, prompts, chatgpt)

        guild = discord.Object(id=settings.discord_guild_id) if settings.discord_guild_id else None
        register_commands(self, guild)
        if guild:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        logging.info("Discord slash commands synced.")

    async def close(self) -> None:
        if self.router:
            await self.router.close()
        await super().close()


def _router(interaction: discord.Interaction) -> CommandRouter:
    bot = interaction.client
    if not isinstance(bot, PaperDevBot) or bot.router is None:
        raise RuntimeError("PaperDev router is not initialized.")
    return bot.router


async def _send_long_followup(interaction: discord.Interaction, message: str) -> None:
    chunks = [message[i : i + 1900] for i in range(0, len(message), 1900)] or [message]
    for chunk in chunks:
        await interaction.followup.send(chunk)


def register_commands(bot: PaperDevBot, guild: discord.Object | None) -> None:
    @bot.tree.command(name="paper_create", description="Create a new PaperDev research-paper workflow.")
    @app_commands.describe(topic_area="Conference topic area", keywords_or_focus="Keywords or focus terms")
    async def paper_create(
        interaction: discord.Interaction, topic_area: str, keywords_or_focus: str
    ) -> None:
        await interaction.response.defer(thinking=True)
        try:
            result = await _router(interaction).paper_create(topic_area, keywords_or_focus)
            await _send_long_followup(interaction, result)
        except Exception as exc:
            logging.exception("paper_create failed")
            await interaction.followup.send(f"Paper creation failed: `{exc}`")

    @bot.tree.command(name="paper_validate", description="Validate a selected topic in the active ChatGPT chat.")
    @app_commands.describe(paper_id="Paper ID such as P1May", selected_topic="The topic you selected from Prompt 1")
    async def paper_validate(
        interaction: discord.Interaction, paper_id: str, selected_topic: str
    ) -> None:
        await interaction.response.defer(thinking=True)
        try:
            result = await _router(interaction).paper_validate(paper_id, selected_topic)
            await _send_long_followup(interaction, result)
        except Exception as exc:
            logging.exception("paper_validate failed")
            await interaction.followup.send(f"Topic validation failed: `{exc}`")

    @bot.tree.command(name="paper_finalize", description="Create final title and IEEE abstract.")
    @app_commands.describe(paper_id="Paper ID such as P1May")
    async def paper_finalize(interaction: discord.Interaction, paper_id: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            result = await _router(interaction).paper_finalize(paper_id)
            await _send_long_followup(interaction, result)
        except Exception as exc:
            logging.exception("paper_finalize failed")
            await interaction.followup.send(f"Finalization failed: `{exc}`")

    @bot.tree.command(
        name="paper_auto_continue",
        description="Continue an existing paper from Prompt 1 using the first recommended topic.",
    )
    @app_commands.describe(paper_id="Paper ID such as P1May")
    async def paper_auto_continue(interaction: discord.Interaction, paper_id: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            result = await _router(interaction).paper_auto_continue(paper_id)
            await _send_long_followup(interaction, result)
        except Exception as exc:
            logging.exception("paper_auto_continue failed")
            await interaction.followup.send(f"Auto-continue failed: `{exc}`")

    @bot.tree.command(name="paper_status", description="Show current paper workflow status.")
    @app_commands.describe(paper_id="Paper ID such as P1May")
    async def paper_status(interaction: discord.Interaction, paper_id: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            await interaction.followup.send(_router(interaction).paper_status(paper_id))
        except Exception as exc:
            logging.exception("paper_status failed")
            await interaction.followup.send(f"Could not load status: `{exc}`")

    @bot.tree.command(name="paper_list", description="List paper workspaces.")
    async def paper_list(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            await _send_long_followup(interaction, _router(interaction).paper_list())
        except Exception as exc:
            logging.exception("paper_list failed")
            await interaction.followup.send(f"Could not list papers: `{exc}`")

    @bot.tree.command(name="paper_resume", description="Resume a saved ChatGPT paper chat.")
    @app_commands.describe(paper_id="Paper ID such as P1May")
    async def paper_resume(interaction: discord.Interaction, paper_id: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            result = await _router(interaction).paper_resume(paper_id)
            await interaction.followup.send(result)
        except Exception as exc:
            logging.exception("paper_resume failed")
            await interaction.followup.send(f"Could not resume paper: `{exc}`")


async def main() -> None:
    configure_logging()
    if not settings.discord_bot_token or settings.discord_bot_token == "replace_with_your_token":
        raise RuntimeError("Set DISCORD_BOT_TOKEN in .env before running PaperDev.")
    settings.app_storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.app_storage_dir / "logs").mkdir(parents=True, exist_ok=True)
    bot = PaperDevBot()
    await bot.start(settings.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())
