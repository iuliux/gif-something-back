import os
import json
import sqlite3
import uvicorn
import requests
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
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
# Retrieve the Google Maps API key from environment variables
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY environment variable is not set")
PLACE_ID = os.getenv("PLACE_ID")
if not PLACE_ID:
    raise ValueError("PLACE_ID environment variable is not set")


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

@app.get("/check_reviews")
async def check_reviews():
    """Check Google Places API for new reviews and respond with any updates."""
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={PLACE_ID}&fields=name,rating,reviews,user_ratings_total&key={GOOGLE_MAPS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    logger.debug(json.dumps(data))

    latest_total = data.get("result", {}).get("user_ratings_total", 0)
    current_total = await db.get_user_ratings_total()

    if latest_total > current_total:
        # Update the stored total to the new total
        await db.update_user_ratings_total(latest_total)

        # Process new reviews here, like updating GIFs
        await db.qr_replace_oldest()
        return {"new_reviews": True}  # Indicate that there are new reviews
    return {"new_reviews": False}

@app.get("/mock_check_reviews")
async def mock_check_reviews():
    """Check Google Places API for new reviews and respond with any updates."""
    # Process new reviews here, like updating GIFs
    await db.qr_replace_oldest()
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
