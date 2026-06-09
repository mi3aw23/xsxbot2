from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from languages import get_text
from utils import get_lang_for_user


async def developer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    dev_name = db.get_setting("dev_name", "Dev")
    dev_id_str = db.get_setting("dev_id", "0")
    dev_username = db.get_setting("dev_username", "dev_username")
    dev_photo = db.get_setting("dev_photo_file_id")

    try:
        dev_id = int(dev_id_str)
    except (ValueError, TypeError):
        dev_id = 0

    text = get_text(
        "dev_info_text", lang,
        name=dev_name,
        id=dev_id,
        username=dev_username
    )

    chat_id = update.effective_chat.id

    if dev_photo:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=dev_photo,
            caption=text,
            parse_mode=ParseMode.HTML,
            has_spoiler=True
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
