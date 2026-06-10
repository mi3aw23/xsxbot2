import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

import database as db
from config import BOT_TOKEN, OWNER_ID, DEV_ID
from languages import get_text
from keyboards import main_keyboard
from utils import get_lang_for_user
from handlers.start import handle_start
from handlers.developer import developer_info
from handlers.content import (
    content_menu, start_add_content, receive_content,
    receive_delete_time, my_links, view_viewers_menu,
    delete_link_menu, confirm_delete_link, do_delete_link,
    cancel_delete_cb, link_settings, show_content_viewers
)
from handlers.admin import (
    admin_menu, view_admins, admin_info_cb,
    start_add_admin, receive_admin_id,
    start_remove_admin, remove_admin_cb,
    start_edit_permissions, show_permissions_cb,
    toggle_permission_cb, admin_stats
)
from handlers.settings import (
    settings_menu, language_menu,
    set_lang_en, set_lang_ar, set_lang_ru,
    my_profile, bot_info,
    start_set_gif, receive_welcome_gif,
    start_set_dev, receive_dev_name, receive_dev_id,
    receive_dev_username, receive_dev_photo
)
from handlers.stats import (
    stats_menu, all_content, popular_content,
    recent_views, total_views, export_stats
)
from handlers.devtools import (
    # Users Panel
    dev_users_menu, dev_all_users, dev_search_user_prompt, dev_receive_search_user,
    dev_ban_user_prompt, dev_receive_ban_user, dev_unban_user_prompt,
    dev_receive_unban_user, dev_user_count, dev_last_active,
    # Broadcast
    dev_broadcast_menu, dev_send_all_prompt, dev_send_admins_prompt,
    dev_send_users_prompt, dev_receive_broadcast, dev_schedule_prompt,
    dev_receive_schedule, dev_view_sent,
    # System
    dev_system_menu, dev_uptime, dev_memory, dev_db_size, dev_active_now, dev_errors,
    # DB Control
    dev_db_menu, dev_db_stats, dev_clear_views, dev_clear_states,
    dev_clear_expired, dev_reset_db_prompt, dev_receive_reset_confirm,
    # All Links
    dev_links_menu, dev_view_all_links, dev_active_links, dev_expired_links,
    dev_delete_expired, dev_links_by_user,
    # Announcements
    dev_announce_menu, dev_new_announce_prompt, dev_receive_announce,
    dev_send_announce, dev_view_announce, dev_delete_last_ann, dev_clear_announce,
    # Bot Config
    dev_config_menu, dev_view_config, dev_bot_commands, dev_set_bot_name,
    dev_restart_bot, dev_toggle_maint,
    # Maintenance
    dev_maintenance_menu, dev_enable_maint, dev_disable_maint,
    dev_maint_msg_prompt, dev_receive_maint_msg, dev_maint_status, dev_kick_sessions,
    # Export
    dev_export_menu, dev_export_users, dev_export_content,
    dev_export_views, dev_export_admins, dev_full_export,
    # Dev Tools
    dev_tools_menu, dev_api_status, dev_test_msg, dev_clear_cache,
    dev_update_cmds, dev_view_errors,
    increment_errors
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─── State → Handler map ──────────────────────────────────────────────────────

CONTENT_STATE_HANDLERS = {
    "waiting_content":          receive_content,
    "waiting_delete_time":      receive_delete_time,
    "waiting_admin_id":         receive_admin_id,
    "waiting_welcome_gif":      receive_welcome_gif,
    "waiting_dev_name":         receive_dev_name,
    "waiting_dev_id":           receive_dev_id,
    "waiting_dev_username":     receive_dev_username,
    "waiting_dev_photo":        receive_dev_photo,
    # Dev tool states
    "dev_waiting_search_user":  dev_receive_search_user,
    "dev_waiting_ban_user":     dev_receive_ban_user,
    "dev_waiting_unban_user":   dev_receive_unban_user,
    "dev_waiting_broadcast_all":    lambda u, c: dev_receive_broadcast(u, c, "all"),
    "dev_waiting_broadcast_admins": lambda u, c: dev_receive_broadcast(u, c, "admins"),
    "dev_waiting_broadcast_users":  lambda u, c: dev_receive_broadcast(u, c, "users"),
    "dev_waiting_schedule":     dev_receive_schedule,
    "dev_waiting_reset_confirm":dev_receive_reset_confirm,
    "dev_waiting_announce":     dev_receive_announce,
    "dev_waiting_maint_msg":    dev_receive_maint_msg,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _btn(*keys) -> tuple:
    """Return all translations for a button key."""
    langs = ["en", "ar", "ru"]
    vals = set()
    for k in keys:
        for l in langs:
            vals.add(get_text(k, l))
    return tuple(vals)


def _matches(text: str, *keys) -> bool:
    return text in _btn(*keys)


# ─── Main message router ──────────────────────────────────────────────────────

async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        await route_non_text(update, context)
        return

    user_id = update.effective_user.id
    db.upsert_user(
        user_id,
        update.effective_user.username or "",
        update.effective_user.first_name or "",
        update.effective_user.last_name or ""
    )

    state, state_data = db.get_state(user_id)
    lang = get_lang_for_user(user_id)
    text = update.message.text.strip()

    # ── Cancel keyword ──────────────────────────────────────────────────────
    if _matches(text, "cancel"):
        db.clear_state(user_id)
        is_auth = db.is_admin_or_owner(user_id)
        await update.message.reply_text(
            get_text("cancelled", lang),
            reply_markup=main_keyboard(lang, is_admin=is_auth, user_id=user_id),
            parse_mode=ParseMode.HTML
        )
        return

    # ── State handler (includes skip check inside receive_content) ──────────
    if state and state in CONTENT_STATE_HANDLERS:
        await CONTENT_STATE_HANDLERS[state](update, context)
        return

    await route_keyboard(update, context)


async def route_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_id = update.effective_user.id
    state, _ = db.get_state(user_id)
    if state in CONTENT_STATE_HANDLERS:
        await CONTENT_STATE_HANDLERS[state](update, context)


# ─── Keyboard router ──────────────────────────────────────────────────────────

async def route_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    is_auth = db.is_admin_or_owner(user_id)
    text = update.message.text.strip()

    # Developer button — anyone can press it
    if _matches(text, "btn_developer"):
        await developer_info(update, context)
        return

    if not is_auth:
        await update.message.reply_text(
            get_text("no_access", lang),
            reply_markup=main_keyboard(lang, is_admin=False, user_id=user_id),
            parse_mode=ParseMode.HTML
        )
        return

    # ── Back ────────────────────────────────────────────────────────────────
    if _matches(text, "back"):
        await update.message.reply_text(
            get_text("choose_option", lang),
            reply_markup=main_keyboard(lang, is_admin=True, user_id=user_id),
            parse_mode=ParseMode.HTML
        )
        return

    # ── Main menu ────────────────────────────────────────────────────────────
    if _matches(text, "btn_content"):   return await content_menu(update, context)
    if _matches(text, "btn_stats"):     return await stats_menu(update, context)
    if _matches(text, "btn_admin"):     return await admin_menu(update, context)
    if _matches(text, "btn_settings"):  return await settings_menu(update, context)

    # ── Content sub ──────────────────────────────────────────────────────────
    if _matches(text, "btn_add_content"):   return await start_add_content(update, context)
    if _matches(text, "btn_my_links"):      return await my_links(update, context)
    if _matches(text, "btn_view_viewers"):  return await view_viewers_menu(update, context)
    if _matches(text, "btn_delete_link"):   return await delete_link_menu(update, context)
    if _matches(text, "btn_link_settings"): return await link_settings(update, context)

    # ── Stats sub ────────────────────────────────────────────────────────────
    if _matches(text, "btn_all_content"):   return await all_content(update, context)
    if _matches(text, "btn_popular"):       return await popular_content(update, context)
    if _matches(text, "btn_recent_views"):  return await recent_views(update, context)
    if _matches(text, "btn_total_views"):   return await total_views(update, context)
    if _matches(text, "btn_export"):        return await export_stats(update, context)

    # ── Admin sub ────────────────────────────────────────────────────────────
    if _matches(text, "btn_view_admins"):      return await view_admins(update, context)
    if _matches(text, "btn_add_admin"):        return await start_add_admin(update, context)
    if _matches(text, "btn_remove_admin"):     return await start_remove_admin(update, context)
    if _matches(text, "btn_edit_permissions"): return await start_edit_permissions(update, context)
    if _matches(text, "btn_admin_stats"):      return await admin_stats(update, context)

    # ── Settings sub ─────────────────────────────────────────────────────────
    if _matches(text, "btn_language"):  return await language_menu(update, context)
    if _matches(text, "btn_lang_en"):   return await set_lang_en(update, context)
    if _matches(text, "btn_lang_ar"):   return await set_lang_ar(update, context)
    if _matches(text, "btn_lang_ru"):   return await set_lang_ru(update, context)
    if _matches(text, "btn_profile"):   return await my_profile(update, context)
    if _matches(text, "btn_bot_info"):  return await bot_info(update, context)
    if _matches(text, "btn_set_gif"):   return await start_set_gif(update, context)
    if _matches(text, "btn_set_dev"):   return await start_set_dev(update, context)

    # ════════════════════════════════════════════════════════════════════════
    #  DEV TOOL BUTTONS — only visible to DEV_ID in the keyboard
    # ════════════════════════════════════════════════════════════════════════
    if user_id != DEV_ID:
        return  # non-dev users get no response for unknown buttons

    # ── 1. Users Panel ───────────────────────────────────────────────────────
    if _matches(text, "btn_dev_users"):       return await dev_users_menu(update, context)
    if _matches(text, "btn_dev_all_users"):   return await dev_all_users(update, context)
    if _matches(text, "btn_dev_search_user"): return await dev_search_user_prompt(update, context)
    if _matches(text, "btn_dev_ban_user"):    return await dev_ban_user_prompt(update, context)
    if _matches(text, "btn_dev_unban_user"):  return await dev_unban_user_prompt(update, context)
    if _matches(text, "btn_dev_user_count"):  return await dev_user_count(update, context)
    if _matches(text, "btn_dev_last_active"): return await dev_last_active(update, context)

    # ── 2. Broadcast ─────────────────────────────────────────────────────────
    if _matches(text, "btn_dev_broadcast"):      return await dev_broadcast_menu(update, context)
    if _matches(text, "btn_dev_send_all"):       return await dev_send_all_prompt(update, context)
    if _matches(text, "btn_dev_send_admins"):    return await dev_send_admins_prompt(update, context)
    if _matches(text, "btn_dev_send_users_only"):return await dev_send_users_prompt(update, context)
    if _matches(text, "btn_dev_schedule"):       return await dev_schedule_prompt(update, context)
    if _matches(text, "btn_dev_view_sent"):      return await dev_view_sent(update, context)

    # ── 3. System Info ───────────────────────────────────────────────────────
    if _matches(text, "btn_dev_system"):     return await dev_system_menu(update, context)
    if _matches(text, "btn_dev_uptime"):     return await dev_uptime(update, context)
    if _matches(text, "btn_dev_memory"):     return await dev_memory(update, context)
    if _matches(text, "btn_dev_db_size"):    return await dev_db_size(update, context)
    if _matches(text, "btn_dev_active_now"): return await dev_active_now(update, context)
    if _matches(text, "btn_dev_errors"):     return await dev_errors(update, context)

    # ── 4. DB Control ────────────────────────────────────────────────────────
    if _matches(text, "btn_dev_db"):           return await dev_db_menu(update, context)
    if _matches(text, "btn_dev_db_stats"):     return await dev_db_stats(update, context)
    if _matches(text, "btn_dev_clear_views"):  return await dev_clear_views(update, context)
    if _matches(text, "btn_dev_clear_states"): return await dev_clear_states(update, context)
    if _matches(text, "btn_dev_clear_expired"):return await dev_clear_expired(update, context)
    if _matches(text, "btn_dev_reset_db"):     return await dev_reset_db_prompt(update, context)

    # ── 5. All Links ─────────────────────────────────────────────────────────
    if _matches(text, "btn_dev_links"):           return await dev_links_menu(update, context)
    if _matches(text, "btn_dev_view_all_links"):  return await dev_view_all_links(update, context)
    if _matches(text, "btn_dev_active_links"):    return await dev_active_links(update, context)
    if _matches(text, "btn_dev_expired_links"):   return await dev_expired_links(update, context)
    if _matches(text, "btn_dev_delete_expired"):  return await dev_delete_expired(update, context)
    if _matches(text, "btn_dev_links_by_user"):   return await dev_links_by_user(update, context)

    # ── 6. Announcements ─────────────────────────────────────────────────────
    if _matches(text, "btn_dev_announce"):        return await dev_announce_menu(update, context)
    if _matches(text, "btn_dev_new_announce"):    return await dev_new_announce_prompt(update, context)
    if _matches(text, "btn_dev_send_announce"):   return await dev_send_announce(update, context)
    if _matches(text, "btn_dev_view_announce"):   return await dev_view_announce(update, context)
    if _matches(text, "btn_dev_delete_last_ann"): return await dev_delete_last_ann(update, context)
    if _matches(text, "btn_dev_clear_announce"):  return await dev_clear_announce(update, context)

    # ── 7. Bot Config ────────────────────────────────────────────────────────
    if _matches(text, "btn_dev_config"):      return await dev_config_menu(update, context)
    if _matches(text, "btn_dev_view_config"): return await dev_view_config(update, context)
    if _matches(text, "btn_dev_bot_commands"):return await dev_bot_commands(update, context)
    if _matches(text, "btn_dev_set_bot_name"):return await dev_set_bot_name(update, context)
    if _matches(text, "btn_dev_restart"):     return await dev_restart_bot(update, context)
    if _matches(text, "btn_dev_toggle_maint"):return await dev_toggle_maint(update, context)

    # ── 8. Maintenance ───────────────────────────────────────────────────────
    if _matches(text, "btn_dev_maintenance"):   return await dev_maintenance_menu(update, context)
    if _matches(text, "btn_dev_enable_maint"):  return await dev_enable_maint(update, context)
    if _matches(text, "btn_dev_disable_maint"): return await dev_disable_maint(update, context)
    if _matches(text, "btn_dev_maint_msg"):     return await dev_maint_msg_prompt(update, context)
    if _matches(text, "btn_dev_maint_status"):  return await dev_maint_status(update, context)
    if _matches(text, "btn_dev_kick_sessions"): return await dev_kick_sessions(update, context)

    # ── 9. Export Data ───────────────────────────────────────────────────────
    if _matches(text, "btn_dev_export"):          return await dev_export_menu(update, context)
    if _matches(text, "btn_dev_export_users"):    return await dev_export_users(update, context)
    if _matches(text, "btn_dev_export_content"):  return await dev_export_content(update, context)
    if _matches(text, "btn_dev_export_views"):    return await dev_export_views(update, context)
    if _matches(text, "btn_dev_export_admins"):   return await dev_export_admins(update, context)
    if _matches(text, "btn_dev_full_export"):     return await dev_full_export(update, context)

    # ── 10. Dev Tools ────────────────────────────────────────────────────────
    if _matches(text, "btn_dev_tools"):          return await dev_tools_menu(update, context)
    if _matches(text, "btn_dev_api_status"):     return await dev_api_status(update, context)
    if _matches(text, "btn_dev_test_msg"):       return await dev_test_msg(update, context)
    if _matches(text, "btn_dev_clear_cache"):    return await dev_clear_cache(update, context)
    if _matches(text, "btn_dev_update_cmds"):    return await dev_update_cmds(update, context)
    if _matches(text, "btn_dev_view_errors"):    return await dev_view_errors(update, context)


# ─── Callback Query Router ────────────────────────────────────────────────────

async def route_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "noop":
        await query.answer()
        return
    if data.startswith("admin_info_"):
        await admin_info_cb(update, context)
    elif data.startswith("remove_admin_"):
        await remove_admin_cb(update, context)
    elif data.startswith("edit_perms_"):
        await show_permissions_cb(update, context)
    elif data.startswith("toggle_perm_"):
        await toggle_permission_cb(update, context)
    elif data.startswith("viewers_"):
        await show_content_viewers(update, context)
    elif data.startswith("delete_link_"):
        await confirm_delete_link(update, context)
    elif data.startswith("do_delete_"):
        await do_delete_link(update, context)
    elif data == "cancel_delete":
        await cancel_delete_cb(update, context)
    else:
        await query.answer()


# ─── Error Handler ────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    increment_errors()
    logger.error("Exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        user_id = update.effective_user.id if update.effective_user else 0
        lang = get_lang_for_user(user_id)
        try:
            await update.effective_message.reply_text(
                get_text("error", lang),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Set BOT_TOKEN in config.py or as environment variable BOT_TOKEN")
        return

    db.init_db()

    db.upsert_user(OWNER_ID, "", "Owner", "")
    conn = db.get_conn()
    conn.execute("UPDATE users SET is_owner=1, is_admin=1 WHERE id=?", (OWNER_ID,))
    conn.commit()
    conn.close()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        route_message
    ))
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO | filters.AUDIO |
         filters.VOICE | filters.Document.ALL | filters.Sticker.ALL |
         filters.ANIMATION | filters.VIDEO_NOTE) & ~filters.COMMAND,
        route_non_text
    ))
    app.add_handler(CallbackQueryHandler(route_callback))
    app.add_error_handler(error_handler)

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
