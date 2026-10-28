# CivicConnect — Crowdsourced Civic Issue Reporting & Resolution

Citizens report local issues (potholes, garbage, streetlights, water leaks…) with a map pin and photo.
Department officers review and resolve them with proof; administrators manage users, departments,
assignments, verification, reports and audit logs.

**Stack:** Flask · SQLAlchemy + Flask-Migrate (SQLite) · Flask-Login · Flask-WTF · Pillow · Leaflet/OpenStreetMap · Chart.js · pytest

> ## Honest status
> This project was generated in a sandbox **without internet access**, so Flask-SQLAlchemy, Flask-Login,
> Flask-WTF and pytest could **not be installed or run there**. What *was* verified: every Python file
> compiles, and every Jinja template parses. What was **not** verified: the app has never been started and the
> pytest suite has never been executed. Treat the first run as a test run — see [Troubleshooting](#troubleshooting)
> and report/fix any failures. Migration files were also not generated (see [Database](#database-setup)).

## Feature checklist
| Feature | Implemented | Tested (tests written) | Notes |
|---|---|---|---|
| Register / login / logout, hashed passwords, CSRF | ✅ | ✅ | Public sign-up creates citizens only |
| Role-based access (citizen / authority / admin) enforced server-side | ✅ | ✅ | `utils/decorators.py` + service-level checks |
| Complaint submit, edit (while Submitted), withdraw, reference numbers | ✅ | ✅ | `CC-YYYY-XXXXXX` |
| Image upload validation (Pillow, random names, re-encode, size limit) | ✅ | ✅ | Files stored outside `static/` |
| Leaflet map picker + geocoding + manual coordinates | ✅ | ❌ browser-only | Needs manual browser test |
| Status-transition policy | ✅ | ✅ | `services/complaint_service.py` |
| Department/officer assignment, accept/reject, internal notes, info requests | ✅ | ✅ | |
| Resolution proof + admin verification + reopen | ✅ | ✅ | |
| Feedback (1 per complaint, DB-unique) | ✅ | ✅ | |
| In-app notifications (+ polling badge) | ✅ | ✅ (creation) | Email not implemented (optional) |
| Role dashboards + Chart.js (real queries) | ✅ | ✅ (pages load) | |
| Admin: users, departments, categories, reports, CSV export, audit log | ✅ | ✅ | |
| Public map/listing with privacy protections | ✅ | ✅ | Rounded coords, no PII/photos |
| Rate limiting (login, register, submit) | ✅ | ❌ | In-memory; use Flask-Limiter+Redis for multi-worker |
| Custom 403/404/429/500 pages | ✅ | ✅ (404) | |
| Alembic migration files | ❌ pending | – | Generate with commands below |
| Email notifications | ❌ pending | – | `MAIL_ENABLED` flag reserved |
| Content-Security-Policy header | ❌ pending | – | Needs allow-list for CDN scripts |

## Project structure
```
app/            application package (factory in __init__.py, CLI in cli.py)
  models/       one file per table          services/   business rules (complaint, upload, stats, notify, audit)
  auth|citizen|authority|admin|public/  blueprints (routes.py + forms.py)
  templates/    base, macros/, components/, per-role pages, errors/
  static/       css/ js/                    utils/      decorators, validators, helpers, rate limiter
scripts/ seed_data.py, create_admin.py      tests/      pytest suite (temp DB + temp upload dir per test)
config.py  run.py  wsgi.py  Procfile  render.yaml  requirements.txt  .env.example
```
Design decisions: routes stay thin; **all workflow rules live in `services/complaint_service.py`** so they can't
drift between roles. Uploads and the SQLite DB live in `instance/` (or `DATA_DIR`), never in `static/`; images are
served by `/media/<file>` only after an authorization check. Records are never hard-deleted (users, departments and
categories are deactivated) so the audit trail stays intact.

## Database schema (summary)
`users` (role, department_id) · `departments` · `categories` · `complaints` (reference_number unique, lat/lng checks,
status/priority, department_id, assigned_officer_id) · `complaint_updates` (public/internal timeline) ·
`resolutions` (proof, admin verification) · `feedback` (unique per complaint, rating 1–5) · `notifications` · `audit_logs`.

### Status policy
`Submitted → Under Review → Assigned → In Progress → Resolved`; `Rejected` (reason required); `Withdrawn` (citizen only,
while Submitted/Under Review). `Resolved` only through the resolution form (officer/admin); reopening
(`Resolved/Rejected → Under Review`) is admin-only. Citizens can never resolve.

## Local setup
**Linux / macOS**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit SECRET_KEY
```
**Windows (PowerShell)**
```powershell
py -m venv venv; venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### Database setup
Quick start (creates tables + default departments/categories):
```bash
flask --app run init-db
```
Proper migrations (recommended; commit the generated `migrations/` folder):
```bash
flask --app run db init
flask --app run db migrate -m "initial schema"
flask --app run db upgrade
flask --app run init-db          # inserts default departments/categories
```

### Create the first administrator
```bash
flask --app run create-admin       # prompts for email, name and password (hidden)
```
For automation, set `CIVICCONNECT_ADMIN_PASSWORD` in the environment instead of typing it. Never commit passwords.

### Demo data (optional, clearly labelled `[DEMO]`)
```bash
flask --app run seed
```
Creates `admin@`, `officer1@`…`officer5@`, `citizen@` `demo.civicconnect.local` accounts (password `Demo@12345`).
**Never run the seed on a production database.**

### Run
```bash
flask --app run run --debug        # http://127.0.0.1:5000
```
Officers: create them in **Admin → Users → Add user** (role *authority* + a department).

## Tests
```bash
pytest -v
```
Each test uses a temporary SQLite file and a temporary upload folder; your real data is never touched.

## Deployment (Render)
GitHub Pages **cannot** run Flask or SQLite — deploy the whole app to Render (or similar).
1. Push to GitHub (`.env`, `*.db`, `instance/` and uploads are git-ignored).
2. Render → New → Blueprint → select the repo (uses `render.yaml`), or create a Web Service manually:
   build `pip install -r requirements.txt`, start `flask --app wsgi init-db && gunicorn wsgi:app`.
3. Environment: `FLASK_ENV=production`, `SECRET_KEY` (random), `DATA_DIR=/var/data`.
4. Attach a **persistent disk** mounted at `/var/data` (SQLite + uploads). Verify current Render pricing/limits:
   disks have historically required a paid instance, and free instances sleep and have ephemeral storage
   (data would be lost on redeploy). SQLite also limits you to a single instance.
5. Open the Render shell once: `flask --app wsgi create-admin`.

**Production alternative:** managed PostgreSQL (`DATABASE_URL`, add `psycopg2-binary`) + object storage (S3/Cloudflare R2)
for uploads — change `upload_service.py` to write to the bucket and `public.media` to redirect to signed URLs.

## Security notes
Werkzeug password hashing · CSRF on all forms · ORM only (no string SQL) · Jinja auto-escaping · server-side role and
ownership checks · images validated by Pillow, re-encoded (strips EXIF/GPS), random filenames · private media behind auth ·
safe `?next=` redirects · generic login errors · secure cookies in production · no stack traces to users · audit logs.
Known gaps: in-memory rate limiter, no CSP header, no email verification / password reset.

## Troubleshooting
* `ModuleNotFoundError` → activate the venv and `pip install -r requirements.txt`.
* `no such table` → run `flask --app run init-db`.
* `RuntimeError: SECRET_KEY must be set` → set `SECRET_KEY` when `FLASK_ENV=production`.
* Maps blank → the Leaflet/OSM CDNs are blocked; use the manual latitude/longitude fields.
* Address search fails → Nominatim is rate-limited; click the map instead.
* Uploads vanish on Render → no persistent disk; set `DATA_DIR` to the disk mount.
* Pinned versions in `requirements.txt` were chosen from memory — if pip complains, loosen them to `>=`.
