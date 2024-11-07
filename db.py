import os
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import select, func, and_, text
from databases import Database

from log import logger

# Load environment variables (for database URL)
DATABASE_URL = os.getenv("DATABASE_URL")  # Ensure this is set in your Render environment

# Set up database connection
database = Database(DATABASE_URL)
metadata = MetaData()

# Define tables using SQLAlchemy
gifs = Table(
    "gifs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("url", String, nullable=False),
    Column("author", String),
    Column("qr", DateTime, nullable=True),
    Column("timestamp", DateTime, default=func.now())
)

review_meta = Table(
    "review_meta",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_ratings_total", Integer, default=0)
)

# Create tables (initialization)
async def init_db():
    engine = create_engine(DATABASE_URL)
    metadata.create_all(engine)
    
    async with database.transaction():
        # Insert a placeholder GIF if no entries exist
        query = select(func.count()).select_from(gifs)
        gif_count = await database.fetch_val(query)
        
        if gif_count == 0:
            await database.execute_many(
                gifs.insert(),
                [
                    {"url": "", "author": "system", "qr": func.now()},
                    {"url": "https://media.giphy.com/media/xT9IgG50Fb7Mi0prBC/giphy.gif", "author": "system"},
                    {"url": "https://media3.giphy.com/media/bbshzgyFQDqPHXBo4c/giphy.gif", "author": "system"},
                ],
            )
        
        # Insert an initial entry if `review_meta` is empty
        query = select(func.count()).select_from(review_meta)
        meta_count = await database.fetch_val(query)
        
        if meta_count == 0:
            await database.execute(review_meta.insert().values(user_ratings_total=0))

async def refresh_fetch_current_gifs():
    # Reset 'qr' field for entries older than threshold
    query = gifs.update().where(
        and_(
            gifs.c.qr.isnot(None),
            gifs.c.url != "",
            gifs.c.qr < func.now() - text("INTERVAL '10 minutes'")
        )
    ).values(qr=None)
    await database.execute(query)

    # Fetch updated GIF list
    query = select(gifs.c.url, gifs.c.author, gifs.c.qr, gifs.c.timestamp)
    result = await database.fetch_all(query)

    # Convert the result to a list of dictionaries
    gifs_list = [[row['url'], row['author'], row['qr'], row['timestamp']] for row in result]

    logger.debug(f"Gifs: {gifs_list}")
    return gifs_list

async def qr_replace_oldest():
    # Identify the oldest gif record
    query = select(gifs.c.id).where(gifs.c.qr.is_(None)).order_by(gifs.c.timestamp.asc()).limit(1)
    oldest_gif_id = await database.fetch_val(query)
    
    if oldest_gif_id is None:
        raise HTTPException(status_code=404, detail="No available gif found to replace.")

    # Set QR Code for the oldest GIF
    query = gifs.update().where(gifs.c.id == oldest_gif_id).values(qr=func.now())
    await database.execute(query)
    
    return {"status": "QR code set"}

async def set_new_gif(new_gif_url):
    # Identify the oldest QR record
    query = select(gifs.c.id).where(gifs.c.qr.isnot(None)).order_by(gifs.c.qr.asc()).limit(1)
    oldest_qr_id = await database.fetch_val(query)
    
    if oldest_qr_id is None:
        raise HTTPException(status_code=404, detail="No QR code placeholder found.")
    
    # Update the identified record
    query = gifs.update().where(gifs.c.id == oldest_qr_id).values(url=new_gif_url, qr=None, timestamp=func.now())
    await database.execute(query)
    
    return {"status": "GIF set"}

async def get_user_ratings_total():
    query = select(review_meta.c.user_ratings_total).where(review_meta.c.id == 1)
    total = await database.fetch_val(query)
    return total

async def update_user_ratings_total(new_total):
    query = review_meta.update().where(review_meta.c.id == 1).values(user_ratings_total=new_total)
    await database.execute(query)
