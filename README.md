# EduTrack

> **Intelligent Student Attendance Management System** — Integrates with Zoom via real-time webhooks, ML-powered student name matching, automated PDF reports, and a rich analytics dashboard.

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
cd zoom_attendance
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings (see Configuration section below)
```

### 3. Initialize Database & Seed Test Data

```bash
python seed_db.py
```

This will:
- Create all database tables
- Insert a test professor account: `dr.smith@university.edu` / `password123`
- Insert 30 students across 5 past sessions
- **Train the ML name matcher model** (takes ~30 seconds on first run)
- Compute risk scores and behavioral clusters

### 4. Run the Application

```bash
python run.py
```

Visit: [http://localhost:5000](http://localhost:5000)

---

## 🔧 Configuration (.env)

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Flask secret key | `change-me-in-prod` |
| `DATABASE_URL` | Database connection | `sqlite:///edutrack.db` |
| `ZOOM_ACCOUNT_ID` | Zoom Server-to-Server OAuth | From Zoom Marketplace |
| `ZOOM_CLIENT_ID` | Zoom App Client ID | From Zoom Marketplace |
| `ZOOM_CLIENT_SECRET` | Zoom App Client Secret | From Zoom Marketplace |
| `ZOOM_WEBHOOK_SECRET_TOKEN` | Zoom Webhook Verification | From Zoom event subscription |
| `MAIL_SERVER` | SMTP server | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USERNAME` | SMTP user | `you@gmail.com` |
| `MAIL_PASSWORD` | Gmail App Password | 16-char app password |
| `SESSION_DURATION_THRESHOLD` | Seconds to count as present | `3600` (1 hour) |

---

## 📹 Zoom App Setup (Server-to-Server OAuth)

### Step 1: Create Zoom App

1. Go to [Zoom Marketplace](https://marketplace.zoom.us/)
2. Click **Develop → Build App**
3. Choose **Server-to-Server OAuth**
4. Name it `EduTrack`

### Step 2: Configure Scopes

Add these scopes:
- `meeting:read:admin`
- `report:read:admin`

### Step 3: Get Credentials

Copy to your `.env`:
- **Account ID** → `ZOOM_ACCOUNT_ID`
- **Client ID** → `ZOOM_CLIENT_ID`
- **Client Secret** → `ZOOM_CLIENT_SECRET`

### Step 4: Configure Webhooks

1. In your app's **Feature** tab, enable **Event Subscriptions**
2. Add a subscription with your **ngrok URL** (see below)
3. Subscribe to these events:
   - `meeting.started`
   - `meeting.ended`
   - `meeting.participant_joined`
   - `meeting.participant_left`
4. Copy the **Verification Token** → `ZOOM_WEBHOOK_SECRET_TOKEN`

---

## 🌐 ngrok Setup (Webhooks for Local Dev)

Zoom needs a public HTTPS URL to send webhooks. Use ngrok:

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 5000
```

Copy the `https://xxxx.ngrok.io` URL and set it as your Zoom Webhook Endpoint URL:
```
https://xxxx.ngrok.io/webhook/zoom
```

> **Alternative**: Use the included `simulate_zoom.py` for testing without real Zoom.

---

## 🎮 Testing Without Zoom (Webhook Simulator)

```bash
# Run full meeting simulation
python simulate_zoom.py

# Custom options
python simulate_zoom.py --meeting-id 88001234567 --host dr.smith@university.edu --participants 15

# Point to different server
python simulate_zoom.py --url http://localhost:5000
```

The simulator will:
1. POST `meeting.started` (creates session in DB)
2. POST 12 `participant_joined` events (with fuzzy name variations)
3. Simulate 3 re-joins
4. POST `participant_left` events
5. POST `meeting.ended` → triggers attendance finalization + PDF generation

---

## 📊 Running Celery (Production / Full Mode)

By default in development, Celery tasks run **synchronously** (no Redis needed).

For production with real async processing:

