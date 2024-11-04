import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store the currently displayed GIFs (URLs or paths to the GIFs)
gif_display = [
    "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",  # Example GIFs
    "QR_CODE_PLACEHOLDER",
    "https://media.giphy.com/media/xT9IgG50Fb7Mi0prBC/giphy.gif"
]

# Retrieve the Giphy API key from environment variables
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")
# Ensure the GIPHY_API_KEY is set
if not GIPHY_API_KEY:
    raise ValueError("GIPHY_API_KEY environment variable is not set")

# Define a Pydantic model for the request body
class GifUpdateRequest(BaseModel):
    new_gif_url: str


@app.get("/")
async def root():
    return RedirectResponse(url="/static/display.html")

@app.get("/current_gifs")
async def get_current_gifs():
    """Endpoint to get currently displayed GIFs."""
    return JSONResponse(gif_display)

@app.post("/webhook")
async def webhook_listener(request: Request):
    """Webhook endpoint triggered by a new Google Maps review."""
    data = await request.json()
    # When triggered, replace the oldest GIF with a placeholder for the QR code
    gif_display.pop(0)
    gif_display.append("QR_CODE_PLACEHOLDER")
    return {"status": "QR code placeholder set"}

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
async def update_gif(request: GifUpdateRequest):
    """Replace the QR code placeholder with the selected GIF."""
    new_gif_url = request.new_gif_url

    for i, gif in enumerate(gif_display):
        if gif == "QR_CODE_PLACEHOLDER":
            gif_display[i] = new_gif_url
            break
    return {"status": "GIF updated"}
