# gif-something-back

FastAPI webapp that displays 3 gifs with the posibility of replacing them on demand.  
The app is designed to incentivize customer reviews by allowing users to add their selected GIFs to a public display after leaving a review.

## Features

- **GIF Display**: Displays three GIFs at a time on a screen, with a smooth refresh mechanism.
- **Review Integration**: Detects new reviews from Google Maps and triggers a QR code display for users to add their GIF.
- **GIF Selection**: Users can search for and select GIFs from Giphy via a simple mobile-friendly interface.
- **Dynamic QR Codes**: Displays QR codes for adding new GIFs after a Google Maps review is detected.

## Technologies Used

- **Frontend**: plain HTML, CSS, JavaScript
  - **JS Libraries**: [p5.js](https://p5js.org/), [qrcodejs](https://github.com/davidshimjs/qrcodejs)
- **Backend**: Python, FastAPI
  - **Database**: PostgreSQL (managed instance)
  - **Async Operations**: Handled via `databases` library.
- **Third-Party APIs**:
  - [Google Maps - Places API](https://developers.google.com/maps/documentation) for fetching reviews.
  - [Giphy API](https://developers.giphy.com/) for GIF selection.

## Install

1. Clone the repository:

```bash
git clone git@github.com:iuliux/gif-something-back.git
cd gif-something-back
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```
DATABASE_URL: PostgreSQL connection string
GIPHY_API_KEY: Your Giphy API key
GOOGLE_MAPS_API_KEY: Your Google Maps API key
PLACE_ID: The Place ID hash
```

Example .env file (note the required `+pg8000` used to work around the need to install the fiddly psycopg2):

```env
DATABASE_URL=postgresql+pg8000://<user>:<password>@<host>:<port>/<database>
GIPHY_API_KEY=your-giphy-api-key
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
PLACE_ID=place-id-hash
```

## Running

Change the log level accordingly.

    uvicorn app:app --host 0.0.0.0 --port 8000 --reload --log-level debug


## How It Works

1. GIF Display:

- Displays 3 GIFs in a loop with smooth transitions.
- Refreshes every 3 seconds to check for updates.

2. Google Maps Integration:

- Periodically polls Google Maps API to check for new reviews.
- When a new review is detected, replaces the oldest GIF with a QR code.

3. QR Code:

- Displays a scannable QR code that links to the GIF selection interface.

4. GIF Selection:

- Users can select a GIF from trending options or search for one using the Giphy API.
- Once selected, the GIF replaces the QR code on the display.