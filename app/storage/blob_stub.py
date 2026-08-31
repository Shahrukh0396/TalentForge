import os
from azure.storage.blob import BlobServiceClient

class BlobStorageService:
    def __init__(self):
        self.connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_BLOB_CONTAINER")

        print("Using blob container:", self.container_name)


        if not self.connection_string:
            raise RuntimeError(
                "AZURE_BLOB_CONNECTION_STRING is not set"
            )

        if not self.container_name:
            raise RuntimeError(
                "AZURE_BLOB_CONTAINER is not set"
            )


        self.client = BlobServiceClient.from_connection_string(
            self.connection_string
        )
        self.container = self.client.get_container_client(
            self.container_name
        )

    def upload_file(self, blob_path: str, data: bytes):
        blob_client = self.container.get_blob_client(blob_path)
        blob_client.upload_blob(data, overwrite=True)

    def generate_read_url(self, blob_path: str) -> str:
        # Temporary placeholder (SAS comes later)
        blob_client = self.container.get_blob_client(blob_path)
        return blob_client.url
    
    def download_file(self, blob_path: str) -> bytes:
        blob_client = self.container.get_blob_client(blob_path)
        return blob_client.download_blob().readall()

    def blob_exists(self, blob_path: str) -> bool:
        blob_client = self.container.get_blob_client(blob_path)
        return blob_client.exists()
