# There were no collabrators.
  Name : B. Chandra Sekhar Reddy
  PRN  : 250200299

# University OD Approval System

A complete Django + PostgreSQL website for Sai University On-Duty (OD) permission workflow.

## Approval Flow

Student → Faculty/Mentor → Dean → Admin visibility/reporting

## Latest Upgrade Included

This package includes the UI/UX + security upgrade requested after the initial build:

- Modern responsive dashboard UI with smoother transitions, polished cards, improved sidebar, icons, mobile menu, table hover effects, loading overlay, and clearer upload screens.
- Website-level rate limiting through `security.middleware.RateLimitMiddleware`.
- Student login is now staff-authorized only.
- Faculty can upload assigned student credentials.
- Dean can upload student credentials for their school.
- Admin can import student credentials globally.
- Student login is blocked unless the student has an active staff-uploaded profile.
- Uploaded student passwords are hashed immediately with Django authentication; plain-text passwords are not stored.

## Features

- Staff-controlled student login, profile, OD application, OD history, cancellation, PDF OD letter download.
- Faculty dashboard for assigned student requests, proof verification, approve-forward, reject with remarks, filters, student history, and student credential upload.
- Dean dashboard, school-scoped requests, final approval/rejection, OD rules, approval delay analytics, reports, faculty add/delete/transfer, and student credential upload.
- Admin dashboard, users, deans add/delete/transfer, faculty transfer, schools, departments, OD categories, OD rules, audit logs, student CSV/XLSX import, reports.
- PostgreSQL database configured for pgAdmin4.
- Role-based access control and safe querysets.
- CSRF protection, login attempt throttling, site-level rate limiting, session timeout, hashed passwords.
- Secure upload validation: PDF/JPG/JPEG/PNG only for OD proof documents, and CSV/XLSX only for student credential imports.
- Audit logs for important actions.
- QR verification page for approved OD letters.
- Excel, CSV, and PDF report exports.

## Project Structure

```text
od_approval_system/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
├── od_approval_system/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/
├── students/
├── faculty/
├── dean/
├── adminpanel/
├── od/
├── reports/
├── notifications/
├── security/
├── templates/
├── static/
│   ├── css/
│   ├── js/
│   ├── files/
│   └── images/
├── media/
└── database/
```

## PostgreSQL Setup

### Option A: pgAdmin4

1. Open pgAdmin4.
2. Connect to your PostgreSQL server.
3. Right-click **Databases** → **Create** → **Database**.
4. Database name: `od_approval_db`.
5. Owner: `postgres` or your PostgreSQL user.
6. Save.

### Option B: Query Tool

Open pgAdmin4 Query Tool and run:

```sql
CREATE DATABASE od_approval_db;
```

Optional dedicated user:

```sql
CREATE USER od_user WITH ENCRYPTED PASSWORD 'change_this_password';
GRANT ALL PRIVILEGES ON DATABASE od_approval_db TO od_user;
```

## pgAdmin4 Connection Fields

- Host: `localhost`
- Port: `5432`
- Maintenance database: `postgres`
- Username: `postgres`
- Password: your PostgreSQL password

## Local Setup Commands

### Windows PowerShell

```powershell
cd od_approval_system
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set your PostgreSQL password:

```env
DB_NAME=od_approval_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
```

Run migrations and seed data:

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Updating an Existing Copy

If you already ran the older version, copy this upgraded project over your existing files, then run:

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

The new migration adds staff-upload authorization fields to student profiles.

## Default Demo Login Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@sai.local` | `Admin@12345` |
| Dean | `dean@sai.local` | `Dean@12345` |
| Faculty | `faculty@sai.local` | `Faculty@12345` |
| Student | `student@sai.local` | `Student@12345` |

The demo student is marked as staff-uploaded by the seed command, so the student login works after `python manage.py seed_demo`.

## Student Credential Upload Rules

Students cannot self-register into the OD workflow. They can login only when an authorized Faculty, Dean, or Admin uploads their credentials.

### Faculty Upload

URL/page: Faculty Dashboard → **Upload Students**

Faculty upload requires these columns:

```csv
email,roll_number,password
```

Optional columns:

```csv
first_name,last_name,mobile,year,section,semester
```

Faculty uploads automatically map students to the faculty member's own school, department, and mentor account.

### Dean Upload

URL/page: Dean Dashboard → **Upload Students**

Dean upload requires:

```csv
email,roll_number,password,department_code
```

Optional:

```csv
first_name,last_name,mobile,year,section,semester,mentor_email
```

Dean uploads are restricted to the dean's own school. If `mentor_email` is provided, it must belong to active faculty in the same school and department.

### Admin Upload

URL/page: Admin Dashboard → **Import Students**

Admin upload requires:

```csv
first_name,last_name,email,mobile,roll_number,school_code,department_code,year,section,semester,mentor_email,password
```

A template is included in:

```text
static/files/student_credentials_template.csv
```

Also available inside the project under:

```text
database/student_credentials_template.csv
```

## Rate Limiting Configuration

Rate limiting is enabled by default. You can adjust it in `.env`:

