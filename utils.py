import uuid
import asyncio
from datetime import datetime
from telegram import Bot
from config import OWNER_ID
import database as db


def generate_code() -> str:
    return uuid.uuid4().hex[:12]


def make_link(bot_username: str, code: str) -> str:
    return f"https://t.me/{bot_username}?start=view_{code}"


def format_name_link(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'


def user_display_name(user) -> str:
    if hasattr(user, "first_name"):
        name = user.first_name or ""
        if user.last_name:
            name += f" {user.last_name}"
        return name.strip() or user.username or str(user.id)
    name = user.get("first_name") or ""
    if user.get("last_name"):
        name += f" {user['last_name']}"
    return name.strip() or user.get("username") or str(user.get("id", ""))


def get_user_role(user: dict, lang: str) -> str:
    from languages import get_text
    if user.get("is_owner"):
        return get_text("role_owner", lang)
    if user.get("is_admin"):
        return get_text("role_admin", lang)
    return get_text("role_member", lang)


def get_lang_for_user(user_id: int) -> str:
    user = db.get_user(user_id)
    if not user:
        return "en"
    if user.get("is_owner") or user.get("is_admin"):
        return user.get("lang", "en")
    return "en"


def require_admin(func):
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if not db.is_admin_or_owner(user_id):
            lang = get_lang_for_user(user_id)
            from languages import get_text
            await update.effective_message.reply_text(
                get_text("no_access", lang),
                parse_mode="HTML"
            )
            return
        return await func(update, context, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


async def schedule_delete(bot: Bot, chat_id: int, message_ids: list, delay: int):
    await asyncio.sleep(delay)
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass


def get_file_type_label(file_type: str) -> str:
    labels = {
        "photo": "Photo",
        "video": "Video",
        "audio": "Audio",
        "voice": "Voice",
        "document": "Document",
        "sticker": "Sticker",
        "animation": "GIF/Animation",
        "text": "Text",
        "video_note": "Video Note",
    }
    return labels.get(file_type, file_type.capitalize())


def format_datetime(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str or "N/A"
