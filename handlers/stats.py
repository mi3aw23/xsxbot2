from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from languages import get_text
from keyboards import stats_keyboard
from utils import get_lang_for_user, get_file_type_label, format_datetime
import json


async def stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "view_stats"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return

    await update.message.reply_text(
        get_text("choose_option", lang),
        reply_markup=stats_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


async def all_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "view_stats"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return

    stats = db.count_all_content()
    await update.message.reply_text(
        get_text("all_content_text", lang,
                 total=stats["total"],
                 active=stats["active"],
                 expired=stats["expired"]),
        parse_mode=ParseMode.HTML
    )


async def popular_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "view_stats"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return

    items = db.get_popular_content(limit=10)
    if not items:
        await update.message.reply_text(get_text("no_content", lang))
        return

    lines = []
    for i, item in enumerate(items, 1):
        file_type = get_file_type_label(item["file_type"])
        lines.append(f"{i}. {file_type} - Views: {item['view_count']}")

    await update.message.reply_text(
        get_text("popular_text", lang, items="\n".join(lines)),
        parse_mode=ParseMode.HTML
    )


async def recent_views(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "view_stats"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return

    views = db.get_recent_views(limit=10)
    if not views:
        await update.message.reply_text(get_text("no_content", lang))
        return

    lines = []
    for v in views:
        name = v.get("viewer_name") or "Unknown"
        vid = v.get("viewer_id")
        file_type = get_file_type_label(v.get("file_type", ""))
        viewed_at = format_datetime(v.get("viewed_at", ""))
        lines.append(f'<a href="tg://user?id={vid}">{name}</a> - {file_type} ({viewed_at})')

    await update.message.reply_text(
        get_text("recent_views_text", lang, items="\n".join(lines)),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


async def total_views(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "view_stats"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return

    stats = db.get_total_views()
    await update.message.reply_text(
        get_text("total_views_text", lang,
                 views=stats["views"],
                 unique=stats["unique"],
                 content=stats["content"]),
        parse_mode=ParseMode.HTML
    )


async def export_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "view_stats"):
        await update.message.reply_text(get_text("not_authorized", lang))
        return

    all_stats = db.count_all_content()
    total_stats = db.get_total_views()
    popular = db.get_popular_content(limit=10)
    recent = db.get_recent_views(limit=20)

    export = {
        "content": all_stats,
        "views": total_stats,
        "popular": [
            {
                "id": p["id"],
                "type": p["file_type"],
                "code": p["link_code"],
                "views": p["view_count"]
            }
            for p in popular
        ],
        "recent_views": [
            {
                "viewer": v.get("viewer_name", "Unknown"),
                "viewer_id": v.get("viewer_id"),
                "content_type": v.get("file_type", ""),
                "time": v.get("viewed_at", "")
            }
            for v in recent
        ]
    }

    export_str = json.dumps(export, ensure_ascii=False, indent=2)
    export_bytes = export_str.encode("utf-8")

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=export_bytes,
        filename="bot_stats.json",
        caption="Bot Statistics Export"
    )
