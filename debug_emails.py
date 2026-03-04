#!/usr/bin/env python3
"""Debug script to check emails manually via Graph API"""
import os
import msal
import requests
from dotenv import load_dotenv
import json

load_dotenv()

tenant_id = os.getenv("GRAPH_TENANT_ID")
client_id = os.getenv("GRAPH_CLIENT_ID")
client_secret = os.getenv("GRAPH_CLIENT_SECRET")
mailbox = os.getenv("MAILBOX_EMAIL")

# Get token
authority = f"https://login.microsoftonline.com/{tenant_id}"
app = msal.ConfidentialClientApplication(
    client_id,
    authority=authority,
    client_credential=client_secret,
)
result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
token = result["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Check ALL emails (not just unread)
print("\n" + "="*60)
print("Checking ALL emails in mailbox...")
print("="*60)
url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages?$top=10&$select=id,subject,isRead,hasAttachments,receivedDateTime"
resp = requests.get(url, headers=headers)
data = resp.json()

print(f"\nFound {len(data.get('value', []))} recent emails:\n")
for i, email in enumerate(data.get("value", []), 1):
    print(f"{i}. Subject: {email.get('subject')}")
    print(f"   Read: {email.get('isRead')}")
    print(f"   Has Attachments: {email.get('hasAttachments')}")
    print(f"   Received: {email.get('receivedDateTime')}")
    
    # Get attachments for this email
    att_url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages/{email['id']}/attachments"
    att_resp = requests.get(att_url, headers=headers)
    attachments = att_resp.json().get('value', [])
    
    if attachments:
        print(f"   Attachments ({len(attachments)}):")
        for att in attachments:
            print(f"     - {att.get('name')} ({att.get('size')} bytes)")
    else:
        print(f"   Attachments: None")
    print()

# Now check with filter
print("\n" + "="*60)
print("Checking UNREAD emails with hasAttachments=true filter...")
print("="*60)
filter_url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages?$filter=isRead eq false and hasAttachments eq true&$select=id,subject,hasAttachments"
filter_resp = requests.get(filter_url, headers=headers)
filter_data = filter_resp.json()

print(f"\nFound {len(filter_data.get('value', []))} emails matching filter\n")
for email in filter_data.get('value', []):
    print(f"- {email.get('subject')}")
