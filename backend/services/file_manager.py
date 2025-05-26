# services/file_manager.py
import os
import uuid
from pathlib import Path
from typing import List, Tuple

from fastapi import UploadFile, HTTPException, status
from config.settings import settings
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

class FileManager:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.storage_bucket = settings.SUPABASE_STORAGE_BUCKET

    async def upload_files(self, files: List[UploadFile], triage_id: str) -> List[Tuple[str, str]]:
        """
        Uploads a list of UploadFile objects to Supabase Storage
        within a folder named after the triage_id.
        Returns a list of (Supabase file path, Public URL) tuples.
        """
        uploaded_file_info = [] # stores the file paths and public URLs
        for file in files: # Iterate over each file
            # Generate a unique filename
            file_extension = Path(file.filename).suffix if file.filename else "" # Get the file extension
            unique_filename = f"{uuid.uuid4()}{file_extension}" # Generate a unique filename
            file_path = f"{triage_id}/{unique_filename}" # Path in Supabase Storage

            try:
                # Upload the file to Supabase Storage
                contents = await file.read() # Read the file contents
                if not contents:
                    raise ValueError(f"File '{file.filename}' is empty")
                
                # upload the file
                # Check if file exists — delete if so (manual upsert)
                try:
                    self.supabase.storage.from_(self.storage_bucket).remove([file_path])
                except Exception:
                    pass  # File might not exist, that's fine

                # Upload file
                response = self.supabase.storage.from_(self.storage_bucket).upload(
                    path=file_path,
                    file=contents,
                    file_options={"content-type": file.content_type or "application/octet-stream"}
                )


                if response and getattr(response, 'error', None) is None: # Check if the upload was successful
                    # Get the public URL for the uploaded file
                    public_url = self.supabase.storage.from_(self.storage_bucket).get_public_url(file_path)
                    uploaded_file_info.append((file_path, public_url)) # Store the file path and public URL in the list
                    print(f"Uploaded {file.filename} to Supabase: {public_url}")
                else:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload file to Supabase")
                
            except Exception as e:
                print(f"Error uploading {file.filename}: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload file: {file.filename}")
            
        return uploaded_file_info
    

# Instantiate FileManager after the class definition
file_manager = FileManager()
