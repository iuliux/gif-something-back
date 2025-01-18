import os
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import select, func, literal, and_, text
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

history = Table(
    "history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("url", String, nullable=True),
    Column("author", String),
    Column("timestamp", DateTime, default=func.now())
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

async def refresh_fetch_current_gifs():
    # Reset qr and author fields for entries older than threshold
    query = select(gifs.c.id, gifs.c.author).where(
        and_(
            gifs.c.qr.isnot(None),
            gifs.c.url != "",
            gifs.c.qr < func.now() - text("INTERVAL '10 minutes'")
        )
    )
    results = await database.fetch_all(query)

    for row in results:
        # Keep only the first author (oldest)
        updated_author = row["author"].split(",")[0]

        # Update the GIF record
        query = gifs.update().where(gifs.c.id == row["id"]).values(
            qr=None,
            author=updated_author
        )
        await database.execute(query)

    # Fetch updated GIF list
    query = select(gifs.c.url, gifs.c.author, gifs.c.qr, gifs.c.timestamp)
    result = await database.fetch_all(query)

    # Convert the result to a list of dictionaries
    gifs_list = [[row['url'], row['author'], row['qr'], row['timestamp']] for row in result]

    logger.debug(f"Gifs: {gifs_list}")
    return gifs_list

async def qr_replace_oldest(media_url: str, sender_id: str):
    author = f"{sender_id}|{media_url}"
    # Identify the oldest gif record
    query = select(gifs.c.id).where(gifs.c.qr.is_(None)).order_by(gifs.c.timestamp.asc()).limit(1)
    oldest_gif_id = await database.fetch_val(query)
    
    if oldest_gif_id is None:
        raise HTTPException(status_code=404, detail="No available gif found to replace.")
    
    # Fetch the current author from the database
    query = select(gifs.c.author).where(gifs.c.id == oldest_gif_id)
    current_author = await database.fetch_val(query)
    # Ensure the current author is a string (handle potential NULL values)
    current_author = current_author or "system"
    updated_author = f"{current_author},{author}"

    # Set QR Code for the oldest GIF (author field is "old_author,new_author")
    query = gifs.update().where(gifs.c.id == oldest_gif_id).values(
        qr=func.now(),
        author=updated_author,
    )
    await database.execute(query)

    # Log in history
    query = history.insert().values(
        url=None,
        author=author,
        timestamp=func.now(),
    )
    await database.execute(query)
    
    return {"status": "QR code set"}

async def set_new_gif(new_gif_url: str):
    # Identify the oldest QR record
    query = select(gifs.c.id, gifs.c.author).where(gifs.c.qr.isnot(None)).order_by(gifs.c.qr.asc()).limit(1)
    result = await database.fetch_one(query)
    
    if not result:
        raise HTTPException(status_code=404, detail="No QR code placeholder found.")
    
    oldest_qr_id = result["id"]
    author = result["author"]

    # Keep only the last (new) author entry from the author field
    updated_author = author.split(",")[-1]

    # Update the identified GIF record
    query = gifs.update().where(gifs.c.id == oldest_qr_id).values(
        url=new_gif_url,
        qr=None,
        timestamp=func.now(),
        author=updated_author
    )
    await database.execute(query)

    # Find the history entry with the new author and empty URL field
    query = select(history.c.id).where(
        history.c.author == updated_author,
        history.c.url.is_(None)
    ).limit(1)
    history_entry_id = await database.fetch_val(query)
    
    if history_entry_id:
        # Update the history entry with the new GIF URL
        query = history.update().where(history.c.id == history_entry_id).values(url=new_gif_url)
        await database.execute(query)
    
    return {"status": "GIF set"}
