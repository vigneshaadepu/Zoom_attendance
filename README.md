<div align="center">

  <h1>🎓 EduTrack</h1>
  <p><b>Enterprise-Grade Student Attendance Engine & ML Analytics Platform</b></p>

  <p><i>Automated Zoom Webhooks • 3-Layer Machine Learning Matcher • Behavioral Risk Analytics • Automated PDF Reporting</i></p>

  <p>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></a>
    <a href="https://flask.palletsprojects.com"><img src="https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/></a>
    <a href="https://scikit-learn.org"><img src="https://img.shields.io/badge/scikit--learn-RandomForest-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white" alt="scikit-learn"/></a>
    <a href="https://docs.celeryq.dev"><img src="https://img.shields.io/badge/Celery-Async_Queue-37B24D?style=for-the-badge&logo=celery&logoColor=white" alt="Celery"/></a>
    <a href="https://redis.io"><img src="https://img.shields.io/badge/Redis-7.x-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis"/></a>
    <a href="https://docker.com"><img src="https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/></a>
  </p>

  <p>
    <a href="https://git.io/typing-svg"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=17&pause=1000&color=38BDF8&center=true&vcenter=true&width=650&lines=Automated+Zoom+Server-to-Server+Webhooks;3-Layer+Machine+Learning+Name+Matcher;Active+Learning+%26+Automated+Nightly+Retraining;Real-time+Behavioral+Risk+%26+Attendance+Clustering" alt="Typing SVG" /></a>
  </p>

  <br/>

  <p>
    <a href="#-executive-overview"><img src="https://img.shields.io/badge/📖_Overview-1E293B?style=for-the-badge&logoColor=white"/></a>
    <a href="#-flagship-capabilities"><img src="https://img.shields.io/badge/✨_Features-1E293B?style=for-the-badge&logoColor=white"/></a>
    <a href="#-system-architecture"><img src="https://img.shields.io/badge/🏛️_Architecture-1E293B?style=for-the-badge&logoColor=white"/></a>
    <a href="#-ml--matching-pipeline"><img src="https://img.shields.io/badge/🤖_ML_Engine-1E293B?style=for-the-badge&logoColor=white"/></a>
    <a href="#-technology-stack-matrix"><img src="https://img.shields.io/badge/🛠️_Tech_Stack-1E293B?style=for-the-badge&logoColor=white"/></a>
    <a href="#-quick-start--installation"><img src="https://img.shields.io/badge/🚀_Quick_Start-1E293B?style=for-the-badge&logoColor=white"/></a>
  </p>

</div>

---

## ⚡ Executive Overview

> [!IMPORTANT]  
> **EduTrack** replaces error-prone manual attendance taking with an enterprise-grade, event-driven pipeline. By seamlessly capturing real-time Zoom telemetries, running multi-stage machine learning identity resolution, and generating predictive risk analytics, EduTrack turns raw meeting events into actionable academic intelligence.

<table width="100%">
  <tr>
    <th width="50%" align="center">❌ Traditional Manual Tracking</th>
    <th width="50%" align="center">✅ EduTrack Intelligent Engine</th>
  </tr>
  <tr>
    <td>
      • Manual roster cross-referencing with high error margin<br/>
      • Single join-time snapshot ignores mid-session drops<br/>
      • Delayed visibility into student absenteeism trends<br/>
      • Labor-intensive administrative report compilation
    </td>
    <td>
      • <b>3-Layer ML Name Matcher</b> (Exact + Fuzzy + RandomForest)<br/>
      • <b>Cumulative duration tracking</b> across leave/re-join events<br/>
      • <b>Real-time student risk scoring & behavioral clustering</b><br/>
      • <b>Automated PDF generation & scheduled SMTP dispatch</b>
    </td>
  </tr>
</table>

---

## ✨ Flagship Capabilities

<table width="100%">
  <tr>
    <td width="50%" valign="top">
      <h3>📡 Real-Time Webhook Engine</h3>
      <img src="https://img.shields.io/badge/Ingestion-Event--Driven-0284C7?style=flat-square"/>
      <br/><br/>
      Captures Zoom lifecycle events (<code>started</code>, <code>ended</code>, <code>joined</code>, <code>left</code>). Uses an event-driven state machine to handle participant drops and re-joins, accurately accumulating active presence duration.
    </td>
    <td width="50%" valign="top">
      <h3>🤖 3-Layer ML Name Matcher</h3>
      <img src="https://img.shields.io/badge/Accuracy-%E2%89%A590%25-16A34A?style=flat-square"/>
      <br/><br/>
      Cascading resolution pipeline: <b>Exact Match</b> $\rightarrow$ <b>Fuzzy Levenshtein</b> $\rightarrow$ <b>RandomForest Classifier</b> (10k synthetic pairs). Features human-in-the-loop active feedback logged to <code>confirmed_pairs.jsonl</code>.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>📊 Risk & Behavioral Analytics</h3>
      <img src="https://img.shields.io/badge/Analytics-Predictive-7C3AED?style=flat-square"/>
      <br/><br/>
      Calculates real-time risk scores and groups students into behavioral clusters (<i>High Risk</i>, <i>Moderate Risk</i>, <i>Consistent</i>). Powered by Chart.js REST endpoints and bulk Excel (<code>.xlsx</code>) imports.
    </td>
    <td width="50%" valign="top">
      <h3>⚙️ Async Pipeline & PDF Engine</h3>
      <img src="https://img.shields.io/badge/Task_Queue-Celery_%2B_Redis-EA580C?style=flat-square"/>
      <br/><br/>
      Offloads heavy post-session workflows via Celery workers. Compiles professional ReportLab PDF reports and automatically emails summaries via SMTP.
    </td>
  </tr>
