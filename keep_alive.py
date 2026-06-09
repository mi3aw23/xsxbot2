from flask import Flask
from threading import Thread
import os
import asyncio

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    # هذا السطر يضمن تشغيل السيرفر على المنفذ الصحيح
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    # حل مشكلة الـ Event Loop للإصدارات الحديثة من بايثون
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    t = Thread(target=run)
    t.daemon = True # لجعل الخيط يعمل كخلفية تابعة
    t.start()























