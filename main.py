import asyncio
import logging
import os
from uuid import uuid4

from telegram import ChatPermissions, Message, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app import chatbot, line_gift

LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT"))
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL)
logger = logging.getLogger(__name__)

APPLICATION = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


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
    if len(paras) == 2:
        target_rate = float(paras[1])
        if target_rate >= 1:
            reply_msg: Message = await update.message.reply_text("loading ...")
            asyncio.create_task(line_gift.crawl_line_gifts(target_rate, context.bot, reply_msg))


async def telegram_error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    logger.debug("[TG BOT START]")
    APPLICATION.add_handler(MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=text_message_handler))
    APPLICATION.add_handler(MessageHandler(filters=filters.StatusUpdate.NEW_CHAT_MEMBERS, callback=chat_member_handler))
    APPLICATION.add_handler(CommandHandler(command="lp", callback=command_lp_handler))
    APPLICATION.add_error_handler(telegram_error_handler)

    # APPLICATION.run_polling()

    # https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}
    # https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo
    APPLICATION.run_webhook(
        listen="0.0.0.0",
        port=WEBHOOK_PORT,
        secret_token=uuid4().hex,
        webhook_url=WEBHOOK_URL,
    )


if __name__ == "__main__":
    main()
