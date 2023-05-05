import json
import logging
import os

from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, MessageHandler, Updater, filters

import app.chatbot as chatbot
import app.line_point as line_point
import app.util as util
from app.chatgpt import ChatGPT

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_BOT = Bot(token=TELEGRAM_BOT_TOKEN)
UPDATER = Updater(bot=TG_BOT, use_context=True)
LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")

app = FastAPI()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL)
logger = logging.getLogger(__name__)

@app.post("/callback")
async def webhook_handler(request: Request):
    request_body = await request.json()
    logger.info(f"request_body: {json.dumps(request_body)}")
    update = Update.de_json(request_body, UPDATER.bot)
    UPDATER.dispatcher.process_update(update)
    return "ok"


def text_message_handler(_, update: Update):
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


def command_u_handler(_, update: Update):
    update.message.reply_text(f"{util.get_usdt()}\n\n{util.get_usd_rate()}")


async def command_lp_handler(_, update: Update):
    answer = ""
    paras = update.message.text.upper().split(" ")
    if len(paras) == 3:
        answer = await line_point.get_answer(paras[1], paras[2])
    else:
        answer = await line_point.get_answer()

    update.message.reply_text(answer, parse_mode=ParseMode.MARKDOWN)

UPDATER.dispatcher.add_handler(MessageHandler(filters=filters.Text, callback=text_message_handler))
UPDATER.dispatcher.add_handler(CommandHandler(command="u", callback=command_u_handler))
UPDATER.dispatcher.add_handler(CommandHandler(command="lp", callback=command_lp_handler, run_async=True))
