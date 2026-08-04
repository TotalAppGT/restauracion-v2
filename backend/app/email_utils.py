import httpx
import os

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "REDIL Restauración <no-reply@totalappgt.online>")
RESEND_API_URL = "https://api.resend.com/emails"

def send_email(to_emails, subject, html_body, attachments=None, smtp_user=None, smtp_password=None):
    if not isinstance(to_emails, list):
        to_emails = [to_emails]
    try:
        payload = {
            "from": RESEND_FROM,
            "to": to_emails,
            "subject": subject,
            "html": html_body
        }
        if attachments:
            payload["attachments"] = []
            for att in attachments:
                payload["attachments"].append({
                    "filename": att.get("filename", "file.pdf"),
                    "content": att.get("content", "")
                })
        resp = httpx.post(
            RESEND_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        if resp.status_code >= 400:
            raise Exception(f"Resend error {resp.status_code}: {resp.text}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        raise e
