import asyncio
import json
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from config import OWNER_ID, CHANNEL_LINK, DEV_ID
from languages import get_text
from keyboards import main_keyboard
from utils import get_lang_for_user, user_display_name, schedule_delete
from handlers.content import _send_single_item


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.first_name or "", user.last_name or "")

    # Check banned
    if db.is_banned(user.id):
        await update.message.reply_text(get_text("user_banned_msg", "en"))
        return

    # Check maintenance (only dev can bypass)
    if db.get_setting("maintenance_mode") == "1" and user.id != DEV_ID:
        msg = db.get_setting("maintenance_message") or get_text("maintenance_msg", "en")
        await update.message.reply_text(msg)
        return

    lang = get_lang_for_user(user.id)
    is_auth = db.is_admin_or_owner(user.id)

    args = context.args
    if args and args[0].startswith("view_"):
        await _handle_view_link(update, context, args[0][5:], user, lang, is_auth)
        return

    await _send_welcome(update, context, lang, is_admin=is_auth, user_id=user.id)


async def _handle_view_link(update, context, code, user, lang, is_auth):
    content = db.get_content_by_code(code)
    if not content:
        await update.message.reply_text(get_text("content_expired", lang), parse_mode=ParseMode.HTML)
        return

    db.add_view(content["id"], user.id, user_display_name(user), user.username or "")

    chat_id = update.effective_chat.id
    sent_msgs = []

    label = await update.message.reply_text(get_text("content_sent", lang), parse_mode=ParseMode.HTML)
    sent_msgs.append(label.message_id)

    # Deliver all items
    stored_items = json.loads(content.get("items_json") or "[]")
    if not stored_items:
        stored_items = [{
            "file_id": content.get("file_id"),
            "file_type": content.get("file_type"),
            "raw_text": content.get("raw_text")
        }]

    for item in stored_items:
        try:
            m = await _send_one_item(context.bot, chat_id, item)
            if m:
                sent_msgs.append(m.message_id)
        except Exception:
            pass

    delete_after = content.get("delete_after", 20)
    if delete_after and delete_after > 0:
        notice = await update.message.reply_text(
            get_text("content_auto_delete", lang, time=delete_after),
            parse_mode=ParseMode.HTML
        )
        sent_msgs.append(notice.message_id)
        asyncio.create_task(schedule_delete(context.bot, chat_id, sent_msgs, delete_after))

    if is_auth:
        from config import DEV_ID as _DEV_ID
        await update.message.reply_text(
            get_text("choose_option", lang),
            reply_markup=main_keyboard(lang, is_admin=True, user_id=user.id),
            parse_mode=ParseMode.HTML
        )


async def _send_one_item(bot, chat_id, item):
    ft = item.get("file_type", "")
    fid = item.get("file_id")
    rt = item.get("raw_text")
    if ft == "photo" and fid:
        return await bot.send_photo(chat_id=chat_id, photo=fid)
    elif ft == "video" and fid:
        return await bot.send_video(chat_id=chat_id, video=fid)
    elif ft == "audio" and fid:
        return await bot.send_audio(chat_id=chat_id, audio=fid)
    elif ft == "voice" and fid:
        return await bot.send_voice(chat_id=chat_id, voice=fid)
    elif ft == "document" and fid:
        return await bot.send_document(chat_id=chat_id, document=fid)
    elif ft == "sticker" and fid:
        return await bot.send_sticker(chat_id=chat_id, sticker=fid)
    elif ft == "animation" and fid:
        return await bot.send_animation(chat_id=chat_id, animation=fid)
    elif ft == "video_note" and fid:
        return await bot.send_video_note(chat_id=chat_id, video_note=fid)
    elif ft == "text" and rt:
        return await bot.send_message(chat_id=chat_id, text=rt, parse_mode=ParseMode.HTML)
    return None


async def _send_welcome(update, context, lang, is_admin, user_id):
    chat_id = update.effective_chat.id
    gif_file_id = db.get_setting("welcome_gif_file_id")

    caption = (
        f"<blockquote>{get_text('welcome_line1', lang)}</blockquote>\n\n"
        f"{get_text('welcome_line2', lang)}\n\n"
        f'<blockquote><a href="{CHANNEL_LINK}">{get_text("welcome_line3", lang)}</a></blockquote>'
    )

    kb = main_keyboard(lang, is_admin=is_admin, user_id=user_id)

    if gif_file_id:
        await context.bot.send_animation(
            chat_id=chat_id,
            animation=gif_file_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )
    else:
        await update.message.reply_text(
            caption,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
            disable_web_page_preview=True
        )
