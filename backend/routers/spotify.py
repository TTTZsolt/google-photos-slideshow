from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import SpotifyConfig
from ..spotify_auth import SpotifyAuthManager
from pydantic import BaseModel

router = APIRouter()
spotify_manager = SpotifyAuthManager()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SpotifyCredentials(BaseModel):
    client_id: str
    client_secret: str

class PlaylistSelection(BaseModel):
    playlist_uri: str
    playlist_name: str

class MusicToggle(BaseModel):
    enabled: bool

@router.post("/spotify/credentials")
def save_credentials(creds: SpotifyCredentials, db: Session = Depends(get_db)):
    """Save Spotify Client ID and Secret."""
    config = spotify_manager.get_config(db)
    config.client_id = creds.client_id
    config.client_secret = creds.client_secret
    db.commit()
    return {"message": "Spotify credentials saved"}

@router.get("/spotify/auth")
def initiate_auth(db: Session = Depends(get_db)):
    """Initiate Spotify OAuth flow."""
    try:
        auth_url = spotify_manager.get_auth_url(db)
        return {"auth_url": auth_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/spotify/callback")
def auth_callback(code: str, db: Session = Depends(get_db)):
    """Handle Spotify OAuth callback."""
    success = spotify_manager.handle_callback(code, db)
    if success:
        return RedirectResponse(url="/?spotify_auth=success")
    else:
        return RedirectResponse(url="/?spotify_auth=failed")

@router.get("/spotify/playlists")
def get_playlists(db: Session = Depends(get_db)):
    """Get user's Spotify playlists."""
    try:
        playlists = spotify_manager.get_user_playlists(db)
        return {"playlists": playlists}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/spotify/playlist")
def select_playlist(selection: PlaylistSelection, db: Session = Depends(get_db)):
    """Select a playlist for playback."""
    config = spotify_manager.get_config(db)
    config.selected_playlist_uri = selection.playlist_uri
    config.selected_playlist_name = selection.playlist_name
    db.commit()
    return {"message": "Playlist selected"}

@router.post("/spotify/music-toggle")
def toggle_music(toggle: MusicToggle, db: Session = Depends(get_db)):
    """Enable or disable music playback."""
    config = spotify_manager.get_config(db)
    config.music_enabled = toggle.enabled
    db.commit()
    return {"message": f"Music {'enabled' if toggle.enabled else 'disabled'}"}

@router.get("/spotify/config")
def get_config(db: Session = Depends(get_db)):
    """Get current Spotify configuration."""
    config = spotify_manager.get_config(db)
    return {
        "authenticated": config.access_token is not None,
        "client_id_set": config.client_id is not None,
        "selected_playlist_uri": config.selected_playlist_uri,
        "selected_playlist_name": config.selected_playlist_name,
        "music_enabled": config.music_enabled
    }

@router.get("/spotify/token")
def get_token(db: Session = Depends(get_db)):
    """Get current access token for Web Playback SDK."""
    config = spotify_manager.get_config(db)
    if not config.access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Refresh token if needed
    try:
        spotify_manager.get_spotify_client(db)  # This will refresh if needed
        config = spotify_manager.get_config(db)  # Get updated config
        return {"access_token": config.access_token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
