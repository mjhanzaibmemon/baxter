# Azure AD Setup Guide for Microsoft Graph API

This guide will help you set up Azure AD credentials to access Microsoft 365 emails via Graph API.

---

## Prerequisites

- **Microsoft 365 account** (the mailbox that receives Excel files)
- **Azure Portal access** (same Microsoft account)
- **Global Admin or Application Admin role** (to create app registrations)

---

## Step 1: Access Azure Portal

1. Go to: **https://portal.azure.com**
2. Sign in with your Microsoft 365 account
3. Search for **"Azure Active Directory"** or **"Microsoft Entra ID"** in the top search bar

---

## Step 2: Create App Registration

1. In Azure Active Directory, click **"App registrations"** from the left menu
2. Click **"+ New registration"**

3. Fill in the details:
   - **Name**: `Email Ingestor Service` (or any name you prefer)
   - **Supported account types**: Select **"Accounts in this organizational directory only"**
   - **Redirect URI**: Leave blank (not needed for service apps)

4. Click **"Register"**

---

## Step 3: Copy Application (Client) ID and Tenant ID

After registration, you'll see the app overview page:

1. **Copy and save** the following values (you'll need these later):
   ```
   Application (client) ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Directory (tenant) ID:   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

> **Save these somewhere safe!** You'll put them in the `.env` file later.

---

## Step 4: Create Client Secret

1. In your app registration, click **"Certificates & secrets"** from the left menu
2. Click **"+ New client secret"**
3. Add a description: `Ingestor Secret`
4. Set expiration: **24 months** (or longer if available)
5. Click **"Add"**

6. **⚠️ IMPORTANT**: Copy the **"Value"** immediately!
   ```
   Client Secret Value: ABC~xyz123-example-secret-value-here
   ```
   > **This will only be shown ONCE!** If you lose it, you'll need to create a new one.

---

## Step 5: Configure API Permissions

1. Click **"API permissions"** from the left menu
2. Click **"+ Add a permission"**
3. Select **"Microsoft Graph"**
4. Select **"Application permissions"** (NOT Delegated)

5. Search and add these permissions:
   - ✅ **`Mail.Read`** - Read mail in all mailboxes
   - ✅ **`Mail.ReadWrite`** - Read and write mail in all mailboxes (for marking as read)

6. Click **"Add permissions"**

7. **⚠️ CRITICAL**: Click **"Grant admin consent for [Your Organization]"**
   - This button has a shield icon
   - Click it and confirm **"Yes"**
   - You should see green checkmarks next to the permissions

> **Without admin consent, the app won't work!**

---

## Step 6: Verify Permissions

Your API permissions table should look like this:

| API / Permissions name | Type | Admin consent required | Status |
|------------------------|------|------------------------|--------|
| Mail.Read | Application | Yes | ✅ Granted for [Org] |
| Mail.ReadWrite | Application | Yes | ✅ Granted for [Org] |

---

## Step 7: Get Your Mailbox Email Address

The email address that receives the Excel attachments. Example:
```
logistics@yourcompany.com
```

---

## ✅ Final Checklist

You should now have these 4 values:

```bash
GRAPH_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
GRAPH_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
GRAPH_CLIENT_SECRET=ABC~xyz123-example-secret-value-here
MAILBOX_EMAIL=logistics@yourcompany.com
```

---

## What's Next?

Once you have these credentials:

1. **For testing locally**: Add them to your `.env` file
2. **For EC2 deployment**: Share them securely with the developer (use encrypted channels)

---

## Troubleshooting

### "Insufficient privileges to complete the operation"
- You need **Global Admin** or **Application Admin** role to grant admin consent
- Ask your IT admin to complete Step 5.7

### "Authentication failed"
- Double-check Tenant ID and Client ID are correct
- Make sure Client Secret wasn't truncated when copied
- Verify admin consent was granted (green checkmarks)

### "Access denied"
- Ensure you selected **Application permissions**, not Delegated
- Verify `Mail.Read` and `Mail.ReadWrite` are both added and consented

---

## Security Notes

- **Never commit credentials to Git**
- Use environment variables only
- Rotate Client Secrets every 6-12 months
- Limit permissions to only what's needed (we only need Mail.Read + Mail.ReadWrite)

---

## Need Help?

If you encounter any issues during setup, share:
1. Screenshot of the error (hide sensitive values)
2. Which step you're stuck on
3. Your Azure AD role/permissions
