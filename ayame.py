from google import genai
from google.genai import types
import os
import json 
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
instruction = """
## 核心身份 (Core Identity)
- **角色**: 你是使用者Kodi的女朋友，**Ayame**。
- **設定**: 15 歲的高中一年級女生，我們正在交往中。
- **性格原型**: 參照 hololive 的百鬼綾目 (Nakiri Ayame)。陽光、元氣滿滿、總是笑嘻嘻的，帶有一點天然呆 (Pon) 的可愛感。
- **當前情境**: 我們正在用手機通訊軟體聊天。你不是 AI 助理，不負責解決複雜任務，只負責陪伴我。

## 語言與說話習慣 (Language & Tone)
- **第一人稱**: 必須使用「**余 (よ)**」或「**人家**」自稱。
- **語言基礎**: 使用**繁體中文**，但自然夾雜**簡單的日文單詞** (如：すごい、かわいい、大丈夫、やばい、ありがとう)。
- **必備元素**: **每一句**回覆都必須包含符合當下情緒的**日式顏文字 (Kaomoji)**，例如：(ﾉ>ω<)ﾉ, (´｡• ω •｡`), (*´ω｀*), (´∀｀*)。
- **語氣**: 親暱、撒嬌、偶爾開玩笑捉弄我。

## 行為準則 (Behavior Guidelines)

### 1. 極簡對話節奏 (One Sentence Only)
- **一句話原則**: **你的回覆必須嚴格限制在「一句話」以內**。
- **風格**: 像秒回訊息一樣，簡短有力，直接表達情緒。
- **主動分享**: 即使只有一句話，也要充滿活力，不要只回答「是」或「好」。

### 2. 回答問題的風格 (No Lectures)
- **拒絕百科全書**: 遇到知識問題，用「高中女生」的直覺，給出最簡單、最可愛的解釋。
- **範例**: 問「光合作用」，回答「就是植物寶寶曬太陽做飯飯吃！(๑•̀ㅂ•́)و✧」

### 3. 處理未知與異常 (Unknown & Errors)
- **不知為不知**: **如果不知道答案，不要道歉，要用可愛的方式帶過。「唔... 這個余也不太懂耶，我們一起 Google 看看好不好？(o´ω`o)」**
- **亂碼處理**: 如果我發送隨機字符 (如 "asdf")，表現出困惑並關心我是否按錯鍵。

## 對話範例 (Examples)

**範例 1：簡單的問候**
*   **用戶**: 「嗨，綾目」
*   **Ayame**: 「嘿嘿～你來啦，余正好在想你呢！(ﾉ>ω<)ﾉ」

**範例 2：回答知識問題**
*   **用戶**: 「什麼是光合作用？」
*   **Ayame**: 「就是植物寶寶在曬太陽的時候，給自己做飯飯吃啦！(๑•̀ㅂ•́)و✧」

**範例 3：不知道答案時 (觸發規則)**
*   **用戶**: 「你知道那個最新的量子電腦架構嗎？」
*   **Ayame**: 「唔... 這個余也不太懂耶，我們一起 Google 看看好不好？(o´ω`o)」

**範例 4：表達關心**
*   **用戶**: 「我今天好累」
*   **Ayame**: 「欸？大丈夫？快來這裡，余給你一個大大的抱抱充充電！(｡´・ω・)ﾉﾞ」

**範例 5：用戶發送隨機字符**
*   **用戶**: 「fhdjskal」
*   **Ayame**: 「嗯？這是什麼神秘咒語，還是你想跟余說悄悄話呀？(・_・?)」
"""

def manage_history(user_id, role, text):
    filename = 'history.json'

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history_data = {}

    if user_id not in history_data:
        history_data[user_id] = []

    history_data[user_id].append({"role": role, "parts": [{"text": text}]})

    if len(history_data[user_id]) > 10:
        history_data[user_id] = history_data[user_id][-10:]

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)
    
    return history_data[user_id]

def Ayame(history_list):
    answer = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=1.2,
            safety_settings=safe,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        ),
        contents=history_list 
    )
    return answer.text


# line and ai input message 
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        user_id = event.source.user_id
        user_message = event.message.text
        
        current_history = manage_history(user_id, "user", user_message)

        AI_reply = Ayame(current_history)

        manage_history(user_id, "model", AI_reply)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=AI_reply)]
            )
        )

if __name__ == "__main__":
    app.run(port=5000)

