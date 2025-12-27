from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

class GooglePhotosClient:
    def __init__(self, creds: Credentials):
        self.service = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

    def list_media_items(self, page_size=100):
        """Yields media items from the library."""
        next_page_token = None
        while True:
            results = self.service.mediaItems().list(
                pageSize=page_size,
                pageToken=next_page_token
            ).execute()
            
            items = results.get('mediaItems', [])
            for item in items:
                yield item
            
            next_page_token = results.get('nextPageToken')
            if not next_page_token:
                break

    def get_media_item(self, media_id):
        return self.service.mediaItems().get(mediaId=media_id).execute()
