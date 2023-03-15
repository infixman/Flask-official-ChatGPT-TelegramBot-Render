import json
import logging
import openai
import os
import telegram
from fastapi import FastAPI, Request
from telegram.ext import Dispatcher, MessageHandler, Filters

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_BOT = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
DISPATCHER = Dispatcher(TG_BOT, None)
LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")

app = FastAPI()
openai.api_key = os.getenv("OPENAI_API_KEY")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=LOG_LEVEL)
logger = logging.getLogger(__name__)



CONVERSATIONS = {}

class ChatGPT:
    def __init__(self, session_id: str):
        self.model = os.getenv("OPENAI_MODEL", default="gpt-3.5-turbo")
        self.session_id = session_id

    def get_response(self, user_input):
        user_messages = []
        if self.session_id in CONVERSATIONS:
            user_messages = CONVERSATIONS.get(self.session_id)

        user_messages.append({"role": "user", "content": user_input})
        response = openai.ChatCompletion.create(
            model=self.model,
            messages = user_messages,
            user=self.session_id,
        )

        chatGPT_anserwer = response['choices'][0]['message']['content'].strip()
        user_messages.append({"role": "assistant", "content": chatGPT_anserwer})
        CONVERSATIONS[self.session_id] = user_messages
        
        logger.info(f"""
Session: {self.session_id}
👨‍:{user_input}
🤖:{chatGPT_anserwer}""")

        return chatGPT_anserwer


@app.post("/callback")
async def webhook_handler(request: Request):
    data = await request.json()
    logger.info(f"request data: {json.dumps(data)}")
    update = telegram.Update.de_json(data, TG_BOT)
    DISPATCHER.process_update(update)
    return "ok"


def reply_handler(bot, update):
    session_id = f"{update.message.chat.id}-{update.message.from_user.id}"
    chatgpt = ChatGPT(session_id)
    chatGPT_anserwer = chatgpt.get_response(update.message.text)
    update.message.reply_text(chatGPT_anserwer)

DISPATCHER.add_handler(MessageHandler(Filters.text, reply_handler))

if __name__ == "__main__":
    app.run(debug=True)