</table>

---

## 🏛️ System Architecture

```mermaid
graph TD
    classDef external fill:#1e293b,stroke:#0284c7,stroke-width:2px,color:#fff;
    classDef security fill:#0f172a,stroke:#eab308,stroke-width:2px,color:#fff;
    classDef async fill:#0f172a,stroke:#16a34a,stroke-width:2px,color:#fff;
    classDef analytics fill:#0f172a,stroke:#9333ea,stroke-width:2px,color:#fff;

    Z[Zoom API / Webhook Event]:::external -->|HTTPS Payload| B[Flask Webhook Gateway]:::security
    B -->|HMAC-SHA256 Verification| V[Anti-Replay Guard]:::security
    V -->|Validated Payload| C[Celery Task Queue & Redis Broker]:::async
    C --> M[3-Layer ML Name Matcher]:::async
    M -->|Classified Record| DB[(SQLAlchemy Database)]:::async
    DB --> R[ML Risk & Clustering Analytics]:::analytics
    DB --> P[ReportLab PDF Generator]:::analytics
    R --> D[Interactive Dashboard & REST APIs]:::analytics
    P --> E[SMTP Mail Service]:::analytics
```

---

## 🔬 ML & Matching Pipeline

Identity resolution follows a 3-tier cascade to eliminate manual name matching overhead:

<table width="100%">
  <tr>
    <th width="25%">Layer 1: Exact Match</th>
    <th width="25%">Layer 2: Fuzzy Distance</th>
    <th width="25%">Layer 3: RandomForest</th>
    <th width="25%">Active Feedback</th>
  </tr>
  <tr>
    <td align="center">
      <img src="https://img.shields.io/badge/Layer_1-O(1)_Lookup-10B981?style=for-the-badge"/><br/><br/>
      Direct normalized string equivalence check.
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/Layer_2-Levenshtein-06B6D4?style=for-the-badge"/><br/><br/>
      Calculates string distance for minor typos.
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/Layer_3-RandomForest-8B5CF6?style=for-the-badge"/><br/><br/>
      Evaluates complex patterns (10k sample model).
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/Feedback-Active_Learning-F59E0B?style=for-the-badge"/><br/><br/>
      Nightly retraining via Celery Beat tasks.
    </td>
  </tr>
</table>

<br/>

> [!TIP]
> **Human-in-the-Loop Feedback**: When a professor confirms or rejects a name suggestion in the UI, the result is saved to `app/ml/train_data/confirmed_pairs.jsonl`. The scheduled Celery Beat task automatically retrains the RandomForest model nightly.

---

## 🛠️ Technology Stack Matrix

| Domain | Integrated Technologies & Tooling |
| :--- | :--- |
| **Backend Framework** | <img src="https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white"/> <img src="https://img.shields.io/badge/Werkzeug-Bcrypt-000000?style=flat-square"/> <img src="https://img.shields.io/badge/Flask--Login-Auth-000000?style=flat-square"/> <img src="https://img.shields.io/badge/Flask--Mail-SMTP-000000?style=flat-square"/> |
| **Machine Learning** | <img src="https://img.shields.io/badge/Scikit--Learn-RandomForest-F7931E?style=flat-square&logo=scikit-learn&logoColor=white"/> <img src="https://img.shields.io/badge/NumPy-Vectorized-013243?style=flat-square&logo=numpy&logoColor=white"/> <img src="https://img.shields.io/badge/Pandas-DataFrames-150458?style=flat-square&logo=pandas&logoColor=white"/> |
| **Async & Infrastructure** | <img src="https://img.shields.io/badge/Celery-Task_Queue-37B24D?style=flat-square&logo=celery&logoColor=white"/> <img src="https://img.shields.io/badge/Celery_Beat-Scheduler-37B24D?style=flat-square"/> <img src="https://img.shields.io/badge/Redis-7.x_Broker-DC382D?style=flat-square&logo=redis&logoColor=white"/> |
| **Database & ORM** | <img src="https://img.shields.io/badge/SQLAlchemy-6_Models-D7101C?style=flat-square&logo=sqlalchemy&logoColor=white"/> <img src="https://img.shields.io/badge/SQLite-Dev-003B57?style=flat-square&logo=sqlite&logoColor=white"/> <img src="https://img.shields.io/badge/PostgreSQL-Production-4169E1?style=flat-square&logo=postgresql&logoColor=white"/> |
| **Reporting & Frontend** | <img src="https://img.shields.io/badge/ReportLab-PDF_Engine-FF6C37?style=flat-square"/> <img src="https://img.shields.io/badge/Chart.js-REST_API-FF6384?style=flat-square&logo=chartdotjs&logoColor=white"/> <img src="https://img.shields.io/badge/Bootstrap-5.x-7952B3?style=flat-square&logo=bootstrap&logoColor=white"/> |
| **DevOps & Testing** | <img src="https://img.shields.io/badge/Docker-Containers-2496ED?style=flat-square&logo=docker&logoColor=white"/> <img src="https://img.shields.io/badge/Docker_Compose-Orchestration-2496ED?style=flat-square"/> <img src="https://img.shields.io/badge/Pytest-Test_Suite-0A9EDC?style=flat-square&logo=pytest&logoColor=white"/> |

