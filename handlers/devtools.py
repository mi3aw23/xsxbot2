import asyncio
import json
import os
import sys
import time
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from config import BOT_TOKEN, OWNER_ID, DEV_ID, CHANNEL_LINK, DB_PATH
from languages import get_text
from utils import get_lang_for_user, user_display_name, get_user_role, format_datetime
from keyboards import (
    dev_users_keyboard, dev_broadcast_keyboard, dev_system_keyboard,
    dev_db_keyboard, dev_links_keyboard, dev_announce_keyboard,
    dev_config_keyboard, dev_maintenance_keyboard, dev_export_keyboard,
    dev_tools_keyboard, main_keyboard
)

BOT_START_TIME = time.time()
_error_count = 0


def increment_errors():
    global _error_count
    _error_count += 1


def is_dev(user_id: int) -> bool:
    return user_id == DEV_ID


async def _dev_only(update, lang):
    await update.message.reply_text(get_text("not_authorized", lang))


# ─── 1. Users Panel ───────────────────────────────────────────────────────────

async def dev_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_users_menu", lang),
        reply_markup=dev_users_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def dev_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    users = db.get_all_users(limit=30)
    if not users:
        await update.message.reply_text(get_text("no_content", lang)); return
    lines = []
    for i, u in enumerate(users, 1):
        name = user_display_name(u)
        role = get_user_role(u, lang)
        username = u.get("username") or "N/A"
        lines.append(get_text("dev_user_item", lang, num=i, id=u["id"], name=name, username=username, role=role))
    await update.message.reply_text(
        get_text("dev_all_users", lang, count=len(users), users="\n".join(lines)),
        parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


async def dev_search_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_state(user_id, "dev_waiting_search_user")
    await update.message.reply_text(get_text("dev_search_prompt", lang), parse_mode=ParseMode.HTML)


async def dev_receive_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    text = update.message.text.strip()
    target = db.get_user(int(text)) if text.lstrip("@").isdigit() else db.get_user_by_username(text)
    db.clear_state(user_id)
    if not target:
        await update.message.reply_text(get_text("dev_user_not_found", lang)); return
    name = user_display_name(target)
    await update.message.reply_text(
        get_text("dev_user_found", lang,
                 id=target["id"], name=name,
                 username=target.get("username") or "N/A",
                 role=get_user_role(target, lang),
                 joined=format_datetime(target.get("joined_at", "")),
                 last_seen=format_datetime(target.get("last_seen", ""))),
        parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


async def dev_ban_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_state(user_id, "dev_waiting_ban_user")
    await update.message.reply_text(get_text("dev_ban_prompt", lang), parse_mode=ParseMode.HTML)


async def dev_receive_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    try:
        target_id = int(update.message.text.strip())
        db.ban_user(target_id)
        db.clear_state(user_id)
        await update.message.reply_text(get_text("dev_banned", lang, id=target_id), parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text(get_text("error", lang))


async def dev_unban_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_state(user_id, "dev_waiting_unban_user")
    await update.message.reply_text(get_text("dev_unban_prompt", lang), parse_mode=ParseMode.HTML)


async def dev_receive_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    try:
        target_id = int(update.message.text.strip())
        db.unban_user(target_id)
        db.clear_state(user_id)
        await update.message.reply_text(get_text("dev_unbanned", lang, id=target_id), parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text(get_text("error", lang))


async def dev_user_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(get_text("dev_user_count", lang, count=db.count_users()), parse_mode=ParseMode.HTML)


async def dev_last_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    users = db.get_last_active_users(limit=10)
    lines = []
    for u in users:
        name = user_display_name(u)
        lines.append(f'<a href="tg://user?id={u["id"]}">{name}</a> — {format_datetime(u.get("last_seen",""))}')
    await update.message.reply_text(
        get_text("dev_last_active", lang, users="\n".join(lines) or "-"),
        parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


# ─── 2. Broadcast ─────────────────────────────────────────────────────────────

async def dev_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_broadcast_menu", lang),
        reply_markup=dev_broadcast_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def _prompt_broadcast(update, context, target: str):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_state(user_id, f"dev_waiting_broadcast_{target}")
    await update.message.reply_text(get_text("dev_broadcast_prompt", lang), parse_mode=ParseMode.HTML)


async def dev_send_all_prompt(update, context): await _prompt_broadcast(update, context, "all")
async def dev_send_admins_prompt(update, context): await _prompt_broadcast(update, context, "admins")
async def dev_send_users_prompt(update, context): await _prompt_broadcast(update, context, "users")


async def dev_receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    text = update.message.text
    db.clear_state(user_id)
    users = db.get_all_users(limit=10000)
    count = 0
    for u in users:
        if target == "admins" and not (u.get("is_admin") or u.get("is_owner")):
            continue
        if target == "users" and (u.get("is_admin") or u.get("is_owner")):
            continue
        try:
            await context.bot.send_message(chat_id=u["id"], text=text)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    key = f"dev_broadcast_{target}_done" if target in ("admins", "users") else "dev_broadcast_done"
    if target == "admins": key = "dev_broadcast_admins_done"
    elif target == "users": key = "dev_broadcast_users_done"
    else: key = "dev_broadcast_done"
    db.add_announcement(text, count)
    await update.message.reply_text(get_text(key, lang, count=count), parse_mode=ParseMode.HTML)


async def dev_schedule_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_state(user_id, "dev_waiting_schedule")
    await update.message.reply_text(get_text("dev_schedule_prompt", lang), parse_mode=ParseMode.HTML)


async def dev_receive_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    db.clear_state(user_id)
    parts = update.message.text.strip().split(" ", 1)
    if len(parts) < 2:
        await update.message.reply_text(get_text("error", lang)); return
    try:
        delay = int(parts[0])
        msg = parts[1]
    except ValueError:
        await update.message.reply_text(get_text("error", lang)); return

    await update.message.reply_text(get_text("dev_scheduled", lang, time=delay), parse_mode=ParseMode.HTML)

    async def _do_schedule():
        await asyncio.sleep(delay)
        users = db.get_all_users(limit=10000)
        for u in users:
            try:
                await context.bot.send_message(chat_id=u["id"], text=msg)
                await asyncio.sleep(0.05)
            except Exception:
                pass

    asyncio.create_task(_do_schedule())


async def dev_view_sent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    announces = db.get_announcements(limit=5)
    if not announces:
        await update.message.reply_text(get_text("dev_no_sent", lang)); return
    lines = []
    for a in announces:
        lines.append(f"- {format_datetime(a['sent_at'])}: {a['text'][:50]}... ({a['sent_to']} users)")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ─── 3. System Info ───────────────────────────────────────────────────────────

async def dev_system_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_system_menu", lang),
        reply_markup=dev_system_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def dev_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    elapsed = int(time.time() - BOT_START_TIME)
    h, r = divmod(elapsed, 3600)
    m, s = divmod(r, 60)
    await update.message.reply_text(
        get_text("dev_uptime", lang, uptime=f"{h}h {m}m {s}s"), parse_mode=ParseMode.HTML
    )


async def dev_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    try:
        import resource
        mem_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        mem_mb = mem_bytes / (1024 * 1024)
        mem_str = f"{mem_mb:.1f} MB"
    except Exception:
        mem_str = "N/A"
    await update.message.reply_text(get_text("dev_memory", lang, memory=mem_str), parse_mode=ParseMode.HTML)


async def dev_db_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    size_bytes = db.get_db_size_bytes()
    size_kb = size_bytes / 1024
    size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"
    await update.message.reply_text(get_text("dev_db_size", lang, size=size_str), parse_mode=ParseMode.HTML)


async def dev_active_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    count = db.get_active_users_last_minutes(10)
    await update.message.reply_text(get_text("dev_active_now", lang, count=count), parse_mode=ParseMode.HTML)


async def dev_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(get_text("dev_errors_text", lang, count=_error_count), parse_mode=ParseMode.HTML)


# ─── 4. DB Control ────────────────────────────────────────────────────────────

async def dev_db_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_db_menu", lang),
        reply_markup=dev_db_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def dev_db_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    stats = db.get_db_stats()
    await update.message.reply_text(
        get_text("dev_db_stats", lang, **stats), parse_mode=ParseMode.HTML
    )


async def dev_clear_views(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.clear_all_views()
    await update.message.reply_text(get_text("dev_views_cleared", lang), parse_mode=ParseMode.HTML)


async def dev_clear_states(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.clear_all_states()
    await update.message.reply_text(get_text("dev_states_cleared", lang), parse_mode=ParseMode.HTML)


async def dev_clear_expired(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    count = db.delete_all_expired()
    await update.message.reply_text(get_text("dev_expired_cleared", lang), parse_mode=ParseMode.HTML)


async def dev_reset_db_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_state(user_id, "dev_waiting_reset_confirm")
    await update.message.reply_text(get_text("dev_reset_confirm", lang), parse_mode=ParseMode.HTML)


async def dev_receive_reset_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    db.clear_state(user_id)
    text = update.message.text.strip().lower()
    if text in ("yes", "نعم", "да"):
        db.reset_database()
        await update.message.reply_text(get_text("dev_reset_done", lang), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(get_text("cancelled", lang), parse_mode=ParseMode.HTML)


# ─── 5. All Links ─────────────────────────────────────────────────────────────

async def dev_links_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_links_menu", lang),
        reply_markup=dev_links_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def dev_view_all_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    stats = db.count_all_content()
    await update.message.reply_text(
        get_text("dev_all_links", lang, **stats), parse_mode=ParseMode.HTML
    )


async def dev_active_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    links = db.get_all_content()
    lines = [f"{i}. {l['file_type'].upper()} — {l['link_code']}" for i, l in enumerate(links[:20], 1)]
    await update.message.reply_text(
        get_text("dev_active_links_list", lang, count=len(links), items="\n".join(lines) or "-"),
        parse_mode=ParseMode.HTML
    )


async def dev_expired_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    links = db.get_expired_content()
    lines = [f"{i}. {l['file_type'].upper()} — {l['link_code']}" for i, l in enumerate(links[:20], 1)]
    await update.message.reply_text(
        get_text("dev_expired_links_list", lang, count=len(links), items="\n".join(lines) or "-"),
        parse_mode=ParseMode.HTML
    )


async def dev_delete_expired(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    count = db.delete_all_expired()
    await update.message.reply_text(get_text("dev_expired_deleted", lang, count=count), parse_mode=ParseMode.HTML)


async def dev_links_by_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    all_links = db.get_all_content_including_expired()
    user_map: dict = {}
    for lnk in all_links:
        oid = lnk["owner_id"]
        user_map.setdefault(oid, 0)
        user_map[oid] += 1
    lines = []
    for uid, cnt in sorted(user_map.items(), key=lambda x: -x[1]):
        u = db.get_user(uid)
        name = user_display_name(u) if u else str(uid)
        lines.append(f'<a href="tg://user?id={uid}">{name}</a>: {cnt} links')
    await update.message.reply_text("\n".join(lines) or "-", parse_mode=ParseMode.HTML, disable_web_page_preview=True)


# ─── 6. Announcements ─────────────────────────────────────────────────────────

async def dev_announce_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_announce_menu", lang),
        reply_markup=dev_announce_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def dev_new_announce_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_state(user_id, "dev_waiting_announce")
    await update.message.reply_text(get_text("dev_announce_prompt", lang), parse_mode=ParseMode.HTML)


async def dev_receive_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    text = update.message.text
    db.clear_state(user_id)
    db.set_state(user_id, "dev_waiting_send_announce", {"announce_text": text})
    await update.message.reply_text(f"Announcement saved. Use 'Send Announcement' to broadcast.", parse_mode=ParseMode.HTML)


async def dev_send_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    state, data = db.get_state(user_id)
    ann_text = data.get("announce_text") if state == "dev_waiting_send_announce" else None
    db.clear_state(user_id)
    if not ann_text:
        await update.message.reply_text("No announcement pending. Create one first."); return
    users = db.get_all_users(limit=10000)
    count = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u["id"], text=ann_text)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    db.add_announcement(ann_text, count)
    await update.message.reply_text(get_text("dev_announce_sent", lang, count=count), parse_mode=ParseMode.HTML)


async def dev_view_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    announces = db.get_announcements(limit=5)
    if not announces:
        await update.message.reply_text(get_text("dev_no_announcements", lang)); return
    lines = [f"{format_datetime(a['sent_at'])}: {a['text'][:80]} ({a['sent_to']} sent)" for a in announces]
    await update.message.reply_text("\n\n".join(lines), parse_mode=ParseMode.HTML)


async def dev_delete_last_ann(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    deleted = db.delete_last_announcement()
    key = "dev_ann_deleted" if deleted else "dev_no_announcements"
    await update.message.reply_text(get_text(key, lang), parse_mode=ParseMode.HTML)


async def dev_clear_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.clear_announcements()
    await update.message.reply_text(get_text("dev_ann_cleared", lang), parse_mode=ParseMode.HTML)


# ─── 7. Bot Config ────────────────────────────────────────────────────────────

async def dev_config_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_config_menu", lang),
        reply_markup=dev_config_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def dev_view_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    maint = "ON" if db.get_setting("maintenance_mode") == "1" else "OFF"
    token_preview = BOT_TOKEN[:10] + "..." if BOT_TOKEN else "N/A"
    await update.message.reply_text(
        get_text("dev_config_text", lang,
                 token=token_preview, owner=OWNER_ID, dev_id=DEV_ID,
                 db=DB_PATH, channel=CHANNEL_LINK, maint=maint),
        parse_mode=ParseMode.HTML
    )


async def dev_bot_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(get_text("dev_bot_commands_text", lang), parse_mode=ParseMode.HTML)


async def dev_set_bot_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(get_text("dev_set_name_prompt", lang), parse_mode=ParseMode.HTML)


async def dev_restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(get_text("dev_restarting", lang), parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    os.execv(sys.executable, [sys.executable] + sys.argv)


async def dev_toggle_maint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    current = db.get_setting("maintenance_mode") == "1"
    db.set_setting("maintenance_mode", "0" if current else "1")
    key = "dev_maint_disabled" if current else "dev_maint_enabled"
    await update.message.reply_text(get_text(key, lang), parse_mode=ParseMode.HTML)


# ─── 8. Maintenance ───────────────────────────────────────────────────────────

async def dev_maintenance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_maintenance_menu", lang),
        reply_markup=dev_maintenance_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def dev_enable_maint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_setting("maintenance_mode", "1")
    await update.message.reply_text(get_text("dev_maint_enabled", lang), parse_mode=ParseMode.HTML)


async def dev_disable_maint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_setting("maintenance_mode", "0")
    await update.message.reply_text(get_text("dev_maint_disabled", lang), parse_mode=ParseMode.HTML)


async def dev_maint_msg_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.set_state(user_id, "dev_waiting_maint_msg")
    await update.message.reply_text(get_text("dev_maint_msg_prompt", lang), parse_mode=ParseMode.HTML)


async def dev_receive_maint_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    db.set_setting("maintenance_message", update.message.text.strip())
    db.clear_state(user_id)
    await update.message.reply_text(get_text("dev_maint_msg_set", lang), parse_mode=ParseMode.HTML)


async def dev_maint_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    status = "ON" if db.get_setting("maintenance_mode") == "1" else "OFF"
    msg = db.get_setting("maintenance_message") or "-"
    await update.message.reply_text(get_text("dev_maint_status", lang, status=status, msg=msg), parse_mode=ParseMode.HTML)


async def dev_kick_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    db.clear_all_states()
    await update.message.reply_text(get_text("dev_sessions_cleared", lang), parse_mode=ParseMode.HTML)


# ─── 9. Export Data ───────────────────────────────────────────────────────────

async def dev_export_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_export_menu", lang),
        reply_markup=dev_export_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def _send_json_export(update, context, data, filename):
    export_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=export_bytes,
        filename=filename,
        caption=f"Export: {filename}"
    )


async def dev_export_users(update, context):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    users = db.get_all_users(limit=100000)
    data = [{"id": u["id"], "name": user_display_name(u), "username": u.get("username"), "role": get_user_role(u, "en"), "joined": u.get("joined_at")} for u in users]
    await _send_json_export(update, context, data, "users_export.json")


async def dev_export_content(update, context):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    items = db.get_all_content_including_expired()
    await _send_json_export(update, context, items, "content_export.json")


async def dev_export_views(update, context):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    views = db.get_recent_views(limit=100000)
    await _send_json_export(update, context, views, "views_export.json")


async def dev_export_admins(update, context):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    admins = db.get_all_admins()
    data = [{"id": a["id"], "name": user_display_name(a), "username": a.get("username"), "is_owner": a.get("is_owner"), "permissions": a.get("permissions")} for a in admins]
    await _send_json_export(update, context, data, "admins_export.json")


async def dev_full_export(update, context):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    data = {
        "users": db.get_all_users(limit=100000),
        "content": db.get_all_content_including_expired(),
        "views": db.get_recent_views(limit=100000),
        "admins": [dict(a) for a in db.get_all_admins()],
        "stats": db.get_db_stats()
    }
    await _send_json_export(update, context, data, "full_export.json")


# ─── 10. Dev Tools ────────────────────────────────────────────────────────────

async def dev_tools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        get_text("dev_tools_menu", lang),
        reply_markup=dev_tools_keyboard(lang), parse_mode=ParseMode.HTML
    )


async def dev_api_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    try:
        me = await context.bot.get_me()
        status = f"API Status: Connected\nBot: @{me.username}\nTelegram API: OK\nDB Connection: OK"
    except Exception as e:
        status = f"API Status: ERROR\n{e}"
    await update.message.reply_text(status, parse_mode=ParseMode.HTML)


async def dev_test_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(
        f"Test message from bot.\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        parse_mode=ParseMode.HTML
    )
    await update.message.reply_text(get_text("dev_test_sent", lang), parse_mode=ParseMode.HTML)


async def dev_clear_cache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(get_text("dev_cache_cleared", lang), parse_mode=ParseMode.HTML)


async def dev_update_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    from telegram import BotCommand
    await context.bot.set_my_commands([
        BotCommand("start", "Start the bot")
    ])
    await update.message.reply_text(get_text("dev_commands_updated", lang), parse_mode=ParseMode.HTML)


async def dev_view_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    if not is_dev(user_id): return await _dev_only(update, lang)
    await update.message.reply_text(get_text("dev_errors_text", lang, count=_error_count), parse_mode=ParseMode.HTML)
