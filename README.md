# 013 Bot - Telegram Bot

Bot features: content sharing with temporary links, admin management, multi-language support (English, Arabic, Russian), content viewer tracking, and developer info.

## Setup on Termux

### 1. Install dependencies
```bash
pkg update && pkg upgrade
pkg install python
pip install -r requirements.txt
```

### 2. Set your Bot Token
Open `config.py` and replace `YOUR_BOT_TOKEN_HERE` with your actual bot token from @BotFather.

Or set it as an environment variable:
```bash
export BOT_TOKEN="your_token_here"
python main.py
```

### 3. Set Owner ID
Your Telegram ID `8269121832` is already set as owner in `config.py`.

### 4. Run the bot
```bash
python main.py
```

### 5. Add welcome GIF
After starting the bot, go to Settings > Set Welcome GIF and send your GIF file. The bot will cache it and use it for all /start messages.

### 6. Set Developer Info
Go to Settings > Set Dev Info and follow the steps to set the developer name, ID, username, and photo.

## Features

- Reply keyboard with 5 main sections
- Add any content (photo, video, audio, voice, document, sticker, GIF, text)
- Auto-generated temporary deep links
- Configurable auto-delete time in seconds
- Track who viewed each content item
- Admin management with per-admin permission toggles
- Multi-language: English, Arabic, Russian (per admin/owner)
- Regular users always see English and can only use the Developer button
- Cached welcome GIF (uploaded once, stored by file_id)
- Developer info with spoiler photo

## File Structure

```
bot/
  main.py          - Entry point and message router
  config.py        - Bot token, owner ID, defaults
  database.py      - SQLite database operations
  languages.py     - All strings in 3 languages
  keyboards.py     - Reply and inline keyboards
  utils.py         - Helpers and utilities
  handlers/
    start.py       - /start command and deep link handler
    content.py     - Content management
    admin.py       - Admin management
    settings.py    - Settings, language, GIF, dev info
    stats.py       - Statistics
    developer.py   - Developer info button
  bot.db           - SQLite database (auto-created)
```

## Run in Background (Termux)
```bash
nohup python main.py > bot.log 2>&1 &
```

To stop:
```bash
pkill -f "python main.py"
```
