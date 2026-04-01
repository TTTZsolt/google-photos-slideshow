from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from .routers import dashboard, music, classification
from .database import engine, Base
import sqlite3
import os

app = FastAPI(title="B2 Random Slideshow - V9.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

def auto_migrate():
    db_path = "photos_app.db"
    if not os.path.exists(db_path):
        if os.path.exists("backend/photos_app.db"):
            db_path = "backend/photos_app.db"
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Add missing B2Account columns
            for col in ["source_bucket_name", "trash_bucket_name", "archive_bucket_name"]:
                try:
                    cursor.execute(f"ALTER TABLE b2_accounts ADD COLUMN {col} TEXT;")
                except sqlite3.OperationalError:
                    pass

            # Add missing MediaItem columns
            try:
                cursor.execute("ALTER TABLE media_items ADD COLUMN bucket_name TEXT;")
            except sqlite3.OperationalError:
                pass

            # Ensure media_classifications exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_classifications (
                    file_name TEXT PRIMARY KEY,
                    category TEXT,
                    is_deleted BOOLEAN DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Migration error: {e}")

auto_migrate()

# Routes
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(music.router, tags=["music"])
app.include_router(classification.router, tags=["classification"])

# Mount static files
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

templates = Jinja2Templates(directory="backend/templates")

if __name__ == "__main__":
    import uvicorn
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": "log.txt",
                "maxBytes": 5 * 1024 * 1024, # 5 MB maximum
                "backupCount": 1,
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["file"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["file"], "level": "INFO", "propagate": False},
            "fastapi": {"handlers": ["file"], "level": "INFO"},
            "pychromecast": {"handlers": ["file"], "level": "CRITICAL"},
            "zeroconf": {"handlers": ["file"], "level": "CRITICAL"},
        },
    }
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=True, log_config=LOGGING_CONFIG)
