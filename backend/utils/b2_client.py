import logging
import time
from b2sdk.v2 import InMemoryAccountInfo, B2Api

logger = logging.getLogger(__name__)

class B2Client:
    def __init__(self, key_id: str, application_key: str):
        # Strip potential whitespace
        self.key_id = key_id.strip() if key_id else ""
        self.application_key = application_key.strip() if application_key else ""
        
        logger.info(f"Authorizing B2 client (KeyID: {self.key_id[:4]}...)")
        
        self.info = InMemoryAccountInfo()
        self.b2_api = B2Api(self.info)
        try:
            self.b2_api.authorize_account('production', self.key_id, self.application_key)
        except Exception as e:
            logger.error(f"B2 Authorization Failed: {str(e)}")
            raise
        
        # Cache for download authorizations: {bucket_name: (token, expiry_timestamp)}
        self._download_auths = {}

    def list_files(self, bucket_name: str):
        bucket = self.b2_api.get_bucket_by_name(bucket_name)
        # generator for listing files recursively
        for file_version, folder_name in bucket.ls(latest_only=True, recursive=True):
            if file_version:
                yield file_version

    def get_download_url(self, bucket_name: str, file_name: str, cloudflare_proxy_url: str = None, valid_duration_seconds: int = 7200, use_proxy: bool = True):
        import urllib.parse
        
        now = time.time()
        cached_auth = self._download_auths.get(bucket_name)
        
        # Use cached token if it's still valid for at least 5 minutes
        if cached_auth and cached_auth[1] > now + 300:
            download_auth_token = cached_auth[0]
        else:
            logger.info(f"Fetching new download authorization for bucket: {bucket_name}")
            bucket = self.b2_api.get_bucket_by_name(bucket_name)
            download_auth_token = bucket.get_download_authorization(
                file_name_prefix="",  # Empty prefix allows access to any file in bucket
                valid_duration_in_seconds=valid_duration_seconds
            )
            self._download_auths[bucket_name] = (download_auth_token, now + valid_duration_seconds)
        
        # Construct the download URL
        base_url = self.b2_api.account_info.get_download_url()
        encoded_file_name = urllib.parse.quote(file_name, safe='/')
        authorized_url = f"{base_url}/file/{bucket_name}/{encoded_file_name}?Authorization={download_auth_token}"
        
        # If Cloudflare Proxy URL is provided and we want to use it, replace the B2 base URL with the proxy URL
        if cloudflare_proxy_url and use_proxy:
            proxy_clean = cloudflare_proxy_url.strip().rstrip('/')
            if proxy_clean:
                authorized_url = authorized_url.replace(base_url, proxy_clean, 1)
                
        return authorized_url
        
    def upload_byte_stream(self, bucket_name: str, file_name: str, file_bytes: bytes, content_type: str = "image/jpeg"):
        """Felölti a memóriában lévő nyers byte tartalmat a megadott vödörbe, megadott néven."""
        logger.info(f"Uploading file stream to {bucket_name}/{file_name}")
        bucket = self.b2_api.get_bucket_by_name(bucket_name)
        file_version = bucket.upload_bytes(
            file_bytes,
            file_name,
            content_type=content_type
        )
        return file_version
        
    def move_file(self, source_bucket_name: str, dest_bucket_name: str, file_name: str):
        """
        Natív B2 másolás a szerveren (letöltés nélkül!), majd az eredeti törlése.
        Ha a célvödör nem létezik, vagy nincs megadva, hibát dob.
        """
        logger.info(f"Moving {file_name} from {source_bucket_name} to {dest_bucket_name}")
        
        source_bucket = self.b2_api.get_bucket_by_name(source_bucket_name)
        dest_bucket = self.b2_api.get_bucket_by_name(dest_bucket_name)
        
        # 1. Keresd meg a forrásfájlt pontos ID alapján (a másoláshoz kell)
        file_version = source_bucket.get_file_info_by_name(file_name)
        
        # 2. Másold át a cél vödörbe (ugyanazzal a névvel)
        new_version = dest_bucket.copy(
            file_id=file_version.id_,
            new_file_name=file_name
        )
        
        # 3. Töröld az eredetit a forrás vödörből
        source_bucket.delete_file_version(file_version.id_, file_name)
        logger.info(f"Successfully moved and cleaned up {file_name}")
        return new_version
