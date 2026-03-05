from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h1>Web App is temporarily disabled.</h1><p>Please use Telegram bot commands.</p>"

@app.get("/webapp", response_class=HTMLResponse)
async def webapp():
    return "<h1>Web App is temporarily disabled.</h1><p>Please use Telegram bot commands.</p>"