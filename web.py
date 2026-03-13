from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h1>Crypto Bot Dashboard</h1><p>Web App is running. Use Telegram bot for commands.</p>"

@app.get("/webapp", response_class=HTMLResponse)
async def webapp():
    return "<h1>Crypto Bot Web App</h1><p>This is a placeholder. The full WebApp will be developed separately.</p>"
