from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    credentials_json = Column(Text) # Store the full credentials object
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(String, primary_key=True, index=True) # Google Photos Media ID
    account_id = Column(Integer, index=True) # ForeignKey relation to Account.id
    base_url = Column(Text)
    mime_type = Column(String)
    filename = Column(String)
    creation_time = Column(DateTime(timezone=True))
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())
