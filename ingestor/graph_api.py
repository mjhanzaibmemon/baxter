"""
graph_api.py — Microsoft Graph API integration for reading Outlook emails.

Supports two modes:
  DEMO_MODE=true   → reads .xlsx files from local DEMO_EXCEL_DIR folder
  DEMO_MODE=false  → authenticates via MSAL and polls real mailbox
"""
import base64
import logging
import os
import time
from pathlib import Path

import msal
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# --- Retry-enabled HTTP session ---
def _get_session() -> requests.Session:
    """Create a requests session with automatic retry on failures."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=2,          # 0s, 2s, 4s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "PATCH"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _get_access_token() -> str:
    """Acquire OAuth2 token using client credentials (Application permissions)."""
    tenant_id     = os.getenv("GRAPH_TENANT_ID")
    client_id     = os.getenv("GRAPH_CLIENT_ID")
    client_secret = os.getenv("GRAPH_CLIENT_SECRET")

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(f"Could not acquire Graph API token: {result.get('error_description')}")
    return result["access_token"]


def _get_allowed_senders() -> list[str]:
    """Get list of allowed sender emails from env var."""
    senders = os.getenv("ALLOWED_SENDERS", "")
    if not senders:
        return []  # Empty means allow all
    return [s.strip().lower() for s in senders.split(",") if s.strip()]


def _get_allowed_keywords() -> list[str]:
    """Get list of allowed filename keywords from env var."""
    keywords = os.getenv("ALLOWED_FILE_KEYWORDS", "")
    if not keywords:
        return []  # Empty means allow all
    return [k.strip().lower() for k in keywords.split(",") if k.strip()]


def _get_unread_excel_emails(token: str, mailbox: str) -> list[dict]:
    """Fetch unread emails with .xlsx attachments from the mailbox."""
    session = _get_session()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get allowed senders for filtering
    allowed_senders = _get_allowed_senders()
    
    url = (
        f"{GRAPH_BASE}/users/{mailbox}/messages"
        f"?$filter=isRead eq false and hasAttachments eq true"
        f"&$select=id,subject,receivedDateTime,hasAttachments,from"
        f"&$top=50"
    )
    emails = []
    while url:
        resp = session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        for email in data.get("value", []):
            # Filter by sender if ALLOWED_SENDERS is set
            if allowed_senders:
                sender_email = email.get("from", {}).get("emailAddress", {}).get("address", "").lower()
                if sender_email not in allowed_senders:
                    logger.info(f"  ↳ Skipping email from {sender_email} (not in allowed senders)")
                    continue
            emails.append(email)
        
        url = data.get("@odata.nextLink")
    return emails


def _get_excel_attachments(token: str, mailbox: str, message_id: str) -> list[tuple]:
    """
    Download .xlsx attachments from a specific email.
    Returns list of (filename, bytes_content) tuples.
    Only downloads files matching ALLOWED_FILE_KEYWORDS if set.
    """
    session = _get_session()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}/attachments"
    resp = session.get(url, headers=headers, timeout=60)
    resp.raise_for_status()

    # Get allowed keywords for filtering
    allowed_keywords = _get_allowed_keywords()

    attachments = []
    for att in resp.json().get("value", []):
        filename = att.get("name", "")
        if not filename.lower().endswith(".xlsx"):
            continue
        
        # Filter by filename keywords if ALLOWED_FILE_KEYWORDS is set
        if allowed_keywords:
            filename_lower = filename.lower()
            if not any(kw in filename_lower for kw in allowed_keywords):
                logger.info(f"  ↳ Skipping file {filename} (no matching keyword)")
                continue
        
        content = base64.b64decode(att["contentBytes"])
        attachments.append((att["name"], content))
        logger.info(f"Downloaded attachment: {att['name']} ({len(content):,} bytes)")
    return attachments


def _mark_email_read(token: str, mailbox: str, message_id: str):
    """Mark an email as read after successful processing."""
    session = _get_session()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}"
    session.patch(url, headers=headers, json={"isRead": True}, timeout=10)


def poll_mailbox() -> list[tuple]:
    """
    Main entry point. Returns list of (filename, bytes, email_id) tuples.

    In DEMO_MODE: reads Excel files from DEMO_EXCEL_DIR.
    In real mode:  polls Microsoft Graph API.
    """
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    if demo_mode:
        return _poll_demo_folder()
    else:
        return _poll_graph_api()


def _poll_demo_folder() -> list[tuple]:
    """Read Excel files from local demo folder (for demo recording)."""
    excel_dir = Path(os.getenv("DEMO_EXCEL_DIR", "/app/sample_data"))
    logger.info(f"[DEMO MODE] Reading Excel files from: {excel_dir}")

    results = []
    if not excel_dir.exists():
        logger.warning(f"[DEMO MODE] Directory not found: {excel_dir}")
        return results

    for xlsx_file in sorted(excel_dir.glob("*.xlsx")):
        file_bytes = xlsx_file.read_bytes()
        results.append((xlsx_file.name, file_bytes, f"demo::{xlsx_file.name}"))
        logger.info(f"[DEMO MODE] Found file: {xlsx_file.name} ({len(file_bytes):,} bytes)")

    return results


def _poll_graph_api() -> list[tuple]:
    """Poll real Microsoft Graph API mailbox for new Excel attachments."""
    mailbox = os.getenv("MAILBOX_EMAIL")
    if not mailbox:
        raise ValueError("MAILBOX_EMAIL env var is required for real Graph API mode")

    logger.info(f"[GRAPH API] Polling mailbox: {mailbox}")
    token = _get_access_token()
    emails = _get_unread_excel_emails(token, mailbox)
    logger.info(f"[GRAPH API] Found {len(emails)} unread emails with attachments")

    results = []
    for email in emails:
        msg_id = email["id"]
        attachments = _get_excel_attachments(token, mailbox, msg_id)
        for fname, fbytes in attachments:
            results.append((fname, fbytes, msg_id))
        if attachments:
            _mark_email_read(token, mailbox, msg_id)

    return results


def send_email_alert(subject: str, body: str, is_success: bool = True):
    """
    Send email alert via Microsoft Graph API.
    
    Args:
        subject: Email subject line
        body: Email body (plain text or HTML)
        is_success: True for success alerts, False for errors
    """
    alert_email = os.getenv("ALERT_EMAIL")
    mailbox = os.getenv("MAILBOX_EMAIL")
    
    if not alert_email or not mailbox:
        logger.warning("ALERT_EMAIL or MAILBOX_EMAIL not configured - skipping alert")
        return
    
    # Skip in demo mode
    if os.getenv("DEMO_MODE", "true").lower() == "true":
        logger.info(f"[DEMO MODE] Would send alert: {subject}")
        return
    
    try:
        session = _get_session()
        token = _get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        # Build email message
        emoji = "✅" if is_success else "❌"
        message = {
            "message": {
                "subject": f"{emoji} {subject}",
                "body": {
                    "contentType": "HTML",
                    "content": f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
    <h2 style="color: {'#28a745' if is_success else '#dc3545'};">{emoji} {subject}</h2>
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
        <pre style="margin: 0; white-space: pre-wrap; font-family: Consolas, monospace;">{body}</pre>
    </div>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #666; font-size: 12px;">Baxter Email Ingestion Service | {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>
</body>
</html>"""
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": alert_email
                        }
                    }
                ],
            },
            "saveToSentItems": "false"
        }
        
        url = f"{GRAPH_BASE}/users/{mailbox}/sendMail"
        resp = session.post(url, headers=headers, json=message, timeout=30)
        resp.raise_for_status()
        logger.info(f"Alert email sent to {alert_email}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
