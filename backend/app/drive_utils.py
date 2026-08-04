import json, os, io, requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        file_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        if file_path and os.path.exists(file_path):
            with open(file_path, "r") as f:
                creds_json = f.read()
        else:
            raise ValueError("GOOGLE_CREDENTIALS_JSON no configurado. " +
                "Agrega el JSON de la cuenta de servicio como variable de entorno en Railway.")
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def upload_pdf(pdf_bytes, filename, folder_id, mime_type="application/pdf"):
    """Upload file to Google Drive using simple upload"""
    service = get_drive_service()
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype=mime_type, resumable=False)
    file_metadata = {"name": filename, "parents": [folder_id]}
    file = service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
    file_id = file.get("id")
    # Hacer público (cualquiera con el link puede ver)
    service.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}).execute()
    web_link = file.get("webViewLink")
    direct_link = f"https://drive.google.com/uc?export=download&id={file_id}"
    return {"id": file_id, "url": web_link, "downloadUrl": direct_link}
