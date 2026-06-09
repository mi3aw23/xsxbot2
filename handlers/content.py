import asyncio
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from config import OWNER_ID
from languages import get_text
from keyboards import content_keyboard, cancel_keyboard, content_list_inline
from utils import (get_lang_for_user, generate_code, make_link,
                   schedule_delete, get_file_type_label)


async def content_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    await update.message.reply_text(
        get_text("choose_option", lang),
        reply_markup=content_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


# ─── Add Content (multi-item) ─────────────────────────────────────────────────

async def start_add_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not db.get_user_permission(user_id, "add_content"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return
    db.set_state(user_id, "waiting_content", {"items": []})
    await update.message.reply_text(
        get_text("send_content", lang),
        reply_markup=cancel_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


def _extract_item(msg) -> dict | None:
    if msg.photo:
        return {"file_id": msg.photo[-1].file_id, "file_type": "photo"}
    if msg.video:
        return {"file_id": msg.video.file_id, "file_type": "video"}
    if msg.audio:
        return {"file_id": msg.audio.file_id, "file_type": "audio"}
    if msg.voice:
        return {"file_id": msg.voice.file_id, "file_type": "voice"}
    if msg.document:
        return {"file_id": msg.document.file_id, "file_type": "document"}
    if msg.sticker:
        return {"file_id": msg.sticker.file_id, "file_type": "sticker"}
    if msg.animation:
        return {"file_id": msg.animation.file_id, "file_type": "animation"}
    if msg.video_note:
        return {"file_id": msg.video_note.file_id, "file_type": "video_note"}
    if msg.text and msg.text.strip().lower() not in ("skip", "/skip"):
        return {"file_id": None, "file_type": "text", "raw_text": msg.text}
    return None


async def receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    msg = update.message
    state, state_data = db.get_state(user_id)
    if state != "waiting_content":
        return

    text = msg.text.strip() if msg.text else ""
    items = state_data.get("items", [])

    # Handle skip
    if text.lower() in ("skip", "/skip"):
        if not items:
            await msg.reply_text(get_text("no_items_yet", lang), parse_mode=ParseMode.HTML)
            return
        # Move to set delete time
        db.set_state(user_id, "waiting_delete_time", {"items": items})
        await msg.reply_text(
            get_text("set_delete_time", lang),
            reply_markup=cancel_keyboard(lang),
            parse_mode=ParseMode.HTML
        )
        return

    item = _extract_item(msg)
    if item is None:
        await msg.reply_text(get_text("send_content", lang), parse_mode=ParseMode.HTML)
        return

    items.append(item)
    db.set_state(user_id, "waiting_content", {"items": items})

    await msg.reply_text(
        get_text("item_added", lang, count=len(items)),
        reply_markup=cancel_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


async def receive_delete_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    msg = update.message
    state, state_data = db.get_state(user_id)
    if state != "waiting_delete_time":
        return

    try:
        delete_after = int(msg.text.strip())
        if delete_after < 0:
            raise ValueError
    except (ValueError, AttributeError):
        await msg.reply_text(get_text("invalid_time", lang))
        return

    items = state_data.get("items", [])
    bot_me = await context.bot.get_me()
    code = generate_code()
    link = make_link(bot_me.username, code)

    # Use first item's fields for backward-compat; store all in items_json
    first = items[0] if items else {}
    file_type = "multi" if len(items) > 1 else first.get("file_type", "text")
    file_id = first.get("file_id")
    raw_text = first.get("raw_text")

    db.add_content(
        owner_id=user_id,
        file_id=file_id,
        file_type=file_type,
        raw_text=raw_text,
        link_code=code,
        delete_after=delete_after,
        items=items
    )
    db.clear_state(user_id)

    count = len(items)
    if count > 1:
        text = (
            get_text("multi_content_added", lang, count=count, link=link, time=delete_after)
            if delete_after > 0
            else get_text("multi_content_added_no_delete", lang, count=count, link=link)
        )
    else:
        text = (
            get_text("content_added", lang, link=link, time=delete_after)
            if delete_after > 0
            else get_text("content_added_no_delete", lang, link=link)
        )

    await msg.reply_text(text, reply_markup=content_keyboard(lang), parse_mode=ParseMode.HTML)


# ─── My Links ─────────────────────────────────────────────────────────────────

async def my_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    content_list = db.get_all_content() if user_id == OWNER_ID else db.get_user_content(user_id)

    if not content_list:
        await update.message.reply_text(get_text("no_links", lang), parse_mode=ParseMode.HTML)
        return

    bot_me = await context.bot.get_me()
    items_text = []
    for i, item in enumerate(content_list, 1):
        link = make_link(bot_me.username, item["link_code"])
        expire = f"{item['delete_after']}s" if item.get("delete_after") else "Never"
        views = db.count_content_views(item["id"])
        stored_items = json.loads(item.get("items_json") or "[]")
        count = len(stored_items) if stored_items else 1
        ft = get_file_type_label(item["file_type"])
        label = f"{ft} x{count}" if count > 1 else ft
        items_text.append(
            get_text("link_item", lang, num=i, type=label,
                     views=views, expire=expire, link=link)
        )

    await update.message.reply_text(
        get_text("my_links_text", lang, items="\n\n".join(items_text)),
        reply_markup=content_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


# ─── View Viewers ─────────────────────────────────────────────────────────────

async def view_viewers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not db.get_user_permission(user_id, "view_viewers"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return

    content_list = db.get_all_content() if user_id == OWNER_ID else db.get_user_content(user_id)
    if not content_list:
        await update.message.reply_text(get_text("no_content", lang))
        return

    kb = content_list_inline(content_list, "viewers")
    await update.message.reply_text(
        get_text("select_content_viewers", lang),
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


async def show_content_viewers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = get_lang_for_user(user_id)
    chat_id = query.message.chat_id
    content_id = int(query.data.split("_", 1)[1])
    content = db.get_content_by_id(content_id)

    if not content:
        await query.message.reply_text(get_text("link_not_found", lang))
        return

    # Send all items in this content
    stored_items = json.loads(content.get("items_json") or "[]")
    if not stored_items:
        # Legacy single-item
        stored_items = [{
            "file_id": content.get("file_id"),
            "file_type": content.get("file_type"),
            "raw_text": content.get("raw_text")
        }]

    for it in stored_items:
        try:
            await _send_single_item(context.bot, chat_id, it)
        except Exception:
            pass

    # Send viewers list
    viewers = db.get_viewers_with_repeats(content_id)
    total_views = db.count_content_views(content_id)

    if not viewers:
        await query.message.reply_text(get_text("no_viewers", lang), parse_mode=ParseMode.HTML)
        return

    entries = []
    for v in viewers:
        entry = get_text("viewer_line", lang,
                         vid=v["viewer_id"],
                         name=v.get("viewer_name") or "Unknown",
                         count=v["view_count"])
        entries.append(entry)

    header = f"• Viewers ({total_views})\n\n"
    await query.message.reply_text(
        header + "\n\n\n".join(entries),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


# ─── Delete Link ──────────────────────────────────────────────────────────────

async def delete_link_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not db.get_user_permission(user_id, "delete_content"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return

    content_list = db.get_all_content() if user_id == OWNER_ID else db.get_user_content(user_id)
    if not content_list:
        await update.message.reply_text(get_text("no_links", lang), parse_mode=ParseMode.HTML)
        return

    kb = content_list_inline(content_list, "delete_link")
    await update.message.reply_text(
        get_text("select_link_delete", lang),
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


async def confirm_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = get_lang_for_user(user_id)
    content_id = int(query.data.split("_", 2)[2])
    content = db.get_content_by_id(content_id)

    if not content:
        await query.message.reply_text(get_text("link_not_found", lang))
        return
    if content["owner_id"] != user_id and user_id != OWNER_ID:
        await query.message.reply_text(get_text("not_authorized", lang))
        return

    views = db.count_content_views(content_id)
    file_type = get_file_type_label(content["file_type"])
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Confirm", callback_data=f"do_delete_{content_id}"),
        InlineKeyboardButton("Cancel", callback_data="cancel_delete")
    ]])
    await query.message.reply_text(
        get_text("confirm_delete", lang, type=file_type, views=views),
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


async def do_delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = get_lang_for_user(user_id)
    content_id = int(query.data.split("_", 2)[2])
    content = db.get_content_by_id(content_id)

    if not content:
        await query.message.reply_text(get_text("link_not_found", lang))
        return
    if content["owner_id"] != user_id and user_id != OWNER_ID:
        await query.message.reply_text(get_text("not_authorized", lang))
        return

    db.deactivate_content_by_id(content_id)
    await query.message.edit_text(get_text("link_deleted", lang), parse_mode=ParseMode.HTML)


async def cancel_delete_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_lang_for_user(query.from_user.id)
    await query.message.edit_text(get_text("cancelled", lang))


# ─── Link Settings ────────────────────────────────────────────────────────────

async def link_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    stats = db.count_all_content()
    await update.message.reply_text(
        f"Link Settings:\n\nTotal: {stats['total']}\nActive: {stats['active']}\nExpired: {stats['expired']}",
        parse_mode=ParseMode.HTML
    )


# ─── Helper: send one item ────────────────────────────────────────────────────

async def _send_single_item(bot, chat_id: int, item: dict):
    ft = item.get("file_type", "")
    fid = item.get("file_id")
    rt = item.get("raw_text")
    if ft == "photo" and fid:
        await bot.send_photo(chat_id=chat_id, photo=fid)
    elif ft == "video" and fid:
        await bot.send_video(chat_id=chat_id, video=fid)
    elif ft == "audio" and fid:
        await bot.send_audio(chat_id=chat_id, audio=fid)
    elif ft == "voice" and fid:
        await bot.send_voice(chat_id=chat_id, voice=fid)
    elif ft == "document" and fid:
        await bot.send_document(chat_id=chat_id, document=fid)
    elif ft == "sticker" and fid:
        await bot.send_sticker(chat_id=chat_id, sticker=fid)
    elif ft == "animation" and fid:
        await bot.send_animation(chat_id=chat_id, animation=fid)
    elif ft == "video_note" and fid:
        await bot.send_video_note(chat_id=chat_id, video_note=fid)
    elif ft == "text" and rt:
        await bot.send_message(chat_id=chat_id, text=rt, parse_mode=ParseMode.HTML)
