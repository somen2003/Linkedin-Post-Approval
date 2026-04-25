# LinkedIn Post Approval Workflow

A multi-level email approval engine for LinkedIn posts. Submitters pick their name from a dropdown, paste content, and the system routes the post through L1 → L2 → L3 via email. Submitters from L1/L2/L3 are automatically skipped from their own approval step.

## Stack

- **FastAPI** (Python 3.11+) + **Uvicorn**
- **SQLite** via **SQLAlchemy** (swap to Postgres later via `DATABASE_URL`)
- **Jinja2** HTML templates
- **smtplib** (generic SMTP — Gmail / SendGrid / SES / Outlook / any)

## Quick Start (local)

### 1. Install

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your SMTP credentials, `BASE_URL`, and admin dashboard credentials.

### 3. Run

Tables auto-create on first run.

```bash
uvicorn main:app --reload
```

- Submitters visit: `http://localhost:8000/`
- Admin dashboard: `http://localhost:8000/dashboard` (HTTP Basic Auth prompt)

## How It Works

### Submission

1. Open `/` — form with a **name dropdown** and a **content** textarea.
2. Pick your name, paste content, submit.
3. System looks up your role from [app/config.py](app/config.py) and routes accordingly.
4. The HTTP response returns instantly; approval email sends in the background.

### Approval chain (skip-submitter rule)

| Submitter's role | Chain |
|---|---|
| L1 | L2 → L3 |
| L2 | L1 → L3 |
| L3 | L1 → L2 |
| OTHER | L1 → L2 → L3 |

### Email flow

Each approver receives an email with **Approve** and **Reject** buttons. Clicking opens a **confirmation page** (not auto-approved) — this prevents Outlook Safe Links and other email scanners from accidentally recording a decision.

- **Approve** at intermediate step → next approver receives an email.
- **Approve** at final step → the fully approved post is sent to **all of L1, L2, L3**.
- **Reject** at any step → workflow stops; submitter gets a notification with the reason.

### Current team (edit in `app/config.py`)

| Name | Role | Email |
|---|---|---|
| Somen Mishra | L1 | somenmishra333@gmail.com |
| Sthitapragnya Sahoo | L2 | sthitapragnya780@gmail.com |
| Surya Pratap | L3 | agenticsurya@gmail.com |
| Suvam Sen | OTHER | suvamsen172420@gmail.com |
| Tapan Das | OTHER | tapankumarpanda164@gmail.com |

---

## Deployment

### Before you deploy — checklist

1. **Change `ADMIN_PASSWORD`** in `.env` from the default to a long random string.
2. **Verify SMTP works locally first.** Submit a test post locally, confirm the email arrives.
3. **Decide on a host.** Recommended: **Render** (simplest free tier with persistent disks) or **Railway**. Either works.
4. **Pick a persistence strategy:**
   - **SQLite + persistent disk** (simplest, fine for low volume): keeps `data.db` on a mounted volume
   - **Postgres** (recommended for anything real): change `DATABASE_URL` to a Postgres connection string — no code changes, SQLAlchemy handles both
5. **Know what your public URL will be** (e.g. `https://cipher-approvals.onrender.com`) — you must set `BASE_URL` to this **exact** URL, because the Approve/Reject links in emails are built from it.
6. **Commit to git** (this repo has a `.gitignore` that already excludes `.env` and `data.db`). Never commit `.env`.

### Deploy to Render (step-by-step)

1. Create a free account at [render.com](https://render.com) and connect your GitHub.
2. Push this project to a GitHub repo.
3. In Render dashboard → **New → Web Service → Connect your repo**.
4. Fill in:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment → Add Environment Variable**, add every variable from your `.env`:
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`
   - `BASE_URL` → set this to the Render URL Render assigns you (e.g. `https://cipher-approvals.onrender.com`)
   - `DATABASE_URL` → leave as `sqlite:///./data.db` (if using persistent disk) **or** point to a Render Postgres instance
   - `ADMIN_USERNAME`, `ADMIN_PASSWORD`
   - `ACTION_TOKEN_EXPIRY_DAYS=7`
6. **For SQLite:** add a persistent disk — **Advanced → Add Disk**. Mount path: `/opt/render/project/src`, size: 1 GB.
7. Click **Create Web Service**. Wait for the first deploy (~2 minutes).
8. Visit `https://your-app.onrender.com/dashboard` — browser will prompt for admin login.

### Why email links only work after deployment

Locally, `BASE_URL` is `http://localhost:8000`. Emails send with links like `http://localhost:8000/approve/<token>`. When an approver clicks from their Gmail inbox, their browser tries to reach `localhost:8000` on *their* machine — which fails. That's why approvals appear broken locally when testing with real recipients.

Once deployed with `BASE_URL=https://your-app.onrender.com`, the links in outgoing emails become `https://your-app.onrender.com/approve/<token>` — which works from any device on the internet.

### After deployment

- Open the dashboard at `/dashboard`, log in with admin creds.
- Submit a test post as "Somen Mishra" (L1) → "Sthitapragnya Sahoo" (L2) receives the email with working buttons.
- Click Approve → confirm page → confirms → L3 gets the next email.
- L3 approves → final email fan-outs to all three Gmail inboxes.

---

## Performance

- **Email sending is non-blocking.** FastAPI's `BackgroundTasks` runs SMTP after the HTTP response returns, so the submitter sees the success page within ~200ms even though SMTP handshakes take 1–3s.
- **For high volume** (more than ~10 posts/min) move from background tasks to a proper queue (Redis + RQ, or Celery). Not needed at current scale.

## Project Structure

```
Email System/
├── main.py                  # FastAPI app entrypoint
├── requirements.txt
├── .env.example
├── app/
│   ├── config.py            # Settings + EMPLOYEES list (edit here)
│   ├── database.py          # SQLAlchemy engine / session
│   ├── models.py            # Post, ApprovalLog, ApprovalToken
│   ├── admin_auth.py        # HTTP Basic Auth for /dashboard
│   ├── schemas.py
│   ├── routers/
│   │   ├── pages.py         # GET / , GET /dashboard (admin-only)
│   │   ├── posts.py         # POST /api/posts
│   │   └── approvals.py     # /approve/:token, /reject/:token, /action/:token
│   ├── services/
│   │   ├── workflow.py      # Chain logic + state transitions
│   │   ├── email_service.py # Generic SMTP wrapper
│   │   └── tokens.py        # One-time action tokens
│   └── templates/           # Jinja2 HTML + email templates
├── static/styles.css
└── data.db                  # SQLite (auto-created, gitignored)
```

## Security

- `/dashboard` protected with HTTP Basic Auth (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).
- Approval email links are **single-use** and expire in 7 days.
- Confirm-page pattern prevents email scanners (Outlook Safe Links, Gmail link preview) from accidentally triggering approvals.
- Tokens: `secrets.token_urlsafe(32)` (~256 bits), stored hashed with SHA-256.
- **Always deploy behind HTTPS** — tokens travel in URLs.

## Extending

- **Add/change people** → edit `EMPLOYEES` in `app/config.py`.
- **Add L4, L5, …** → edit `approval_levels` in `app/config.py`. Chain logic, dashboard, and fan-out all read this list dynamically.
- **Move to Postgres** → change `DATABASE_URL` to `postgresql://...`.
- **Swap email provider** → update SMTP credentials in `.env`. No code change.
