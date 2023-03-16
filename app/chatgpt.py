import logging
import os

import openai
from openai.error import InvalidRequestError

OPENAI_MODEL = os.getenv("OPENAI_MODEL", default="gpt-3.5-turbo")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", default=250))
LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")

CONVERSATIONS = {}

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL)
logger = logging.getLogger(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

class ChatGPT:
    def __init__(self, session_id: str):
        self.session_id = session_id

    def get_response(self, user_input):
        user_messages = []
        if self.session_id in CONVERSATIONS:
            user_messages = CONVERSATIONS.get(self.session_id)

        user_messages.append({"role": "user", "content": user_input})
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=user_messages,
                user=self.session_id,
                max_tokens=OPENAI_MAX_TOKENS,
            )
            chatgpt_anserwer = response["choices"][0]["message"]["content"].strip()
            user_messages.append({"role": "assistant", "content": chatgpt_anserwer})
            CONVERSATIONS[self.session_id] = user_messages
            
            logger.info(f"""
Session: {self.session_id}
👨‍:{user_input}
🤖:{chatgpt_anserwer}""")
        except InvalidRequestError:
            user_messages = []
            chatgpt_anserwer = "腦容量不足，已清除對話紀錄，請重新詢問。"
        
        return chatgpt_anserwer
