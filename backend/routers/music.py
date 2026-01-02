from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import MusicConfig
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class MusicSettings(BaseModel):
    youtube_playlist_id: Optional[str] = None
    music_enabled: bool
    volume: int = 50

@router.get("/music/config")
def get_music_config(db: Session = Depends(get_db)):
    """Get current music configuration."""
    config = db.query(MusicConfig).first()
    if not config:
        config = MusicConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return {
        "youtube_playlist_id": config.youtube_playlist_id,
        "music_enabled": config.music_enabled,
        "volume": config.volume
    }

@router.post("/music/config")
def update_music_config(settings: MusicSettings, db: Session = Depends(get_db)):
    """Update music configuration."""
    config = db.query(MusicConfig).first()
    if not config:
        config = MusicConfig()
        db.add(config)
    
    # Update fields if provided
    if settings.youtube_playlist_id is not None:
        config.youtube_playlist_id = settings.youtube_playlist_id
    
    config.music_enabled = settings.music_enabled
    config.volume = settings.volume
    
    db.commit()
    db.refresh(config)
    return {"message": "Music settings updated", "config": settings}
