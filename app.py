import logging
import openai
import os
import telegram
from flask import Flask, request
from telegram.ext import Dispatcher, MessageHandler, Filters

app = Flask(__name__)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
CHAT_LANGUAGE = os.getenv("INIT_LANGUAGE", default = "zh")
TELEGRAM_BOT_TOKEN = str(os.getenv("TELEGRAM_BOT_TOKEN"))
TG_BOT = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
DISPATCHER = Dispatcher(TG_BOT, None)
CONVERSATIONS = {}

class ChatGPT:
    def __init__(self, tg_user_id: int):
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
        
        logger.info(f"""tg user: {self.tg_user_id})
👨‍💼:{user_input}
🤖:{chatGPT_anserwer}""")
        
        return chatGPT_anserwer


@app.route('/callback', methods=['POST'])
def webhook_handler():
    """Set route /hook with POST method will trigger this method."""
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), TG_BOT)

        # Update dispatcher process that handler to process this message
        DISPATCHER.process_update(update)
    return 'ok'


def reply_handler(bot, update):
    """Reply message."""
    chatgpt = ChatGPT(update.message.from_user.id)
    ai_reply_response = chatgpt.get_response(update.message.text)
    update.message.reply_text(ai_reply_response)

if __name__ == "__main__":
    DISPATCHER.add_handler(MessageHandler(Filters.text, reply_handler))
    app.run(debug=True)

