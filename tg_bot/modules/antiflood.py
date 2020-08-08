import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql
import tg_bot.modules.sql.lang_sql as lang
from tg_bot.strings.string_helper import get_string

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(bot: Bot, update: Update) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if not user:  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        chat.kick_member(user.id)
        msg.reply_text(get_string("antiflood", "MSG_KICK", lang.get_lang(update.effective_chat.id))) # MSG_KICK

        return get_string("antiflood", "MSG_KICK_HTML", lang.get_lang(update.effective_chat.id)).format(html.escape(chat.title),
                                             mention_html(user.id, user.first_name)) # MSG_KICK_HTML

    except BadRequest:
        msg.reply_text(get_string("antiflood", "ERR_NO_PERMS", lang.get_lang(update.effective_chat.id))) # ERR_NO_PERMS
        sql.set_flood(chat.id, 0)
        return get_string("antiflood", "ERR_NO_PERMS_HTML", lang.get_lang(update.effective_chat.id)).format(chat.title) # ERR_NO_PERMS_HTML


@run_async
@user_admin
@can_restrict
@loggable
def set_flood(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat.id, 0)
            message.reply_text(get_string("antiflood", "MSG_DISABLED", lang.get_lang(update.effective_chat.id))) # MSG_DISABLED

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat.id, 0)
                message.reply_text(get_string("antiflood", "MSG_DISABLED", lang.get_lang(update.effective_chat.id))) # MSG_DISABLED
                return get_string("antiflood", "MSG_DISABLED_HTML", lang.get_lang(update.effective_chat.id)).format(html.escape(chat.title), mention_html(user.id, user.first_name)) # MSG_DISABLED_HTML

            elif amount < 3:
                message.reply_text(get_string("antiflood", "ERR_BAD_AMOUNT", lang.get_lang(update.effective_chat.id))) # ERR_BAD_AMOUNT
                return ""

            else:
                sql.set_flood(chat.id, amount)
                message.reply_text(get_string("antiflood", "MSG_SUCCESS", lang.get_lang(update.effective_chat.id)).format(amount)) # MSG_SUCCESS
                return get_string("antiflood", "MSG_SUCCESS_HTML", lang.get_lang(update.effective_chat.id)).format(html.escape(chat.title),
                                                                    mention_html(user.id, user.first_name), amount) # MSG_SUCCESS_HTML

        else:
            message.reply_text(get_string("antoflood", "ERR_BAD_REQUEST", lang.get_lang(update.effective_chat.id))) # ERR_BAD_REQUEST

    return ""


@run_async
def flood(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    limit = sql.get_flood_limit(chat.id)
    if limit == 0:
        update.effective_message.reply_text(get_string("antiflood", "MSG_DISABLED", lang.get_lang(update.effective_chat.id))) # MSG_DISABLED
    else:
        update.effective_message.reply_text(
            get_string("antiflood", "MSG_INFO", lang.get_lang(update.effective_chat.id)).format(limit)) # MSG_INFO


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return get_string("antiflood", "CHAT_SETTINGS_OFF", lang.get_lang(chat_id)) # CHAT_SETTINGS_OFF
    else:
        return get_string("antiflood", "CHAT_SETTINGS_ON", lang.get_lang(chat_id)).format(limit) # CHAT_SETTINGS_ON


def __help__(update: Update) -> str:
    return get_string("antiflood", "HELP", lang.get_lang(update.effective_chat.id))

__mod_name__ = "AntiFlood"

FLOOD_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_flood)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, pass_args=True, filters=Filters.group)
FLOOD_HANDLER = CommandHandler("flood", flood, filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
