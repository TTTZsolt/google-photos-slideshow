import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import SpotifyConfig
from .database import SessionLocal
import os

class SpotifyAuthManager:
    def __init__(self):
        self.redirect_uri = "http://localhost:8080/spotify/callback"
        self.scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative streaming"
    
    def get_config(self, db: Session) -> SpotifyConfig:
        """Get or create Spotify config from database."""
        config = db.query(SpotifyConfig).first()
        if not config:
            config = SpotifyConfig()
            db.add(config)
            db.commit()
            db.refresh(config)
        return config
    
    def get_auth_url(self, db: Session) -> str:
        """Generate Spotify authorization URL."""
        config = self.get_config(db)
        if not config.client_id or not config.client_secret:
            raise ValueError("Spotify Client ID and Secret not configured")
        
        sp_oauth = SpotifyOAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        return sp_oauth.get_authorize_url()
    
    def handle_callback(self, code: str, db: Session) -> bool:
        """Handle OAuth callback and store tokens."""
        config = self.get_config(db)
        
        sp_oauth = SpotifyOAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        
        token_info = sp_oauth.get_access_token(code)
        if token_info:
            config.access_token = token_info['access_token']
            config.refresh_token = token_info['refresh_token']
            config.token_expires_at = datetime.now() + timedelta(seconds=token_info['expires_in'])
            db.commit()
            return True
        return False
    
    def get_spotify_client(self, db: Session) -> spotipy.Spotify:
        """Get authenticated Spotify client, refreshing token if needed."""
        config = self.get_config(db)
        
        if not config.access_token:
            raise ValueError("Not authenticated with Spotify")
        
        # Check if token needs refresh
        if config.token_expires_at and datetime.now() >= config.token_expires_at:
            self._refresh_token(config, db)
        
        return spotipy.Spotify(auth=config.access_token)
    
    def _refresh_token(self, config: SpotifyConfig, db: Session):
        """Refresh the access token."""
        sp_oauth = SpotifyOAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        
        token_info = sp_oauth.refresh_access_token(config.refresh_token)
        config.access_token = token_info['access_token']
        config.token_expires_at = datetime.now() + timedelta(seconds=token_info['expires_in'])
        db.commit()
    
    def get_user_playlists(self, db: Session):
        """Get user's playlists."""
        sp = self.get_spotify_client(db)
        playlists = sp.current_user_playlists(limit=50)
        return [
            {
                "name": pl['name'],
                "uri": pl['uri'],
                "tracks": pl['tracks']['total']
            }
            for pl in playlists['items']
        ]
