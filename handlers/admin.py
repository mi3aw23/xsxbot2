from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from languages import get_text
from keyboards import (admin_keyboard, cancel_keyboard,
                       admins_list_inline, permissions_inline, admin_select_inline)
from utils import get_lang_for_user, user_display_name, format_datetime
from config import OWNER_ID


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    await update.message.reply_text(
        get_text("choose_option", lang),
        reply_markup=admin_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


# ─── View Admins ──────────────────────────────────────────────────────────────

async def view_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    admins = db.get_all_admins()
    if not admins:
        await update.message.reply_text(get_text("no_admins", lang))
        return

    kb = admins_list_inline(admins, lang)
    await update.message.reply_text(
        get_text("admins_list", lang),
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


async def admin_info_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = get_lang_for_user(user_id)

    target_id = int(query.data.split("_")[2])
    target = db.get_user(target_id)
    if not target:
        await query.answer("User not found", show_alert=True)
        return

    name = user_display_name(target)
    role = "Owner" if target.get("is_owner") else "Admin"
    perms = target.get("permissions", {})
    perm_lines = []
    for k, v in perms.items():
        label = get_text(f"perm_{k}", lang)
        val = get_text("yes", lang) if v else get_text("no", lang)
        perm_lines.append(f"- {label}: {val}")

    text = (
        f'<a href="tg://user?id={target_id}">{name}</a>\n'
        f"Role: {role}\n"
        f"ID: <code>{target_id}</code>\n\n"
        f"Permissions:\n" + "\n".join(perm_lines)
    )
    await query.message.reply_text(text, parse_mode=ParseMode.HTML)


# ─── Add Admin ────────────────────────────────────────────────────────────────

async def start_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "manage_admins"):
        await update.message.reply_text(get_text("need_manage_perm", lang))
        return

    db.set_state(user_id, "waiting_admin_id")
    await update.message.reply_text(
        get_text("send_admin_id", lang),
        reply_markup=cancel_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


async def receive_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)
    msg = update.message

    state, _ = db.get_state(user_id)
    if state != "waiting_admin_id":
        return

    text = msg.text.strip()
    target = None

    if text.lstrip("@").isdigit():
        target = db.get_user(int(text))
    elif text.startswith("@"):
        target = db.get_user_by_username(text[1:])
    else:
        target = db.get_user_by_username(text)

    if not target:
        await msg.reply_text(get_text("user_not_found", lang))
        return

    if target.get("is_admin") or target.get("is_owner"):
        await msg.reply_text(get_text("already_admin", lang))
        db.clear_state(user_id)
        return

    db.add_admin(target["id"])
    db.clear_state(user_id)

    name = user_display_name(target)
    await msg.reply_text(
        f'{get_text("admin_added", lang)}\n\n<a href="tg://user?id={target["id"]}">{name}</a>',
        reply_markup=admin_keyboard(lang),
        parse_mode=ParseMode.HTML
    )


# ─── Remove Admin ─────────────────────────────────────────────────────────────

async def start_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "manage_admins"):
        await update.message.reply_text(get_text("need_manage_perm", lang))
        return

    admins = [a for a in db.get_all_admins() if not a.get("is_owner")]
    if not admins:
        await update.message.reply_text(get_text("no_admins", lang))
        return

    kb = admins_list_inline(admins, lang)
    await update.message.reply_text(
        get_text("admins_list", lang),
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


async def remove_admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "manage_admins"):
        await query.answer(get_text("need_manage_perm", lang), show_alert=True)
        return

    target_id = int(query.data.split("_")[2])

    if target_id == OWNER_ID:
        await query.answer(get_text("owner_cannot_remove", lang), show_alert=True)
        return

    if target_id == user_id:
        await query.answer(get_text("self_cannot_remove", lang), show_alert=True)
        return

    db.remove_admin(target_id)
    target = db.get_user(target_id)
    name = user_display_name(target) if target else str(target_id)

    await query.message.reply_text(
        f'{get_text("admin_removed", lang)}\n\n<a href="tg://user?id={target_id}">{name}</a>',
        parse_mode=ParseMode.HTML
    )

    await query.message.edit_reply_markup(reply_markup=None)


# ─── Edit Permissions ─────────────────────────────────────────────────────────

async def start_edit_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "manage_admins"):
        await update.message.reply_text(get_text("need_manage_perm", lang))
        return

    admins = [a for a in db.get_all_admins() if not a.get("is_owner")]
    if not admins:
        await update.message.reply_text(get_text("no_admins", lang))
        return

    kb = admin_select_inline(admins, "edit_perms")
    await update.message.reply_text(
        get_text("choose_admin_edit", lang),
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


async def show_permissions_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = get_lang_for_user(user_id)

    target_id = int(query.data.split("_")[2])
    target = db.get_user(target_id)
    if not target:
        await query.answer("User not found", show_alert=True)
        return

    perms = target.get("permissions", {})
    name = user_display_name(target)

    kb = permissions_inline(target_id, perms, lang)
    await query.message.reply_text(
        f'Permissions for <a href="tg://user?id={target_id}">{name}</a>:',
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )


async def toggle_permission_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = get_lang_for_user(user_id)

    if not db.get_user_permission(user_id, "manage_admins"):
        await query.answer(get_text("need_manage_perm", lang), show_alert=True)
        return

    parts = query.data.split("_", 3)
    target_id = int(parts[2])
    perm_key = parts[3]

    target = db.get_user(target_id)
    if not target:
        await query.answer("User not found", show_alert=True)
        return

    perms = target.get("permissions", {})
    perms[perm_key] = not perms.get(perm_key, False)
    db.update_permissions(target_id, perms)

    target = db.get_user(target_id)
    updated_perms = target.get("permissions", {})
    kb = permissions_inline(target_id, updated_perms, lang)
    await query.message.edit_reply_markup(reply_markup=kb)


# ─── Admin Stats ──────────────────────────────────────────────────────────────

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang_for_user(user_id)

    admins = db.get_all_admins()
    count = len(admins)
    active = db.count_active_admins_today()

    await update.message.reply_text(
        get_text("admin_stats_text", lang, count=count, active=active),
        parse_mode=ParseMode.HTML
    )
