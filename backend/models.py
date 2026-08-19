from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base

class B2Account(Base):
    __tablename__ = "b2_accounts"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String, unique=True, index=True)
    application_key = Column(String)
    bucket_name = Column(String) # kepek02 (Active)
    archive_bucket_name = Column(String, nullable=True) # kepek01 (Edit Originals)
    source_bucket_name = Column(String, nullable=True) # forras (Staging - legacy, no active role)
    trash_bucket_name = Column(String, nullable=True) # torles-elott (Trash)
    incoming_bucket_name = Column(String, nullable=True) # beerkezo (raw phone-sync inbox, feldolgozatlan)
    cloudflare_proxy_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String, default="Idle") # Idle, Syncing, Finished, Error
    sync_count = Column(Integer, default=0) # Number of items indexed in last/current sync
    sync_total = Column(Integer, default=0) # Total estimated items to sync
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(String, primary_key=True, index=True) # B2 File ID
    b2_account_id = Column(Integer, index=True) # ForeignKey relation to B2Account.id
    bucket_name = Column(String, index=True) # Which bucket this file is currently in
    file_name = Column(Text, index=True) # B2 File Name (Path)
    mime_type = Column(String)
    size = Column(Integer, nullable=True)
    creation_time = Column(DateTime(timezone=True), nullable=True)
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())
    is_in_sorter = Column(Boolean, default=False, index=True)
    sha1 = Column(String, nullable=True, index=True) # B2 native content SHA1

class MediaClassification(Base):
    __tablename__ = "media_classifications"
    
    file_name = Column(Text, primary_key=True, index=True) # B2 File Path (Key)
    category = Column(String, nullable=True) # család, utazás, állatok, stb.
    is_deleted = Column(Boolean, default=False)
    ai_suggested_category = Column(String, nullable=True) # Javasolt kategória, vagy 'delete'
    ai_status = Column(String, nullable=True) # "pending", "approved", "failed"
    ai_error = Column(Text, nullable=True) # AI error message if status is failed
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class DeletedContentHash(Base):
    """Tombstone: permanently records the content-SHA1 of every image that was
    ever emptied from the Trash, so it survives the MediaItem/MediaClassification
    row deletion and can be checked against future (re-)uploads (e.g. from a
    fresh Google Photos Takeout export) to avoid accidentally restoring content
    that was deliberately deleted."""
    __tablename__ = "deleted_content_hashes"

    sha1 = Column(String, primary_key=True, index=True)
    last_known_file_name = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String, nullable=True) # e.g. "trash-empty"

class MusicConfig(Base):
    __tablename__ = "music_config"

    id = Column(Integer, primary_key=True, index=True)
    youtube_playlist_id = Column(String, nullable=True) # YouTube Playlist ID or Video ID
    music_enabled = Column(Boolean, default=False)
    volume = Column(Integer, default=50)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class FlaggedImage(Base):
    __tablename__ = "flagged_images"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(Text, unique=True, index=True) # B2 File Path
    flagged_at = Column(DateTime(timezone=True), server_default=func.now())

class CategoryDefinition(Base):
    __tablename__ = "category_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # internal name, lowercase, e.g. "család"
    display_name = Column(String) # shown to user, e.g. "Család"
    icon = Column(String, default="tag") # Lucide icon name
    color = Column(String, default="#6366f1") # CSS color
    order = Column(Integer, default=0)
    description = Column(Text, nullable=True) # Description for AI classification rules
    created_at = Column(DateTime(timezone=True), server_default=func.now())
