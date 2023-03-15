import json
import logging
import openai
import os
import telegram
from flask import Flask, request
from telegram.ext import Dispatcher, MessageHandler, Filters

CHAT_LANGUAGE = os.getenv("INIT_LANGUAGE", default = "zh")
TELEGRAM_BOT_TOKEN = str(os.getenv("TELEGRAM_BOT_TOKEN"))
TG_BOT = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
DISPATCHER = Dispatcher(TG_BOT, None)
CONVERSATIONS = {}
LOG_LEVEL = os.getenv("LOG_LEVEL", default = "DEBUG")
app = Flask(__name__)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=LOG_LEVEL)
logger = logging.getLogger(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

class ChatGPT:
    def __init__(self, tg_user_id: str):
        self.model = os.getenv("OPENAI_MODEL", default = "gpt-3.5-turbo")
        self.tg_user_id = tg_user_id

    def get_response(self, user_input):
        user_messages = []
        if self.tg_user_id in CONVERSATIONS:
            user_messages = CONVERSATIONS.get(self.tg_user_id)

        user_messages.append({"role": "user", "content": user_input})
        response = openai.ChatCompletion.create(
            model=self.model,
            messages = user_messages,
            user=str(self.tg_user_id),
        )

        chatGPT_anserwer = response['choices'][0]['message']['content'].strip()
        user_messages.append({"role": "assistant", "content": chatGPT_anserwer})
        CONVERSATIONS[self.tg_user_id] = user_messages
        
        log_msg = f"""tg user: {self.tg_user_id})
👨‍💼:{user_input}
🤖:{chatGPT_anserwer}"""
        print(log_msg)
        logger.info(log_msg)

        return chatGPT_anserwer


@app.route('/callback', methods=['POST'])
def webhook_handler():
    """Set route /hook with POST method will trigger this method."""
    if request.method == "POST":
        callback_body = request.get_json(force=True)
        print(f"callback_body: {json.dumps(callback_body)}")
        logger.info(f"callback_body= {json.dumps(callback_body)}")

        update = telegram.Update.de_json(callback_body, TG_BOT)
        DISPATCHER.process_update(update)
    return 'ok'


def reply_handler(bot, update):
    """Reply message."""
    user_id = str(update.message.from_user.id)
    print(f"user_id: {user_id}, message: {update.message.text}")
    chatgpt = ChatGPT(user_id)
    chatGPT_anserwer = chatgpt.get_response(update.message.text)
    print(f"user_id: {user_id}, message: {update.message.text}, chatGPT: {chatGPT_anserwer}")
    update.message.reply_text(chatGPT_anserwer)

if __name__ == "__main__":
    DISPATCHER.add_handler(MessageHandler(Filters.text, reply_handler))
    app.run(debug=True)

