from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base

class B2Account(Base):
    __tablename__ = "b2_accounts"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String, unique=True, index=True)
    application_key = Column(String)
    bucket_name = Column(String)
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(String, primary_key=True, index=True) # B2 File ID
    b2_account_id = Column(Integer, index=True) # ForeignKey relation to B2Account.id
    file_name = Column(Text) # B2 File Name
    mime_type = Column(String)
    size = Column(Integer, nullable=True)
    creation_time = Column(DateTime(timezone=True), nullable=True)
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())

class SpotifyConfig(Base):
    __tablename__ = "spotify_config"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, nullable=True)
    client_secret = Column(String, nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    selected_playlist_uri = Column(String, nullable=True)
    selected_playlist_name = Column(String, nullable=True)
    music_enabled = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
