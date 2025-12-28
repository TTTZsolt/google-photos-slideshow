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
        # generator for listing files
        for file_version, folder_name in bucket.ls():
            yield file_version

    def get_download_url(self, bucket_name: str, file_name: str, valid_duration_seconds: int = 7200):
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
        return authorized_url
