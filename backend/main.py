from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()
from .routers import dashboard, music, classification, trash
from .database import engine, Base
from .version import VERSION, PROJECT_NAME
from . import models  # Ensure all models are loaded for create_all
import sqlite3
import os

app = FastAPI(title=f"{PROJECT_NAME} V{VERSION}")

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
            
            try:
                cursor.execute("ALTER TABLE media_items ADD COLUMN is_in_sorter BOOLEAN DEFAULT 0;")
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_media_items_is_in_sorter ON media_items (is_in_sorter);")
            except sqlite3.OperationalError:
                pass
            
            # Ensure index exists on file_name
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_media_items_file_name ON media_items (file_name);")
            except sqlite3.OperationalError:
                pass

            # Ensure media_classifications exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_classifications (
                    file_name TEXT PRIMARY KEY,
                    category TEXT,
                    is_deleted BOOLEAN DEFAULT 0,
                    ai_suggested_category TEXT,
                    ai_status TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Add AI columns if table already existed but without them
            for col in ["ai_suggested_category", "ai_status", "ai_error"]:
                try:
                    cursor.execute(f"ALTER TABLE media_classifications ADD COLUMN {col} TEXT;")
                except sqlite3.OperationalError:
                    pass

            # Ensure category_definitions exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS category_definitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    display_name TEXT,
                    icon TEXT DEFAULT 'tag',
                    color TEXT DEFAULT '#6366f1',
                    "order" INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Add description column if it does not exist
            try:
                cursor.execute("ALTER TABLE category_definitions ADD COLUMN description TEXT;")
            except sqlite3.OperationalError:
                pass

            # Seed default categories if empty
            cursor.execute("SELECT COUNT(*) FROM category_definitions;")
            if cursor.fetchone()[0] == 0:
                defaults = [
                    ("család", "Család", "users", "#4f46e5", 0),
                    ("utazás", "Utazás", "plane", "#a855f7", 1),
                    ("állatok", "Állatok", "cat", "#f59e0b", 2)
                ]
                cursor.executemany("""
                    INSERT INTO category_definitions (name, display_name, icon, color, "order")
                    VALUES (?, ?, ?, ?, ?);
                """, defaults)
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Migration error: {e}")

auto_migrate()

# Routes
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(music.router, tags=["music"])
app.include_router(classification.router, tags=["classification"])
app.include_router(trash.router, tags=["trash"])

# Mount static files
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

templates = Jinja2Templates(directory="backend/templates")
templates.env.globals.update(version=VERSION)


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "version": VERSION})

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
                "class": "logging.FileHandler",
                "formatter": "default",
                "filename": "log.txt",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["file"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["file"], "level": "INFO", "propagate": False},
            "fastapi": {"handlers": ["file"], "level": "INFO"},
            "backend": {"handlers": ["file"], "level": "INFO"},
            "pychromecast": {"handlers": ["file"], "level": "CRITICAL"},
            "zeroconf": {"handlers": ["file"], "level": "CRITICAL"},
        },
    }
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False, log_config=LOGGING_CONFIG)
