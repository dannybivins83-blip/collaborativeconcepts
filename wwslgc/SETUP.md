# WWSLGC Portal — Deploy & Setup

Internal, login-gated mailer that lives inside the Collaborative Concepts site
and sends through Microsoft 365 (Graph) or Gmail. Portal URL:
**https://wwslgc.collaborativeconceptsfl.com/send**

> The `wwslgc.` subdomain **root** now serves the public WWS marketing landing
> page (`wwslgc/index.html`). This internal mailer lives at **`/send`**
> (`wwslgc/send/index.html`), routed by the `/send` rewrite in `vercel.json`.
> The mailer's `/api/*` calls and OAuth callbacks are unchanged.

There are 3 one-time setup blocks. Do them in this order. ~20 minutes total.

---

## 1. Register the app in Microsoft Entra (Azure AD)

This gives the portal permission to sign you in and send mail as you. You must
be a Microsoft 365 admin for lagalacon.com.

1. Go to **https://entra.microsoft.com** → **Identity → Applications → App registrations → New registration**.
2. **Name:** `WWSLGC Portal`
3. **Supported account types:** *Accounts in this organizational directory only (Single tenant)* — this is what restricts sign-in to lagalacon.com.
4. **Redirect URI:** platform **Web**, value:
   `https://wwslgc.collaborativeconceptsfl.com/api/auth/callback`
5. Click **Register**.
6. On the **Overview** page, copy these two — you'll paste them into Vercel:
   - **Application (client) ID** → `MS_CLIENT_ID`
   - **Directory (tenant) ID** → `MS_TENANT_ID`
7. **Certificates & secrets → New client secret** → description `wwslgc`, expiry 24 months → **Add**. Copy the **Value** immediately (it's only shown once) → `MS_CLIENT_SECRET`.
8. **API permissions → Add a permission → Microsoft Graph → Delegated permissions** → add:
   - `User.Read`
   - `Mail.Send`
   - `Mail.ReadWrite`
   Then click **Grant admin consent for La Gala** (the checkmark button).

---

## 2. Set environment variables in Vercel

Vercel project (collaborativeconcepts) → **Settings → Environment Variables**.
Add each for **Production** (and Preview if you want preview deploys to work):

| Name | Value |
|---|---|
| `MS_CLIENT_ID` | (from step 1.6) |
| `MS_TENANT_ID` | (from step 1.6) |
| `MS_CLIENT_SECRET` | (from step 1.7) |
| `SESSION_SECRET` | a long random string — see below |
| `WWSLGC_REDIRECT_URI` | `https://wwslgc.collaborativeconceptsfl.com/api/auth/callback` |
| `ALLOWED_EMAIL_DOMAIN` | `lagalacon.com` |

Generate a `SESSION_SECRET` (run locally, paste the output):
```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 3. Point the subdomain at Vercel (DNS is on Cloudflare)

1. **Vercel** → project → **Settings → Domains → Add** → enter
   `wwslgc.collaborativeconceptsfl.com`. Vercel shows the CNAME target
   (usually `cname.vercel-dns.com`).
2. **Cloudflare** → `collaborativeconceptsfl.com` → **DNS → Add record**:
   - Type **CNAME**, Name **wwslgc**, Target **cname.vercel-dns.com**
   - **Proxy status: DNS only (grey cloud)** — important, so Vercel manages HTTPS.
3. Back in Vercel, wait for the domain to show **Valid Configuration** (a minute or two).

---

## Deploy

Everything is committed to the repo. Push to the branch Vercel builds (usually `main`):
```
git add .
git commit -m "Add WWSLGC portal (login-gated Graph mailer)"
git push
```
Vercel auto-detects `requirements.txt` + `api/index.py` and builds the Python
functions. No Node needed.

---

## Test

1. Visit **https://wwslgc.collaborativeconceptsfl.com/send** → you should see the
   **Sign in with Microsoft** gate.
2. Sign in with your `@lagalacon.com` account (consent once).
3. Drag in a leads CSV (e.g. export from the tracker) → pick a template.
4. Click **Send 1 test to myself** → check your Outlook **Drafts** (the test
   creates a draft to your own address).
5. **Create drafts in Outlook** → review them in your mailbox → send when ready.

> The public marketing landing page is unaffected: the portal lives only at
> `wwslgc.collaborativeconceptsfl.com/send`, behind the Microsoft/Google sign-in.
> No lead data is stored on the server — CSVs are parsed in your browser and
> only finished emails are sent through Graph.

---

## Gmail (Google) send option

The portal can also send via Gmail. Google OAuth client lives in Google Cloud
project **deep-wares-394121** (Google Auth Platform → Clients → **WWSLGC Portal**),
redirect URI `https://wwslgc.collaborativeconceptsfl.com/api/auth/google/callback`,
Gmail API enabled, app in **Testing** with test users added. To finish, set in Vercel:

| Name | Value |
|---|---|
| `GOOGLE_CLIENT_ID` | from the WWSLGC Portal client (starts `202155726344-…`) |
| `GOOGLE_CLIENT_SECRET` | from the same client (Sensitive) |

Then redeploy. To allow a new Gmail sender, add it as a **Test user** under
Google Auth Platform → Audience. On first sign-in users see a "Google hasn't
verified this app" screen → **Advanced → Go to WWSLGC Portal → Allow** (expected
while the app is in Testing).

## Troubleshooting

- **"AADSTS50011 redirect URI mismatch"** → the redirect URI in Entra (step 1.4)
  must exactly equal `WWSLGC_REDIRECT_URI` (step 2). Check for http vs https / trailing slash.
- **Gate shows but sign-in loops** → `SESSION_SECRET` missing or changed between
  deploys (it must stay constant). Set it and redeploy.
- **"This portal is restricted to @lagalacon.com"** → you signed in with a
  different account; use your lagalacon.com one.
- **Graph 403 on send** → the `Mail.Send` / `Mail.ReadWrite` permissions weren't
  consented (step 1.8). Re-grant admin consent.
- **Function build fails** → confirm `requirements.txt` is at the repo root.
