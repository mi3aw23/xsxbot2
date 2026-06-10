import os
from threading import Thread
from flask import Flask
import asyncio

app = Flask('')

@app.route('/')
def home():
    return "Bot 2 is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    t = Thread(target=run)
    t.daemon = True
    t.start()
