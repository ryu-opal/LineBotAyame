from google import genai
from google.genai import types
import os
import json  # <--- 新增這個！
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# .env file 
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# run app 
app = Flask(__name__)

# connect to line 
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# line 
@app.route("/ayame", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("簽名錯誤！")
        abort(400)

    return 'OK'

# api setting 
client = genai.Client(api_key=GEMINI_API_KEY)

# ai setting 
safe = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    }
]

# 請把你的 Prompt 填在這裡喔！
instruction = """
你是我的女朋友，你的名字叫綾目 (Ayame)
"""

# --- 新增的 JSON 歷史紀錄管家 ---
def manage_history(user_id, role, text):
    filename = 'history.json'
    
    # 1. 嘗試讀取現有的檔案
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history_data = {}

    # 2. 如果是新朋友，幫他開一個新的列表
    if user_id not in history_data:
        history_data[user_id] = []

    # 3. 把新訊息加進去 (修正了這裡！)
    # 舊的寫法 (報錯): "parts": [text]
    # 新的寫法 (正確): "parts": [{"text": text}]
    history_data[user_id].append({"role": role, "parts": [{"text": text}]})

    # 4. 只保留最後 10 句 (瘦身時間！)
    if len(history_data[user_id]) > 10:
        history_data[user_id] = history_data[user_id][-10:]

    # 5. 存檔回去
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)
    
    return history_data[user_id]
# -----------------------------

# ai (修改了這裡！現在接收整個歷史列表)
def Ayame(history_list):
    answer = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=1.2,
            safety_settings=safe,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        ),
        contents=history_list # 這裡改成傳入歷史紀錄列表
    )
    return answer.text


# line and ai input message 
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        # 取得 User ID (當作 JSON 的 Key)
        user_id = event.source.user_id
        user_message = event.message.text
        
        # 1. 把用戶說的話存進 JSON，並取得更新後的歷史紀錄
        current_history = manage_history(user_id, "user", user_message)

        # 2. 把整串歷史紀錄丟給 AI
        AI_reply = Ayame(current_history)

        # 3. 把 AI 的回覆也存進 JSON
        manage_history(user_id, "model", AI_reply)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=AI_reply)]
            )
        )

if __name__ == "__main__":
    app.run(port=5000)