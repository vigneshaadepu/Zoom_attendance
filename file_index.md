# EduTrack — Complete Project File Directory & Functionality Index

This document provides an exhaustive, line-item index of every single file in the EduTrack project and describes its exact functionality in the application.

---

## 1. Project Root Directory (`/`)
*   **`.env`**: Configuration file containing environment-specific variables, database connections, SMTP secrets, and local flags.
*   **`.env.example`**: A template file documenting the required keys for the `.env` file so developers know what configurations to create.
*   **`requirements.txt`**: Declares all external Python package dependencies (Flask, SQLAlchemy, openpyxl, RapidFuzz, ReportLab, etc.) with version details for installation.
*   **`run.py`**: The main execution script. Creates the Flask application context and runs the local development server on `http://localhost:5000`.
*   **`seed_db.py`**: A database seeding utility that populates SQLite with test professors, student rosters, past sessions, and reports.
*   **`workflow_guide.md`**: Architectural document explaining how the system calculates and matches attendance.
*   **`file_index.md`**: Index of files and their functions (this document).
*   **`README.md`**: General documentation, installation guides, and setup guidelines.

---

## 2. Core Application Root (`app/`)
*   **`app/__init__.py`**: Initializes the Flask application instance using the App Factory pattern, binds SQLAlchemy and Login Manager extensions, and registers blueprints.
*   **`app/config.py`**: Defines configuration classes (Development, Production, Testing) that load values from the `.env` file.
*   **`app/extensions.py`**: Instantiates global extensions shared across blueprints (SQLAlchemy `db`, Flask-Login `login_manager`, and Flask-Mail `mail`).
*   **`app/models.py`**: Defines SQLAlchemy database ORM schemas:
    *   `Professor`: Handles professor profile and authentication credentials.
    *   `RegisteredStudent`: Manages enrolled student data (Name, Email, Student ID, Course).
    *   `ZoomSession`: Stores Zoom session headers, meeting IDs, and start/end times.
    *   `AttendanceRecord`: Compiles session attendance states for students (Present, Partial, Absent, Duration).
    *   `ParticipantEvent`: Stores raw join/leave events parsed from Zoom logs.
    *   `AttendanceReport`: Links session analytics to generated PDF files and mail delivery flags.

---

## 3. Web Views & Routing Blueprints (`app/routes/`)
*   **`app/routes/__init__.py`**: Makes the blueprints folder a Python package.
*   **`app/routes/auth.py`**: Controls professor login, logout, account registration views, and session authentication states.
*   **`app/routes/dashboard.py`**: Prepares dashboard KPIs (e.g., total students, average rates, at-risk rosters) and passes them to the analytics HTML view.
*   **`app/routes/students.py`**: Handles student rosters, Excel uploads, student profiles, and the global database reset function.
*   **`app/routes/sessions.py`**: Controls session histories, session details, and handles the **Zoom CSV Participant Uploader** logic.
*   **`app/routes/reports.py`**: Manages generated PDF report downloads and manual report email triggers.
*   **`app/routes/api.py`**: Hosts JSON endpoints providing chart analytics and live feed updates to the browser.
*   **`app/routes/webhook.py`**: Listener endpoints for real-time Zoom webhook integrations.

---

## 4. Business Logic Services (`app/services/`)
*   **`app/services/__init__.py`**: Makes the services folder a Python package.
*   **`app/services/matching.py`**: Compares Zoom display names and emails with enrolled students, enforcing strict perfect matches.
*   **`app/services/attendance.py`**: Accumulates total connection duration across multiple joins/leaves and finalizes session statuses.
*   **`app/services/report_gen.py`**: Renders PDF summaries containing tables and breakdown charts.
*   **`app/services/email_service.py`**: Connects to SMTP servers to email generated PDF reports to professors.
*   **`app/services/ml_analytics.py`**: Evaluates attendance histories to assign student risk profiles.
*   **`app/services/zoom_auth.py`**: Handles OAuth handshakes with Zoom API servers.
*   **`app/services/zoom_webhook.py`**: Validates the signatures of Zoom webhook payloads to prevent unauthorized access.

---

## 5. Web Templates (`app/templates/`)
*   **`app/templates/base.html`**: The master HTML layout defining navigation sidebars, page topbars, and Bootstrap/AOS/SweetAlert2 scripts.
*   **`app/templates/dashboard.html`**: The home dashboard displaying KPI cards, Chart.js views, and participant review modules.

### Authentication View Subfolder (`app/templates/auth/`)
*   **`app/templates/auth/login.html`**: Sign-in page.
*   **`app/templates/auth/register.html`**: Sign-up page.

### Student View Subfolder (`app/templates/students/`)
*   **`app/templates/students/list.html`**: Displays the student roster, with a search bar and status filters.
*   **`app/templates/students/detail.html`**: Displays individual student profiles and attendance records.
*   **`app/templates/students/upload.html`**: The Excel roster uploader page.

### Sessions View Subfolder (`app/templates/sessions/`)
*   **`app/templates/sessions/list.html`**: Lists Zoom session histories.
*   **`app/templates/sessions/detail.html`**: Displays session details, attendance stats, and timelines.
*   **`app/templates/sessions/upload_csv.html`**: The Zoom Participant CSV uploader.

### Reports View Subfolder (`app/templates/reports/`)
*   **`app/templates/reports/list.html`**: Lists PDF reports with attendance percentage filters.

---

## 6. Static Web Assets (`app/static/`)
*   **`app/static/css/style.css`**: Global style sheet defining dark-mode properties, colors, transitions, and element layouts.
*   **`app/static/js/charts.js`**: Controls Chart.js visualizations on the dashboard.
*   **`app/static/js/dashboard.js`**: Manages client-side operations, AJAX calls, and SweetAlert2 notifications.

---

## 7. Testing Modules (`tests/`)
*   **`tests/__init__.py`**: Makes the tests folder a Python package.
*   **`tests/conftest.py`**: Configures test environments, setups, and fixture database contexts.
*   **`tests/test_attendance.py`**: Tests join/leave timeline aggregations and duration logic.
*   **`tests/test_matching.py`**: Tests Name and Email strict-match rules.
*   **`tests/test_webhook.py`**: Tests webhook signature verification and URL validation challenges.
