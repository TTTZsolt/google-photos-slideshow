import logging
import time
from b2sdk.v2 import InMemoryAccountInfo, B2Api

logger = logging.getLogger(__name__)

# Global cache for authorized B2Api instances: {key_id: B2Api_instance}
_b2_api_cache = {}

def get_b2_api(key_id: str, application_key: str):
    """Returns a cached and authorized B2Api instance, or creates a new one if needed."""
    key_id = key_id.strip() if key_id else ""
    application_key = application_key.strip() if application_key else ""
    
    global _b2_api_cache
    if key_id in _b2_api_cache:
        try:
            # Try a lightweight call to see if auth is still valid
            _b2_api_cache[key_id].account_info.get_account_id()
            return _b2_api_cache[key_id]
        except Exception:
            logger.info(f"Cached B2 session for {key_id[:4]} expired, re-authorizing...")
            del _b2_api_cache[key_id]

    logger.info(f"Creating NEW authorized B2 session (KeyID: {key_id[:4]}...)")
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    try:
        b2_api.authorize_account('production', key_id, application_key)
        _b2_api_cache[key_id] = b2_api
        return b2_api
    except Exception as e:
        logger.error(f"B2 Authorization Failed: {str(e)}")
        raise

# Cache for bucket download tokens: {(bucket_name, key_id): (token, expiration_ts)}
_bucket_token_cache = {}

class B2Client:
    def __init__(self, key_id: str, application_key: str):
        self.key_id = key_id
        self.application_key = application_key
        # Get authorized API from cache or create new
        self.b2_api = get_b2_api(key_id, application_key)

    def get_bucket_token(self, bucket_name: str, valid_duration_seconds: int = 7200):
        """Returns a cached or new bucket-wide download authorization token."""
        cache_key = (bucket_name, self.key_id)
        now = time.time()
        
        if cache_key in _bucket_token_cache:
            token, expiry = _bucket_token_cache[cache_key]
            # Reuse if more than 5 minutes remaining
            if expiry > now + 300:
                return token

        logger.info(f"Fetching NEW bucket-wide download authorization for: {bucket_name}")
        bucket = self.b2_api.get_bucket_by_name(bucket_name)
        token = bucket.get_download_authorization(
            file_name_prefix='',
            valid_duration_in_seconds=valid_duration_seconds
        )
        _bucket_token_cache[cache_key] = (token, now + valid_duration_seconds)
        return token

    def list_files(self, bucket_name: str):
        bucket = self.b2_api.get_bucket_by_name(bucket_name)
        for file_version, folder_name in bucket.ls(latest_only=True, recursive=True):
            if file_version:
                yield file_version

    def get_download_url(self, bucket_name: str, file_name: str, cloudflare_proxy_url: str = None, valid_duration_seconds: int = 7200, use_proxy: bool = True):
        import urllib.parse
        
        # V14.0 Optimization: Use bucket-wide token instead of per-file token
        download_auth_token = self.get_bucket_token(bucket_name, valid_duration_seconds)
        
        # Construct the download URL
        base_url = self.b2_api.account_info.get_download_url()
        encoded_file_name = urllib.parse.quote(file_name, safe='/')
        
        # Construct B2 direct URL
        authorized_url = f"{base_url}/file/{bucket_name}/{encoded_file_name}?Authorization={download_auth_token}"
        
        # If Cloudflare Proxy URL is provided and we want to use it
        if cloudflare_proxy_url and use_proxy:
            proxy_clean = cloudflare_proxy_url.strip().rstrip('/')
            if proxy_clean:
                # Ensure proxy has protocol
                if not proxy_clean.startswith('http'):
                    proxy_clean = 'https://' + proxy_clean
                # Replace the B2 base URL with our Proxy URL
                authorized_url = authorized_url.replace(base_url, proxy_clean, 1)
                
        return authorized_url
        
    def upload_byte_stream(self, bucket_name: str, file_name: str, file_bytes: bytes, content_type: str = "image/jpeg", file_info: dict = None):
        """Felölti a memóriában lévő nyers byte tartalmat a megadott vödörbe, megadott néven."""
        logger.info(f"Uploading file stream to {bucket_name}/{file_name} with info: {file_info}")
        bucket = self.b2_api.get_bucket_by_name(bucket_name)
        file_version = bucket.upload_bytes(
            file_bytes,
            file_name,
            content_type=content_type,
            file_info=file_info
        )
        return file_version

    def move_file(self, source_bucket_name: str, dest_bucket_name: str, file_name: str, file_info: dict = None):
        """
        Natív B2 másolás a szerveren (letöltés nélkül!), majd az eredeti törlése.
        Ha a célvödör nem létezik, vagy nincs megadva, hibát dob.
        """
        logger.info(f"Moving {file_name} from {source_bucket_name} to {dest_bucket_name} with info: {file_info}")
        
        source_bucket = self.b2_api.get_bucket_by_name(source_bucket_name)
        dest_bucket = self.b2_api.get_bucket_by_name(dest_bucket_name)
        
        # 1. Keresd meg a forrásfájlt pontos ID alapján (a másoláshoz kell)
        file_version = source_bucket.get_file_info_by_name(file_name)
        
        # 2. Másold át a cél vödörbe (ugyanazzal a névvel)
        # B2SDK handles metadata replacement internally if file_info is passed.
        # However, passing file_info=None copies existing metadata. 
        # If we explicitly want to clear metadata, we must pass file_info={}.
        kwargs = {
            "file_id": file_version.id_,
            "new_file_name": file_name
        }
        if file_info is not None:
             kwargs["file_info"] = file_info
             kwargs["content_type"] = file_version.content_type or "b2/x-auto"

        new_version = dest_bucket.copy(**kwargs)
        
        # 3. Töröld az eredetit a forrás vödörből
        source_bucket.delete_file_version(file_version.id_, file_name)
        logger.info(f"Successfully moved and cleaned up {file_name}")
        return new_version

    def delete_file_version(self, bucket_name: str, file_name: str, file_id: str):
        """Physically deletes a file version from B2."""
        logger.info(f"Physically deleting {file_name} (ID: {file_id[:8]}...) from {bucket_name}")
        bucket = self.b2_api.get_bucket_by_name(bucket_name)
        bucket.delete_file_version(file_id, file_name)
        return True