```env
RATE_LIMIT_ENABLED=True
RATE_LIMIT_GENERAL_PER_MINUTE=180
RATE_LIMIT_POST_PER_MINUTE=35
RATE_LIMIT_LOGIN_PER_MINUTE=8
RATE_LIMIT_UPLOAD_PER_5_MINUTES=10
```

A blocked request returns HTTP `429 Too Many Requests`.

## Create Superuser Manually

```powershell
python manage.py createsuperuser
```

## Important Notes About Official Sai University Data

The `seed_demo` command includes Sai University schools and public dean/faculty reference records based on Sai University public web pages. These records are created as inactive `@official.sai.local` accounts with unusable passwords, so they are reference/demo records only. Activate/reset only if your university officially assigns those users to this system.

Sources used in the seed data include official Sai University pages for:

- School of Computing and Data Science
- School of Arts and Sciences
- School of Law
- School of Artificial Intelligence
- School of Media
- School of Technology
- School of Business
- School of Allied Health Sciences
- Sai University media kit logo

## Security Checklist

Before deployment:

- Set `DEBUG=False`.
- Use a strong `SECRET_KEY`.
- Use a dedicated PostgreSQL user, not `postgres`.
- Configure `ALLOWED_HOSTS`.
- Serve static/media through a production web server.
- Enable HTTPS and secure cookies.
- Keep uploaded documents private behind authenticated views if production policy requires it.
- Review official staff records before activating accounts.
- Do not share uploaded student credential files after import.

## Main URLs

- Home: `/`
- Login: `/login/`
- Student dashboard: `/students/dashboard/`
- Faculty dashboard: `/faculty/dashboard/`
- Faculty student upload: `/faculty/students/upload/`
- Dean dashboard: `/dean/dashboard/`
- Dean student upload: `/dean/students/upload/`
- Admin dashboard: `/adminpanel/dashboard/`
- Admin student import: `/adminpanel/import-students/`
- Django admin: `/django-admin/`
- Reports: `/reports/`
- Notifications: `/notifications/`
- QR verification: `/od/verify/<verification-id>/`

## Final Power Upgrade Pack

This version adds the requested production-style upgrade set:

- OpenRouter AI chatbot inside the website.
- Import preview validation before saving student credentials.
- Faculty/dean/admin controlled student login authorization.
- Admin student transfer between school, department, section, semester, and mentor.
- Dean student transfer within the dean's school.
- Admin dean add/delete/transfer.
- Dean faculty add/delete/transfer.
- Admin faculty transfer/deactivate.
- Secure proof-document download through permission-checked Django views.
- Digital signature upload for faculty/dean profiles.
- OD letter PDF with QR verification, digital hash, and signature blocks.
- OD calendar view for all roles.
- Admin/dean analytics with status, department, OD type, and approval delay views.
- Force temporary password change after admin reset.
- PWA manifest and service worker for app-like mobile loading.
- External notification hooks for email, Fast2SMS SMS, and WhatsApp/Twilio configuration.
- Docker, Docker Compose, Nginx example, production `.env`, and PostgreSQL backup scripts.

## OpenRouter AI Chatbot Setup

The chatbot uses OpenRouter's OpenAI-compatible chat-completions API endpoint.

1. Create an OpenRouter API key.
2. Add it to `.env`:

```env
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=openrouter/free
SITE_URL=http://127.0.0.1:8000
```

3. Restart Django:

```powershell
python manage.py runserver
```

The floating chatbot button appears after login. It answers OD workflow questions and respects the user's role context.

## Digital Signature Setup

Faculty and Dean users can upload a signature from:

```text
Profile → Digital Signature
```

Allowed formats:

```text
PNG, JPG, JPEG up to 2 MB
```

The signatures appear in final approved OD PDF letters.

## Secure Document Access

Proof files are no longer linked directly through raw media URLs in request pages. They are served through:

```text
/od/documents/<document-id>/
```

Access is checked by role:

- Student: own documents only
- Faculty: assigned students only
- Dean: school-scoped documents only
- Admin: all documents

Every document view is written to audit logs.

## Student Transfer Pages

Admin:

```text
/adminpanel/students/
/adminpanel/students/<student-id>/transfer/
```

Dean:

```text
/dean/students/
/dean/students/<student-id>/transfer/
```

Dean transfer is restricted to the dean's own school.

## Calendar and Analytics URLs

```text
/reports/calendar/
/reports/analytics/
```

Calendar is available for all authenticated roles with role-scoped data. Analytics is available for Admin and Dean.

## Production / Docker Commands

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8000/
```

For production, copy:

```text
deployment/.env.production.example
```

and configure real secrets, domain, PostgreSQL password, HTTPS, and OpenRouter key.

## PostgreSQL Backup

PowerShell:

```powershell
.\scripts\backup_postgres.ps1
```

Linux/macOS:

```bash
./scripts/backup_postgres.sh
```

## Final Verification Performed Before Packaging

The project was checked with:

```powershell
python -m compileall -q .
python manage.py check
python manage.py makemigrations --check --dry-run
```

Template URL reverse checks and template load checks were also performed to catch broken URL names and template syntax problems.