---

## 🚀 Quick Start & Installation

### 1. Repository Setup
```bash
git clone https://github.com/vigneshaadepu/Zoom_attendance.git
cd Zoom_attendance

# Initialize virtual environment
python -m venv venv
# Windows: venv\Scripts\activate | Unix: source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

### 2. Database & ML Initialization
```bash
python seed_db.py
```
> [!NOTE]
> `seed_db.py` creates database schema tables, inserts demo professor credentials (`dr.smith@university.edu` / `password123`), generates 30 student records across 5 sessions, trains the RandomForest model (`app/ml/name_matcher.pkl`), and calculates behavioral risk scores.

### 3. Launch Application

<details>
<summary><b>🔥 Option A: Local Development Server</b></summary>
<br/>

```bash
python run.py
# Access Web Dashboard at http://localhost:5000
```
</details>

<details>
<summary><b>🐳 Option B: Full Production Container Stack (Docker & Celery)</b></summary>
<br/>

```bash
# Spins up Redis broker, Celery worker, Celery Beat scheduler, and Gunicorn application
docker-compose up --build
```
</details>

---

## 📹 Zoom Integration & Webhook Simulation

> [!TIP]
> **No Zoom Account Required for Testing**: Use the included simulation utility `simulate_zoom.py` to trigger full meeting lifecycles offline.

```bash
# Execute standard Zoom meeting simulation
python simulate_zoom.py

# Execute custom simulation with specific meeting parameters
python simulate_zoom.py --meeting-id 88001234567 --host dr.smith@university.edu --participants 15
```

<details>
<summary><b>🔑 Production Zoom Server-to-Server OAuth Configuration</b></summary>
<br/>

1. Build a **Server-to-Server OAuth App** in the [Zoom Marketplace](https://marketplace.zoom.us/).
2. Grant administrative scopes: `meeting:read:admin` and `report:read:admin`.
3. Enable **Event Subscriptions** pointing to `https://<your-domain>/webhook/zoom` for:
   - `meeting.started`, `meeting.ended`, `meeting.participant_joined`, `meeting.participant_left`
4. Configure `.env` keys:
   ```env
   ZOOM_ACCOUNT_ID=your_account_id
   ZOOM_CLIENT_ID=your_client_id
   ZOOM_CLIENT_SECRET=your_client_secret
   ZOOM_WEBHOOK_SECRET_TOKEN=your_verification_token
   ```
</details>

---

## 🧪 Testing & Security Infrastructure

<table width="100%">
  <tr>
    <td width="50%" valign="top">
      <h3>🛡️ Security Protections</h3>
      • <b>HMAC-SHA256</b> signature verification on all webhooks.<br/>
      • <b>5-Minute Anti-Replay</b> window to prevent payload replay attacks.<br/>
      • <b>Bcrypt Password Hashing</b> via Werkzeug.<br/>
      • <b>SQLAlchemy Rollbacks</b> on exception state.
    </td>
    <td width="50%" valign="top">
      <h3>🧪 Automated Testing</h3>
      <pre><code># Run full pytest suite
pytest tests/ -v

# Run targeted test suites
pytest tests/test_matching.py -v
pytest tests/test_webhook.py -v

# Code coverage report
pytest tests/ --cov=app</code></pre>
    </td>
  </tr>
</table>

<br/>

<div align="center">

  <hr style="border: 1px solid #1e293b; width: 100%;"/>

  <p><b>🎓 EduTrack Platform</b> • Enterprise Student Attendance Engine</p>
  <p><sub>Built with Flask 3.x, Scikit-Learn, Celery, Redis, ReportLab, and Bootstrap 5</sub></p>

</div>
