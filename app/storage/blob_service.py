import os
from azure.storage.blob import BlobServiceClient


class BlobStorageService:
    _shared_local_store: dict[str, bytes] = {}

    def __init__(self):
        self.connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_BLOB_CONTAINER")
        self.client = None
        self.container = None
        if self.connection_string and self.container_name:
            self.client = BlobServiceClient.from_connection_string(self.connection_string)
            self.container = self.client.get_container_client(self.container_name)

    def _use_local_store(self) -> bool:
        return self.container is None

    def upload_file(self, blob_path: str, data: bytes):
        if self._use_local_store():
            self._shared_local_store[blob_path] = data
            return
        blob_client = self.container.get_blob_client(blob_path)
        blob_client.upload_blob(data, overwrite=True)

    def generate_read_url(self, blob_path: str) -> str:
        if self._use_local_store():
            return f"/api/v1/resumes/{blob_path}"
        blob_client = self.container.get_blob_client(blob_path)
        return blob_client.url

    def download_file(self, blob_path: str) -> bytes:
        if self._use_local_store():
            return self._shared_local_store.get(blob_path, b"")
        blob_client = self.container.get_blob_client(blob_path)
        return blob_client.download_blob().readall()
