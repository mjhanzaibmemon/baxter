#!/usr/bin/env python3
"""
Test script to verify Azure AD / Microsoft Graph API credentials

Run this to verify your credentials work BEFORE deploying to production.

Usage:
    python test_azure_credentials.py

Requirements:
    pip install msal requests python-dotenv
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")


def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")


def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")


def check_env_variables():
    """Check if all required environment variables are set."""
    print("\n" + "="*60)
    print("Step 1: Checking Environment Variables")
    print("="*60)
    
    required = {
        "GRAPH_TENANT_ID": os.getenv("GRAPH_TENANT_ID"),
        "GRAPH_CLIENT_ID": os.getenv("GRAPH_CLIENT_ID"),
        "GRAPH_CLIENT_SECRET": os.getenv("GRAPH_CLIENT_SECRET"),
        "MAILBOX_EMAIL": os.getenv("MAILBOX_EMAIL"),
    }
    
    all_set = True
    for key, value in required.items():
        if not value or value.strip() == "":
            print_error(f"{key} is not set")
            all_set = False
        else:
            # Mask sensitive values
            if "SECRET" in key:
                masked = value[:8] + "..." + value[-4:]
            else:
                masked = value
            print_success(f"{key} = {masked}")
    
    if not all_set:
        print_error("\nMissing required environment variables!")
        print_info("Please check your .env file and add all required values.")
        print_info("See AZURE_SETUP_GUIDE.md for instructions.")
        return False
    
    return True


def test_token_acquisition():
    """Test if we can acquire an access token."""
    print("\n" + "="*60)
    print("Step 2: Testing Token Acquisition")
    print("="*60)
    
    try:
        import msal
    except ImportError:
        print_error("msal library not installed")
        print_info("Run: pip install msal")
        return False
    
    tenant_id = os.getenv("GRAPH_TENANT_ID")
    client_id = os.getenv("GRAPH_CLIENT_ID")
    client_secret = os.getenv("GRAPH_CLIENT_SECRET")
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    try:
        print_info(f"Authority: {authority}")
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret,
        )
        
        print_info("Requesting token from Microsoft...")
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        if "access_token" in result:
            print_success("Successfully acquired access token!")
            print_info(f"Token expires in: {result.get('expires_in', 'N/A')} seconds")
            return result["access_token"]
        else:
            print_error("Failed to acquire token")
            print_error(f"Error: {result.get('error')}")
            print_error(f"Description: {result.get('error_description')}")
            
            if "AADSTS" in str(result.get('error_description', '')):
                print_warning("\nCommon Azure AD errors:")
                print("  - AADSTS700016: Application not found → Check CLIENT_ID")
                print("  - AADSTS7000215: Invalid secret → Check CLIENT_SECRET")
                print("  - AADSTS90002: Tenant not found → Check TENANT_ID")
            
            return None
            
    except Exception as e:
        print_error(f"Exception during token acquisition: {e}")
        return None


def test_mailbox_access(token):
    """Test if we can access the mailbox."""
    print("\n" + "="*60)
    print("Step 3: Testing Mailbox Access")
    print("="*60)
    
    try:
        import requests
    except ImportError:
        print_error("requests library not installed")
        print_info("Run: pip install requests")
        return False
    
    mailbox = os.getenv("MAILBOX_EMAIL")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Directly access mailbox messages (uses Mail.Read permission)
    print_info(f"Testing access to mailbox: {mailbox}")
    url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages?$top=1"
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            msg_count = len(data.get('value', []))
            print_success(f"Mailbox accessible! Found {msg_count} message(s)")
            if msg_count > 0:
                print_info(f"Latest email subject: {data['value'][0].get('subject', 'N/A')}")
        elif response.status_code == 404:
            print_error(f"Mailbox not found: {mailbox}")
            print_warning("Check if MAILBOX_EMAIL is correct")
            return False
        elif response.status_code == 403:
            print_error("Access denied (403 Forbidden)")
            print_error(f"Response: {response.text}")
            print_warning("Possible causes:")
            print("  - Admin consent not granted")
            print("  - Wrong permission type (delegated vs application)")
            print("  - Insufficient permissions")
            return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Exception during mailbox access: {e}")
        return False
    
    # Test 2: List messages (to verify Mail.Read permission)
    print_info("Testing Mail.Read permission...")
    url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages?$top=5&$select=id,subject,receivedDateTime"
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            message_count = len(data.get("value", []))
            print_success(f"Successfully read {message_count} messages from mailbox")
            
            if message_count > 0:
                print_info("Recent emails:")
                for msg in data["value"][:3]:
                    subject = msg.get("subject", "(no subject)")[:50]
                    date = msg.get("receivedDateTime", "N/A")[:10]
                    print(f"  • {date} - {subject}")
            else:
                print_warning("Mailbox is empty or no messages found")
            
            return True
        elif response.status_code == 403:
            print_error("Permission denied when reading messages")
            print_warning("Ensure Mail.Read permission is granted AND admin consent is given")
            return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Exception during message listing: {e}")
        return False


def main():
    print(f"\n{BLUE}{'='*60}")
    print("Microsoft Graph API Credentials Test")
    print("="*60 + RESET)
    
    # Step 1: Check environment variables
    if not check_env_variables():
        print_error("\n❌ Test failed at Step 1")
        sys.exit(1)
    
    # Step 2: Acquire token
    token = test_token_acquisition()
    if not token:
        print_error("\n❌ Test failed at Step 2")
        print_info("\nPlease verify your Azure AD credentials:")
        print("  1. Check TENANT_ID, CLIENT_ID, CLIENT_SECRET in .env")
        print("  2. Ensure the app registration exists in Azure Portal")
        print("  3. Verify the client secret hasn't expired")
        sys.exit(1)
    
    # Step 3: Test mailbox access
    if not test_mailbox_access(token):
        print_error("\n❌ Test failed at Step 3")
        print_info("\nPlease verify:")
        print("  1. MAILBOX_EMAIL is correct")
        print("  2. Mail.Read and Mail.ReadWrite permissions are added")
        print("  3. Admin consent is granted (green checkmarks in Azure Portal)")
        sys.exit(1)
    
    # All tests passed!
    print("\n" + "="*60)
    print_success("✅ ALL TESTS PASSED!")
    print("="*60)
    print(f"\n{GREEN}Your Azure AD credentials are correctly configured.{RESET}")
    print(f"{GREEN}You can now deploy the application to production.{RESET}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
