# VL Silks — Render + Aiven MySQL Deployment Guide

> **Stack:** Flask + Gunicorn → Render Free Web Service → Aiven Free MySQL  
> **Schema:** Pure MySQL 8.x (InnoDB, utf8mb4)  
> **Do NOT run schema.sql after seeding — it contains DROP TABLE statements.**

---

## Prerequisites

- Git repository on GitHub (public or private)
- Aiven account (free at aiven.io)
- Render account (free at render.com)

---

## A. Create Aiven MySQL Free Service

1. Log in to [Aiven Console](https://console.aiven.io)
2. Click **Create Service** → **MySQL**
3. Select **Free** plan
4. Choose a cloud region (e.g., `aws-ap-south-1` for India)
5. Service name: `vl-silks-mysql` (or any name)
6. Click **Create Service** — wait for the service to reach **Running** state

---

## B. Obtain Aiven Connection Details

From the Aiven service page → **Overview** tab, copy:

| Variable | Where to find |
|---|---|
| `DB_HOST` | **Host** field |
| `DB_PORT` | **Port** field |
| `DB_NAME` | **Database name** field (default: `defaultdb`) |
| `DB_USER` | **User** field (default: `avnadmin`) |
| `DB_PASSWORD` | **Password** field (click the eye icon) |

> **Rename the database if desired:** Aiven allows creating a new database within the service. If you create a database named `vl_silks_db`, use that as `DB_NAME`. Otherwise use `defaultdb`.

---

## C. Download the Aiven CA Certificate

The Aiven CA certificate is required for TLS verification.

1. In the Aiven console → service page → **Overview** tab
2. Scroll to **Connection Information**
3. Click **Download CA certificate** → saves as `ca.pem`

### Supplying ca.pem to Render safely

**Option 1 — Use Render Secret Files (Recommended):**

Render Secret Files allow you to securely attach certificate files directly to the running container without modifying git:

1. In Render Dashboard → select your Web Service → **Environment** tab → **Secret Files**
2. Click **Add Secret File**
3. Set **Filename**: `/etc/secrets/aiven-ca.pem`
4. Paste the entire content of the downloaded `ca.pem` file into the file contents editor
5. Click **Save Changes**
6. Set the Environment Variable on Render:
   ```
   MYSQL_SSL_CA=/etc/secrets/aiven-ca.pem
   ```

**Option 2 — Repository Certificate Path:**
Alternatively, place `ca.pem` in a project subfolder (e.g. `certs/aiven-ca.pem`) and configure:
```
MYSQL_SSL_CA=certs/aiven-ca.pem
```

> [!IMPORTANT]
> NEVER commit `DB_PASSWORD`, `SECRET_KEY`, or any database credentials to Git. Only the public root CA certificate is safe for SSL/TLS verification.

---

## D. Import schema.sql (ONCE — before first deploy)

Connect to Aiven MySQL with SSL:

```bash
mysql \
  --host=<DB_HOST> \
  --port=<DB_PORT> \
  --user=avnadmin \
  --password \
  --ssl-ca=certs/aiven-ca.pem \
  <DB_NAME> < database/schema.sql
```

Enter your Aiven password when prompted.

> **Warning:** schema.sql contains `DROP TABLE IF EXISTS` for all 15 tables.
> Run this ONLY ONCE before seeding, on a fresh/empty database.
> NEVER run again after the application is live — it will wipe all data.

---

## E. Import seed.sql (ONCE — immediately after schema)

```bash
mysql \
  --host=<DB_HOST> \
  --port=<DB_PORT> \
  --user=avnadmin \
  --password \
  --ssl-ca=certs/aiven-ca.pem \
  <DB_NAME> < database/seed.sql
```

This imports the initial demo data:
- 2 users (admin + staff)
- 7 categories, 4 suppliers, 9 products, 24 variants
- 5 customers, 5 sales, 3 purchases, credit ledger, returns

---

## F. Push Project to GitHub

```bash
cd "C:\Users\punee\Desktop\VL-Silks"
git init
git add .
git commit -m "Initial commit — VL Silks production-ready"
git remote add origin https://github.com/<your-username>/vl-silks.git
git push -u origin master
```

> `.env` is in `.gitignore` and will NOT be committed.  
> `scratch/` (DB backups) are also excluded.

---

## G. Create Render Web Service

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Web Service**
3. Connect your GitHub account if not already connected
4. Select the `vl-silks` repository
5. Configure:

| Field | Value |
|---|---|
| **Name** | `vl-silks` |
| **Region** | Choose closest to users |
| **Branch** | `master` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn "backend.app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |
| **Plan** | Free |

---

## H. Build Command

```
pip install -r requirements.txt
```

Render will install all packages from the root `requirements.txt`.

---

## I. Start Command

```
gunicorn "backend.app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

- `$PORT` is automatically provided by Render
- `--workers 2` is appropriate for the free tier (512 MB RAM)
- `--timeout 120` allows for PDF generation requests

---

## J. Set Render Environment Variables

In Render → your service → **Environment** tab, add:

| Variable | Value |
|---|---|
| `FLASK_ENV` | `production` |
| `FLASK_DEBUG` | `0` |
| `SECRET_KEY` | *(generate: see below)* |
| `DB_HOST` | *(from Aiven — your host)* |
| `DB_PORT` | *(from Aiven — your port)* |
| `DB_NAME` | *(Aiven database name, e.g. `defaultdb` or `vl_silks_db`)* |
| `DB_USER` | *(from Aiven — your user)* |
| `DB_PASSWORD` | *(from Aiven — your password)* |
| `MYSQL_SSL_CA` | `certs/aiven-ca.pem` *(or `/etc/secrets/aiven-ca.pem`)* |

**Do NOT set `TEST_DB_NAME` in Render.**

### Generate a secure SECRET_KEY

Run locally:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the `SECRET_KEY` value in Render.

---

## K. Configure Health Check

In Render → your service → **Settings** → **Health Check Path**:

```
/api/health
```

Render will GET this endpoint every 90 seconds. The app responds:
```json
{"status": "ok", "service": "VL Silks", "database": "connected"}
```

---

## L. First Login & Password Security After Deploy
 
Initial administrator and staff accounts are provisioned directly by importing `database/seed.sql`.
 
> [!IMPORTANT]
> **Change Default Passwords Immediately:**
> For production security, log in immediately upon deployment and change the passwords for both the Admin and Staff accounts via the **User Management** page (`/users/edit/<id>`).
> 
> Never commit, share, or publish production database user credentials or application login passwords in public repositories or public documentation.

---

## M. Verify Dashboard After Deploy

1. Open `https://<your-render-app>.onrender.com`
2. Log in as Admin
3. Verify dashboard shows:
   - 9 products / 24 variants
   - 5 recent invoices
   - Credit to Collect visible
   - Category Sales doughnut chart renders
4. Navigate to Reports → run Sales Report
5. Test PDF download for a customer credit statement

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| App fails to start with `RuntimeError: Production configuration validation failed` | Missing/incorrect Render env vars | Check all required variables are set in Render |
| `Database error: SSL connection error` | Wrong `MYSQL_SSL_CA` path or missing cert | Verify ca.pem is committed and path matches env var |
| `Database 'vl_silks_db' does not exist` | `DB_NAME` does not match Aiven database | Use the exact database name from Aiven console |
| `Access denied for user` | Wrong `DB_USER` or `DB_PASSWORD` | Copy credentials directly from Aiven console |
| App works but PDF fonts are system Helvetica | DejaVu not installed on Render | Normal — PDF falls back to Helvetica gracefully |

---

## Important Safety Notes

1. **schema.sql has DROP TABLE** — import only once on a fresh database
2. **seed.sql imports demo data** — import once; can be re-imported only on an empty schema
3. **Never set `TEST_DB_NAME`** on Render — the production isolation guard will reject it
4. **Render free tier restarts** after 15 minutes of inactivity — first request after restart may be slow (~30s)
5. **Render ephemeral filesystem** — no files written to disk persist across deploys (PDF/CSV are memory-only, so no issue)
