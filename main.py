import logging
import os

from telegram import ChatPermissions, Message, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app import chatbot, line_gift

LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL)
logger = logging.getLogger(__name__)


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    chat_name = str(update.message.chat.full_name)
    user_id = str(update.message.from_user.id)
    user_name = str(update.message.from_user.name)
    user_full_name = str(update.message.from_user.full_name)
    user_message = str(update.message.text).strip()
    logger.debug(
        f"[NEW MESSAGE] chat_id:{chat_id}, chat_name:{chat_name}, user_id:{user_id}, user_name:{user_name}, user_full_name:{user_full_name}, user_message:{user_message}"
    )
    await chatbot.reply(update)


async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    for user in update.message.new_chat_members:
        user_id = str(user.id)
        user_name = str(user.name)
        user_full_name = str(user.full_name)
        chat_id = str(chat.id)
        chat_name = str(chat.full_name)

        if (
            "网" in user_full_name
            and "月" in user_full_name
            and "万" in user_full_name
            and ("暗" in user_full_name or "黑" in user_full_name)
        ):
            await context.bot.restrict_chat_member(chat.id, user.id, permissions=ChatPermissions())
            await context.bot.ban_chat_member(chat_id=chat.id, user_id=user.id)

            logger.debug(
                f"[BAN MEMBER] chat_id:{chat_id}, chat_name:{chat_name}, user_id:{user_id}, user_name:{user_name}, user_full_name:{user_full_name}"
            )
        else:
            logger.debug(
                f"[NEW MEMBER] chat_id:{chat_id}, chat_name:{chat_name}, user_id:{user_id}, user_name:{user_name}, user_full_name:{user_full_name}"
            )


async def command_lp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    paras = update.message.text.upper().split(" ")
    reply_msg: Message = await update.message.reply_text("loading ...")
    if len(paras) == 2:
        target_rate = float(paras[1])
        if target_rate >= 1:
            msg = await line_gift.crawl_line_gifts(target_rate, context.bot, reply_msg)
            await context.bot.edit_message_text(
                chat_id=reply_msg.chat_id, message_id=reply_msg.message_id, text=msg, parse_mode=ParseMode.MARKDOWN
            )


async def telegram_error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(telegram_bot_token).build()

    application.add_handler(MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=text_message_handler))
    application.add_handler(MessageHandler(filters=filters.StatusUpdate.NEW_CHAT_MEMBERS, callback=chat_member_handler))
    application.add_handler(CommandHandler(command="lp", callback=command_lp_handler))
    application.add_error_handler(telegram_error_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
