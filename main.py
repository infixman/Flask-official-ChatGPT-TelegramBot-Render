import asyncio
import logging
import os

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import app.chatbot as chatbot
import app.line_point as line_point
import app.util as util
from app.chatgpt import ChatGPT

LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL)
logger = logging.getLogger(__name__)

def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    user_id = str(update.message.from_user.id)
    user_message = str(update.message.text).strip()
    is_need_ask_chatgpt = False

    # private chat
    if chat_id == user_id:
        is_need_ask_chatgpt = True
    # group chat
    elif user_message.upper().startswith("Q:") and len(user_message) > 2:
        is_need_ask_chatgpt = True
        user_message = user_message[3:].strip()

    if is_need_ask_chatgpt:
        chatgpt = ChatGPT(chat_id)
        chatgpt_anserwer = chatgpt.get_response(user_message)
        update.message.reply_text(chatgpt_anserwer)
    else:
        chatbot.reply(update)


def command_u_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text(f"{util.get_usdt()}\n\n{util.get_usd_rate()}")


def command_lp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = ""
    paras = update.message.text.upper().split(" ")
    if len(paras) == 3:
        answer = asyncio.run(line_point.get_answer(paras[1], paras[2]))
    else:
        answer = asyncio.run(line_point.get_answer())

    update.message.reply_text(answer, parse_mode=ParseMode.MARKDOWN)

def main():
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(telegram_bot_token).build()

    application.add_handler(MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=text_message_handler))
    application.add_handler(CommandHandler(command="u", callback=command_u_handler))
    application.add_handler(CommandHandler(command="lp", callback=command_lp_handler))
    
    application.run_polling()

if __name__ == "__main__":
    main()
    