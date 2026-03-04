# Quick Start: Testing Azure Credentials

Follow these steps to set up and test your Azure credentials before deployment.

---

## Step 1: Set Up Azure AD App

👉 **Follow the complete guide**: [AZURE_SETUP_GUIDE.md](./AZURE_SETUP_GUIDE.md)

You need to:
1. Create an App Registration in Azure Portal
2. Get Tenant ID and Client ID
3. Create a Client Secret
4. Add Mail.Read + Mail.ReadWrite permissions
5. Grant admin consent

After completing the setup, you'll have these 4 values:
```
GRAPH_TENANT_ID=...
GRAPH_CLIENT_ID=...
GRAPH_CLIENT_SECRET=...
MAILBOX_EMAIL=...
```

---

## Step 2: Update .env File

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Azure credentials:
   ```env
   # Change DEMO_MODE to false
   DEMO_MODE=false

   # Add your Azure credentials
   GRAPH_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   GRAPH_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   GRAPH_CLIENT_SECRET=ABC~xyz123...
   MAILBOX_EMAIL=logistics@yourcompany.com
   ```

---

## Step 3: Install Test Dependencies

```bash
pip install msal requests python-dotenv
```

---

## Step 4: Run the Test Script

```bash
python test_azure_credentials.py
```

### Expected Output (Success):

```
============================================================
Microsoft Graph API Credentials Test
============================================================

============================================================
Step 1: Checking Environment Variables
============================================================
✓ GRAPH_TENANT_ID = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
✓ GRAPH_CLIENT_ID = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
✓ GRAPH_CLIENT_SECRET = ABC~xyz1...xyz9
✓ MAILBOX_EMAIL = logistics@company.com

============================================================
Step 2: Testing Token Acquisition
============================================================
ℹ Authority: https://login.microsoftonline.com/xxxxxxxx...
ℹ Requesting token from Microsoft...
✓ Successfully acquired access token!
ℹ Token expires in: 3599 seconds

============================================================
Step 3: Testing Mailbox Access
============================================================
ℹ Testing access to mailbox: logistics@company.com
✓ Mailbox found: Logistics Team
ℹ UPN: logistics@company.com
ℹ Testing Mail.Read permission...
✓ Successfully read 15 messages from mailbox
ℹ Recent emails:
  • 2026-03-03 - Shipment Report - Excel Attachment
  • 2026-03-03 - Daily Logistics Update
  • 2026-03-02 - Carrier Performance Data

============================================================
✅ ALL TESTS PASSED!
============================================================

Your Azure AD credentials are correctly configured.
You can now deploy the application to production.
```

---

## Common Errors and Fixes

### ❌ Error: "AADSTS7000215: Invalid client secret"
**Fix**: 
- Client secret is wrong or expired
- Go back to Azure Portal → Certificates & secrets → Create new secret
- Update `GRAPH_CLIENT_SECRET` in `.env`

### ❌ Error: "Mailbox not found"
**Fix**: 
- Check `MAILBOX_EMAIL` spelling
- Ensure the mailbox exists in your M365 tenant

### ❌ Error: "Access denied (403 Forbidden)"
**Fix**: 
- Admin consent not granted
- Go to Azure Portal → App Registration → API Permissions
- Click "Grant admin consent for [Your Org]"
- Ensure green checkmarks appear

### ❌ Error: "Application not found"
**Fix**: 
- Wrong Tenant ID or Client ID
- Verify these values in Azure Portal → App Registration → Overview

---

## What's Next?

Once the test passes ✅:

1. **For local testing**: Run `docker compose up -d --build`
2. **For EC2 deployment**: Share credentials with your deployment team
3. **Send credentials securely**: Use encrypted email or password manager

---

## Need Help?

If the test fails, share:
1. The complete error output from `test_azure_credentials.py`
2. Screenshot of your Azure AD app permissions (hide sensitive values)
3. Your role in Azure AD (e.g., Global Admin, User, etc.)
