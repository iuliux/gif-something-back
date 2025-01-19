import os
import json
import sqlite3
import uvicorn
import requests
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

import db
from log import logger


# Create the FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Retrieve the Giphy API key from environment variables
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")
if not GIPHY_API_KEY:
    raise ValueError("GIPHY_API_KEY environment variable is not set")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
if not VERIFY_TOKEN:
    raise ValueError("VERIFY_TOKEN environment variable is not set")


# --- Setup ---

@app.on_event("startup")
async def startup():
    await db.database.connect()
    await db.init_db()

@app.on_event("shutdown")
async def shutdown():
    await db.database.disconnect()


# --- Endpoints ---

@app.get("/")
async def root():
    return RedirectResponse(url="/static/display.html")

@app.get("/current_gifs")
async def get_current_gifs():
    """Retrieve all GIF URLs from the database."""
    gifs = await db.refresh_fetch_current_gifs()
    return JSONResponse(content=jsonable_encoder(gifs))

@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return PlainTextResponse(content=challenge, status_code=200)
        else:
            return PlainTextResponse(content="Forbidden", status_code=403)
    raise HTTPException(status_code=400, detail="Bad Request")

@app.post("/webhook")
async def handle_instagram_mentions(request: Request):
    payload = await request.json()

    try:
        # Extract mention data
        field = payload.get("field")
        value = payload.get("value", {})
        
        if field != "mentions" or not value.get("media_id"):
            raise HTTPException(status_code=400, detail="Invalid payload format")

        media_id = value.get("media_id")
        sender_id = value.get("comment_id")

        if not sender_id or not media_id:
            raise HTTPException(status_code=400, detail="Failed to fetch media details")

        # Process the mention
        await db.qr_replace_oldest(media_id, sender_id)

    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid payload format")
    except Exception as e:
        print(f"Error processing mentions: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return {"message": "Mention processed successfully"}

@app.get("/mock_check_reviews")
async def mock_check_reviews():
    """trigger a fake mention"""
    await db.qr_replace_oldest("https://instagram.com/media/xT9IgG50Fb7Mi0prB", "4443123")
    return {"new_reviews": True}

@app.get("/giphy_trending")
async def giphy_trending():
    """Fetch trending GIFs from Giphy API."""
    response = requests.get(
        f"https://api.giphy.com/v1/gifs/trending?api_key={GIPHY_API_KEY}&limit=9"
    )
    return response.json()

@app.get("/giphy_search")
async def giphy_search(query: str):
    """Search for GIFs on Giphy."""
    response = requests.get(
        f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_API_KEY}&q={query}&limit=9"
    )
    return response.json()

@app.post("/update_gif")
async def update_gif(new_gif_url: str = Body(...)):
    """Replace the QR code placeholder with the selected GIF."""
    await db.set_new_gif(new_gif_url)
    return {"status": "GIF updated"}
