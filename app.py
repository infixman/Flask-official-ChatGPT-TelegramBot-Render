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
    def __init__(self, session_id: str):
        self.model = os.getenv("OPENAI_MODEL", default = "gpt-3.5-turbo")
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
        
        logger.info(f"""tg user: {self.session_id})
👨‍💼:{user_input}
🤖:{chatGPT_anserwer}""")

        return chatGPT_anserwer


@app.route('/callback', methods=['POST'])
def webhook_handler():
    """Set route /hook with POST method will trigger this method."""
    if request.method == "POST":
        callback_body = request.get_json(force=True)
        logger.info(f"callback_body: {json.dumps(callback_body)}")
        update = telegram.Update.de_json(callback_body, TG_BOT)
        DISPATCHER.process_update(update)
    return 'ok'


def reply_handler(bot, update):
    """Reply message."""
    logger.info(f"update.message: {json.dumps(update.message)}")
    session_id = f"{update.message.chat.id}"
    chatgpt = ChatGPT(session_id)
    chatGPT_anserwer = chatgpt.get_response(update.message.text)
    update.message.reply_text(chatGPT_anserwer)

if __name__ == "__main__":
    DISPATCHER.add_handler(MessageHandler(Filters.text, reply_handler))
    app.run(debug=True)

