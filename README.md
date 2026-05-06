# PaperDev

PaperDev is a local, personal Discord-controlled browser automation agent for research-paper workflows. It uses:

- `discord.py` for Discord slash commands
- `LangGraph` for workflow orchestration
- `Playwright` for headful Chrome automation
- A separate persistent Chrome profile at `browser_profile/PaperDevProfile`

Version 1 controls ChatGPT through the browser UI. It does not use the OpenAI API for content generation.

## Setup

1. Create a Discord bot in the Discord Developer Portal and copy its token.
2. Copy `.env.example` to `.env`.
3. Put your token in `.env`:

```env
DISCORD_BOT_TOKEN=replace_with_your_token
```

4. Install dependencies:

```powershell
pip install -r requirements.txt
```

5. Install Playwright browser support:

```powershell
python -m playwright install chromium
```

6. Run PaperDev:

```powershell
python bot.py
```

7. First time only: the browser opens ChatGPT. Log in manually in that automation browser profile. PaperDev will reuse that profile later.

## Configuration

`.env.example` contains:

```env
DISCORD_BOT_TOKEN=replace_with_your_token
DISCORD_GUILD_ID=
CHROME_CHANNEL=chrome
CHROME_EXECUTABLE_PATH=
PAPERDEV_OUTPUT_ROOT=F:\Upwork
PAPERDEV_BROWSER_PROFILE_DIR=browser_profile/PaperDevProfile
PAPERDEV_APP_STORAGE_DIR=app_storage
CHATGPT_URL=https://chatgpt.com/
```

Paper outputs are created under:

```text
F:\Upwork\<MonthName> <CurrentYear> Papers\<PaperFolderName>\
```

Example:

```text
F:\Upwork\May 2026 Papers\P1May Machine Vision Pattern Recognition\
```

Internal runtime files such as memory, logs, and the Chrome automation profile stay inside the `PaperDev` project directory.

## Discord Commands

Use these slash commands:

- `/paper_create topic_area keywords_or_focus`
- `/paper_validate paper_id selected_topic`
- `/paper_finalize paper_id`
- `/paper_auto_continue paper_id`
- `/paper_status paper_id`
- `/paper_list`
- `/paper_resume paper_id`

## Workflow

1. `/paper_create` creates the monthly folder under `F:\Upwork`, creates a paper workspace, opens ChatGPT, starts a new chat, sends Prompt 1, saves `01_topic_discovery.md`, automatically extracts the first recommended topic, sends Prompt 2, saves `02_topic_validation.md`, sends Prompt 3, writes `03_title_abstract_raw.md` and `final_title_abstract.txt`, attempts to rename the ChatGPT chat, attempts to rename the local folder, and records the topic in `app_storage/memory.json`.
2. `/paper_validate` is still available as a manual recovery command if you want to validate a different selected topic later.
3. `/paper_finalize` is still available as a manual recovery command if finalization needs to be rerun.
4. `/paper_auto_continue` is available for an older workflow that stopped after Prompt 1. It reads `01_topic_discovery.md`, extracts the first recommended topic, then runs Prompt 2 and Prompt 3 automatically.

Each paper folder contains:

- `metadata.json`
- `01_topic_discovery.md`
- `02_topic_validation.md`
- `03_title_abstract_raw.md`
- `final_title_abstract.txt`
- `logs.txt` if you add paper-specific logging later

## ChatGPT UI Selectors

ChatGPT UI changes over time. Browser selectors are centralized in:

```text
browser/ui_selectors.py
```

If sending prompts, reading responses, or renaming chats stops working, update selectors there first.

## Notes

- PaperDev uses a separate Chrome automation profile and does not touch your normal Chrome profile.
- It runs headful by default so you can see what it is doing.
- Existing paper folders are never overwritten. Numeric suffixes such as `- 2` and `- 3` are appended when needed.
- Existing output files are backed up with timestamped `.bak` names before being overwritten.
