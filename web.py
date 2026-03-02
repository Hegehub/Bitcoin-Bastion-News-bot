from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from database import get_db, News
import databases
import sqlalchemy
from config import DATABASE_URL

database = databases.Database(DATABASE_URL)
templates = Jinja2Templates(directory="templates")

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    query = "SELECT COUNT(*) FROM news"
    total_news = await database.fetch_val(query)
    query = "SELECT COUNT(*) FROM news WHERE matched = TRUE"
    matched_news = await database.fetch_val(query)
    query = "SELECT COUNT(*) FROM news WHERE published_in_channel = TRUE"
    published = await database.fetch_val(query)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "total_news": total_news,
        "matched_news": matched_news,
        "published": published
    })
