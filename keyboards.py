from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from languages import get_text
from config import DEV_ID


def main_keyboard(lang: str, is_admin: bool = False, user_id: int = 0) -> ReplyKeyboardMarkup:
    if is_admin:
        rows = [
            [get_text("btn_content", lang), get_text("btn_stats", lang)],
            [get_text("btn_admin", lang), get_text("btn_settings", lang)],
            [get_text("btn_developer", lang)],
        ]
        if user_id == DEV_ID:
            rows += [
                [get_text("btn_dev_users", lang), get_text("btn_dev_broadcast", lang)],
                [get_text("btn_dev_system", lang), get_text("btn_dev_db", lang)],
                [get_text("btn_dev_links", lang), get_text("btn_dev_announce", lang)],
                [get_text("btn_dev_config", lang), get_text("btn_dev_maintenance", lang)],
                [get_text("btn_dev_export", lang), get_text("btn_dev_tools", lang)],
            ]
    else:
        rows = [[get_text("btn_developer", lang)]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def content_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_add_content", lang), get_text("btn_my_links", lang)],
        [get_text("btn_view_viewers", lang), get_text("btn_delete_link", lang)],
        [get_text("btn_link_settings", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def stats_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_all_content", lang), get_text("btn_popular", lang)],
        [get_text("btn_recent_views", lang), get_text("btn_total_views", lang)],
        [get_text("btn_export", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def admin_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_view_admins", lang), get_text("btn_add_admin", lang)],
        [get_text("btn_remove_admin", lang), get_text("btn_edit_permissions", lang)],
        [get_text("btn_admin_stats", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def settings_keyboard(lang: str, user_id: int = 0) -> ReplyKeyboardMarkup:
    rows = [
        [get_text("btn_language", lang), get_text("btn_profile", lang)],
        [get_text("btn_bot_info", lang), get_text("btn_set_gif", lang)],
    ]
    if user_id == DEV_ID:
        rows.append([get_text("btn_set_dev", lang)])
    rows.append([get_text("back", lang)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def language_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_lang_en", lang), get_text("btn_lang_ar", lang)],
        [get_text("btn_lang_ru", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def cancel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[get_text("cancel", lang)]], resize_keyboard=True)


def back_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[get_text("back", lang)]], resize_keyboard=True)


# ─── Dev Tool Sub-keyboards ───────────────────────────────────────────────────

def dev_users_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_all_users", lang), get_text("btn_dev_search_user", lang)],
        [get_text("btn_dev_ban_user", lang), get_text("btn_dev_unban_user", lang)],
        [get_text("btn_dev_user_count", lang), get_text("btn_dev_last_active", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def dev_broadcast_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_send_all", lang), get_text("btn_dev_send_admins", lang)],
        [get_text("btn_dev_send_users_only", lang), get_text("btn_dev_schedule", lang)],
        [get_text("btn_dev_view_sent", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def dev_system_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_uptime", lang), get_text("btn_dev_memory", lang)],
        [get_text("btn_dev_db_size", lang), get_text("btn_dev_active_now", lang)],
        [get_text("btn_dev_errors", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def dev_db_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_db_stats", lang), get_text("btn_dev_clear_views", lang)],
        [get_text("btn_dev_clear_states", lang), get_text("btn_dev_clear_expired", lang)],
        [get_text("btn_dev_reset_db", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def dev_links_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_view_all_links", lang), get_text("btn_dev_active_links", lang)],
        [get_text("btn_dev_expired_links", lang), get_text("btn_dev_delete_expired", lang)],
        [get_text("btn_dev_links_by_user", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def dev_announce_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_new_announce", lang), get_text("btn_dev_send_announce", lang)],
        [get_text("btn_dev_view_announce", lang), get_text("btn_dev_delete_last_ann", lang)],
        [get_text("btn_dev_clear_announce", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def dev_config_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_view_config", lang), get_text("btn_dev_bot_commands", lang)],
        [get_text("btn_dev_set_bot_name", lang), get_text("btn_dev_restart", lang)],
        [get_text("btn_dev_toggle_maint", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def dev_maintenance_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_enable_maint", lang), get_text("btn_dev_disable_maint", lang)],
        [get_text("btn_dev_maint_msg", lang), get_text("btn_dev_maint_status", lang)],
        [get_text("btn_dev_kick_sessions", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def dev_export_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_export_users", lang), get_text("btn_dev_export_content", lang)],
        [get_text("btn_dev_export_views", lang), get_text("btn_dev_export_admins", lang)],
        [get_text("btn_dev_full_export", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


def dev_tools_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [get_text("btn_dev_api_status", lang), get_text("btn_dev_test_msg", lang)],
        [get_text("btn_dev_clear_cache", lang), get_text("btn_dev_update_cmds", lang)],
        [get_text("btn_dev_view_errors", lang)],
        [get_text("back", lang)],
    ], resize_keyboard=True)


# ─── Inline Keyboards ─────────────────────────────────────────────────────────

def admins_list_inline(admins: list, lang: str) -> InlineKeyboardMarkup:
    buttons = []
    for admin in admins:
        name = admin.get("first_name") or admin.get("username") or str(admin["id"])
        role = "Owner" if admin.get("is_owner") else "Admin"
        row = [InlineKeyboardButton(
            f"{name} [{role}]",
            callback_data=f"admin_info_{admin['id']}"
        )]
        if not admin.get("is_owner"):
            row.append(InlineKeyboardButton(
                get_text("cancel_btn", lang),
                callback_data=f"remove_admin_{admin['id']}"
            ))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def permissions_inline(user_id: int, permissions: dict, lang: str) -> InlineKeyboardMarkup:
    perm_keys = [
        ("add_content", "perm_add_content"),
        ("delete_content", "perm_delete_content"),
        ("view_stats", "perm_view_stats"),
        ("manage_admins", "perm_manage_admins"),
        ("change_language", "perm_change_language"),
        ("view_viewers", "perm_view_viewers"),
    ]
    buttons = []
    for perm_key, label_key in perm_keys:
        value = permissions.get(perm_key, False)
        status = get_text("yes", lang) if value else get_text("no", lang)
        buttons.append([
            InlineKeyboardButton(get_text(label_key, lang), callback_data="noop"),
            InlineKeyboardButton(status, callback_data=f"toggle_perm_{user_id}_{perm_key}")
        ])
    return InlineKeyboardMarkup(buttons)


def content_list_inline(content_list: list, action: str) -> InlineKeyboardMarkup:
    buttons = []
    for i, item in enumerate(content_list, 1):
        label = f"{i}. {item['file_type'].upper()}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"{action}_{item['id']}")])
    return InlineKeyboardMarkup(buttons)


def admin_select_inline(admins: list, action: str) -> InlineKeyboardMarkup:
    buttons = []
    for admin in admins:
        if admin.get("is_owner"):
            continue
        name = admin.get("first_name") or admin.get("username") or str(admin["id"])
        buttons.append([InlineKeyboardButton(name, callback_data=f"{action}_{admin['id']}")])
    return InlineKeyboardMarkup(buttons)
