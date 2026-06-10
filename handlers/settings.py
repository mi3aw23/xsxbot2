from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from config import OWNER_ID, DEV_ID
from languages import get_text
from keyboards import settings_keyboard, language_keyboard, cancel_keyboard, main_keyboard
from utils import get_lang_for_user, user_display_name, get_user_role, format_datetime


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    await update.message.reply_text(
        get_text("choose_option", lang),
        reply_markup=settings_keyboard(lang, user_id=user_id),
        parse_mode=ParseMode.HTML
    )


# ─── Language ─────────────────────────────────────────────────────────────────

async def language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not db.get_user_permission(user_id, "change_language"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return
    await update.message.reply_text(
        get_text("current_language", lang),
        reply_markup=language_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


async def _set_language(update, context, new_lang):
    user_id = update.effective_user.id
    old_lang = get_lang_for_user(user_id)
    if not db.get_user_permission(user_id, "change_language"):
        await update.message.reply_text(get_text("not_authorized", old_lang))
        return
    db.set_user_lang(user_id, new_lang)
    await update.message.reply_text(
        get_text("language_changed", new_lang),
        reply_markup=main_keyboard(new_lang, is_admin=db.is_admin_or_owner(user_id), user_id=user_id),
        parse_mode=ParseMode.HTML
    )


async def set_lang_en(update, context): await _set_language(update, context, "en")
async def set_lang_ar(update, context): await _set_language(update, context, "ar")
async def set_lang_ru(update, context): await _set_language(update, context, "ru")


# ─── Profile ──────────────────────────────────────────────────────────────────

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text(get_text("error", lang))
        return
    name = user_display_name(user)
    await update.message.reply_text(
        get_text("profile_text", lang,
                 name=name,
                 id=user_id,
                 username=user.get("username") or "N/A",
                 role=get_user_role(user, lang),
                 joined=format_datetime(user.get("joined_at", ""))),
        parse_mode=ParseMode.HTML
    )


# ─── Bot Info ─────────────────────────────────────────────────────────────────

async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    stats = db.get_total_views()
    await update.message.reply_text(
        get_text("bot_info_text", lang,
                 owner_id=OWNER_ID,
                 users=db.count_users(),
                 content=stats["content"],
                 views=stats["views"]),
        parse_mode=ParseMode.HTML
    )


# ─── Set Welcome GIF ──────────────────────────────────────────────────────────

async def start_set_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not db.is_admin_or_owner(user_id):
        await update.message.reply_text(get_text("not_authorized", lang))
        return
    db.set_state(user_id, "waiting_welcome_gif")
    await update.message.reply_text(
        get_text("send_gif", lang),
        reply_markup=cancel_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


async def receive_welcome_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    msg = update.message
    state, _ = db.get_state(user_id)
    if state != "waiting_welcome_gif":
        return

    gif_file_id = None
    if msg.animation:
        gif_file_id = msg.animation.file_id
    elif msg.video:
        gif_file_id = msg.video.file_id
    elif msg.document and msg.document.mime_type in ("video/mp4", "image/gif"):
        gif_file_id = msg.document.file_id

    if not gif_file_id:
        await msg.reply_text("Please send a GIF or animation file.")
        return

    db.set_setting("welcome_gif_file_id", gif_file_id)
    db.clear_state(user_id)
    await msg.reply_text(
        get_text("gif_saved", lang),
        reply_markup=settings_keyboard(lang, user_id=user_id),
        parse_mode=ParseMode.HTML
    )


