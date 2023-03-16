import json
import logging
import os

import telegram
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import CommandHandler, Dispatcher, Filters, MessageHandler

import app.chatbot as chatbot
import app.util as util
from app.chatgpt import ChatGPT

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_BOT = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
DISPATCHER = Dispatcher(TG_BOT, None)
LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")

app = FastAPI()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL)
logger = logging.getLogger(__name__)

@app.post("/callback")
async def webhook_handler(request: Request):
    request_body = await request.json()
    logger.info(f"request_body: {json.dumps(request_body)}")
    update = Update.de_json(request_body, TG_BOT)
    DISPATCHER.process_update(update)
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

DISPATCHER.add_handler(MessageHandler(filters=Filters.text, callback=text_message_handler))
DISPATCHER.add_handler(CommandHandler(command="u", callback=command_u_handler))