```bash
# Terminal 1: Redis (via Docker)
docker run -p 6379:6379 redis:7-alpine

# Terminal 2: Celery Worker
celery -A app.tasks.celery_app.celery worker --loglevel=info --pool=solo

# Terminal 3: Celery Beat (scheduled tasks)
celery -A app.tasks.celery_app.celery beat --loglevel=info

# Terminal 4: Flask App
python run.py
```

Or use Docker Compose (includes all services):
```bash
docker-compose up
```

---

## 🤖 ML Model Training

### Name Matcher (runs automatically on first seed)
```bash
python -m app.ml.train_matcher
```
- Generates 10,000 synthetic name pair examples
- Trains RandomForestClassifier
- Target accuracy: ≥ 90%
- Saved to: `app/ml/name_matcher.pkl`

### Retrain with Professor Feedback
- When professors confirm/reject matches in the dashboard, pairs are saved to `app/ml/train_data/confirmed_pairs.jsonl`
- Nightly Celery beat task retrains the model automatically

---

## 📤 Uploading Students (Excel)

1. Navigate to **Upload Students** in the sidebar
2. Upload an `.xlsx` file with columns:
   - `Full Name`
   - `Email`
   - `Student ID`
   - `Course Code`
3. The system validates all rows before committing
4. Duplicate emails in the same course are skipped

---

## 🧪 Running Tests

```bash
pytest tests/ -v

# Run specific test file
pytest tests/test_matching.py -v
pytest tests/test_attendance.py -v
pytest tests/test_webhook.py -v

# With coverage
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
```

---

## 📁 Project Structure

```
zoom_attendance/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Dev/Prod/Test configs
│   ├── extensions.py        # db, login_manager, mail
│   ├── models.py            # 6 SQLAlchemy models
│   ├── routes/              # Blueprint routes
│   │   ├── auth.py          # Login/register/logout
│   │   ├── dashboard.py     # Analytics dashboard
│   │   ├── students.py      # Student CRUD + Excel upload
│   │   ├── sessions.py      # Session management
│   │   ├── reports.py       # PDF reports
│   │   ├── webhook.py       # Zoom webhook receiver
│   │   └── api.py           # JSON API for Chart.js
│   ├── services/            # Business logic
│   │   ├── zoom_auth.py     # Zoom OAuth token manager
│   │   ├── zoom_webhook.py  # Signature verification
│   │   ├── attendance.py    # Duration accumulation
│   │   ├── matching.py      # 3-layer ML matching
│   │   ├── report_gen.py    # ReportLab PDF generator
│   │   ├── email_service.py # Flask-Mail email sender
│   │   └── ml_analytics.py  # Risk, clustering, forecasting
│   ├── tasks/               # Celery async tasks
│   │   ├── celery_app.py    # Celery factory + beat schedule
│   │   ├── finalize_session.py # Post-session pipeline
│   │   └── retrain_models.py   # Nightly model retrain
│   ├── ml/                  # ML artifacts
│   │   ├── train_matcher.py # Training script
│   │   ├── name_matcher.pkl # Trained model (generated)
│   │   └── train_data/      # Training data files
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS, JS, reports
├── tests/
│   ├── conftest.py
│   ├── test_attendance.py
│   ├── test_matching.py
│   └── test_webhook.py
├── seed_db.py               # Database seeder
├── simulate_zoom.py         # Zoom webhook simulator
├── run.py                   # App entry point
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## 🔐 Security Notes

- All Zoom webhooks verified with HMAC-SHA256
- Replay attack protection (5-minute timestamp window)
- Passwords hashed with bcrypt via Werkzeug
- Session data protected with Flask-Login
- Database writes in webhook handlers wrapped in try/except with rollback
- Environment secrets loaded from `.env` (never committed)

---

## 📧 Gmail SMTP Setup

1. Enable 2FA on your Google account
2. Go to **Security → App Passwords**
3. Generate an app password for "Mail"
4. Set in `.env`: `MAIL_PASSWORD=your-16-char-app-password`

---

## 🏗️ Production Deployment

```bash
# Set production environment
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:pass@host:5432/edutrack

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"
```

---

*Built with Flask 3.x, scikit-learn, ReportLab, Chart.js, and Bootstrap 5.*
