from flask import Flask
from threading import Thread
app = Flask("app")

@app.get("/")
def Hello():
    return "Hello!"

def run():
    app.run()

def keep_alive():
    t = Thread(target=run)
    t.start()