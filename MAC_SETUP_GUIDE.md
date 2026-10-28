# CivicConnect — Complete Beginner Guide for a New MacBook

Follow every step in order. Lines inside grey boxes (```) are **commands**: type or paste them into the **Terminal** app and press **Enter**. Do not type the `$` sign if you see one.

> Honest note: this project was written without being run on a real machine. If something fails, copy the **full error text** from Terminal and send it to Claude — it can be fixed quickly.

---

## PART 1 — Install the tools (one time only)

### Step 1: Open Terminal
1. Press **Command (⌘) + Space** to open Spotlight.
2. Type **Terminal** and press **Enter**.
3. A window with a text prompt opens. This is where you type commands.

### Step 2: Install Apple Command Line Tools (gives you Git)
```
xcode-select --install
```
A pop-up appears → click **Install** → accept the license → wait (5–15 minutes). If it says "already installed", that's fine.

### Step 3: Install Homebrew (the Mac "app installer" for developers)
Paste this whole line:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
- It asks for your **Mac password**. Typing shows nothing — that is normal. Press Enter.
- Press **Enter** again when it asks to continue.
- When it finishes, it prints **"Next steps"** with 2–3 commands (they start with `echo` and `eval`). **Copy and run exactly those commands.** For Apple Silicon Macs (M1/M2/M3/M4) they look like:
```
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```
Check it worked:
```
brew --version
```
You should see a version number.

### Step 4: Install Python 3.12
```
brew install python@3.12
```
Check:
```
python3.12 --version
```
Expected: `Python 3.12.x`. (We use 3.12 on purpose — the newest Python can break some packages.)

### Step 5: Install Git
```
brew install git
git --version
```

### Step 6: Install Visual Studio Code (code editor)
```
brew install --cask visual-studio-code
```
Open it from Launchpad later. (Optional but recommended. Inside VS Code, install the extension **Python** from the Extensions icon on the left.)

### Step 7: Get the project
1. Download **civicconnect.zip** from Claude and save it (usually to **Downloads**).
2. Double-click it to unzip. You get a folder named **civicconnect**.
3. Move that folder to your **Documents** folder.

---

## PART 2 — Set up the project

### Step 8: Go into the project folder
```
cd ~/Documents/civicconnect
ls
```
You should see files such as `run.py`, `config.py`, `requirements.txt`, `app`, `tests`.
If you see "No such file or directory", the folder is somewhere else or nested (e.g. `civicconnect/civicconnect`). Fix the path, or type `cd ` (with a space) and **drag the folder into Terminal**, then press Enter.

### Step 9: Create a virtual environment (a private box for this project's packages)
```
python3.12 -m venv venv
```

### Step 10: Activate it
```
source venv/bin/activate
```
Your prompt now starts with **(venv)**. **Every time you open a new Terminal window you must run Step 8 and Step 10 again.**

### Step 11: Install the project's packages
```
pip install --upgrade pip
pip install -r requirements.txt
```
Wait until it ends without red errors. If one version is "not found", open `requirements.txt` in VS Code, replace `==` with `>=` on that line, save, and run again.

### Step 12: Create your settings file
```
cp .env.example .env
```
Generate a secret key:
```
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the long text it prints. Open the file `.env` (in VS Code: **File → Open Folder → civicconnect**, then click `.env`; it may be hidden — press **Command + Shift + .** in Finder to show hidden files). Change this line:
```
SECRET_KEY=change-me-to-a-long-random-string
```
to
```
SECRET_KEY=PASTE_YOUR_LONG_TEXT_HERE
```
Save (⌘ + S). Never share or upload `.env`.

### Step 13: Create the database
```
flask --app run init-db
```
Expected: `Database ready.` This creates the database file in the `instance` folder plus default departments (Roads, Sanitation, Water…) and categories (Pothole, Garbage…).

### Step 14: Create your administrator account
```
flask --app run create-admin
```
It asks for **Email**, **Full name**, **Password** (typing is hidden), and password again.
Password rule: at least 8 characters with letters AND numbers. Remember these — you log in with them.

### Step 15 (optional): Add demo data
Fills the app with sample complaints so dashboards look alive:
```
flask --app run seed
```
Demo logins (password for all: `Demo@12345`):
- Admin: `admin@demo.civicconnect.local`
- Officers: `officer1@demo.civicconnect.local` … `officer5@demo.civicconnect.local`
- Citizen: `citizen@demo.civicconnect.local`

---

## PART 3 — Run the website

### Step 16: Start the server
```
flask --app run run --debug --port 5001
```
Why 5001? On new Macs, port 5000 is used by "AirPlay Receiver", which causes errors. 5001 avoids that.

You will see text like `Running on http://127.0.0.1:5001`. **Leave this Terminal window open** — closing it stops the website.

### Step 17: Open it in your browser
Go to: **http://127.0.0.1:5001**

### Step 18: Stop the server
In Terminal press **Control + C**.

### Next time you want to run the project
```
cd ~/Documents/civicconnect
source venv/bin/activate
flask --app run run --debug --port 5001
```

---

## PART 4 — Try every role (a quick tour)

1. **Citizen:** click **Sign up**, create an account, log in, click **Report an Issue**. Fill title (5+ chars), category, description (20+ chars), address. Click the map to drop a pin (or type latitude/longitude, e.g. 28.6139 and 77.2090). Add an optional photo (JPG/PNG/WebP, max 5 MB). Submit and note your reference number (CC-2026-XXXXXX).
2. **Admin:** log out, log in with your admin account.
   - Go to **Users → Add user / officer**: create an officer with role **authority** and pick a **department** (the officer sees only that department's complaints).
   - Open **Complaints** → click your complaint → **Assign** it to that department and officer.
3. **Officer:** log out, log in as the officer → **Complaints** → open it → **Accept & start work** → later **Record resolution** with a description and proof photo.
4. **Admin again:** open the complaint → **Verify resolution**. Check **Reports** and **Audit log**.
5. **Citizen again:** open the complaint → see the timeline and resolution → give a 1–5 star **feedback**.

---

## PART 5 — Run the automatic tests
Stop the server first (Control + C) or open a second Terminal tab (⌘ + T, then repeat Steps 8 and 10):
```
pytest -v
```
Green "passed" = good. Red "FAILED" = copy the output and send it to Claude. Tests use a temporary database and never touch your real data.

---

## PART 6 — (Optional) Put it on GitHub
1. Create a free account at https://github.com and make a **new empty repository** called `civicconnect` (do not add a README).
2. In Terminal (inside the project folder):
```
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/civicconnect.git
git push -u origin main
```
(Git may ask you to sign in; GitHub requires a **Personal Access Token** instead of a password: GitHub → Settings → Developer settings → Tokens.)
The `.gitignore` already keeps `.env`, the database and uploads out of GitHub.

## PART 7 — (Optional) Put it online with Render
See the **Deployment** section in `README.md`. Short version: create a Render account → New → Blueprint → choose your GitHub repo → set `SECRET_KEY` → attach a persistent disk at `/var/data` (check Render's current pricing; free plans lose data on redeploy) → open the Render Shell and run `flask --app wsgi create-admin`.

---

## Troubleshooting (common beginner problems)

| Problem | Fix |
|---|---|
| `command not found: brew` | Redo the "Next steps" commands from Step 3, then close and reopen Terminal. |
| `command not found: python3.12` | Run `brew install python@3.12` again, reopen Terminal. |
| `command not found: flask` | You forgot Step 10. Run `source venv/bin/activate`. |
| `ModuleNotFoundError` | Activate venv (Step 10), then `pip install -r requirements.txt`. |
| `no such table` | Run `flask --app run init-db`. |
| `Address already in use` | Use another port: `--port 5002`. Or stop the old server with Control + C. |
| Page shows 403 | You are logged in with the wrong role for that page. Log out and use the right account. |
| Map is gray/blank | Check your internet; you can still type latitude and longitude manually. |
| "Address not found" | The free search service is limited; click the map instead. |
| Want to start fresh | Stop server, delete `instance/civicconnect.db`, then redo Steps 13–15. |

## Useful words
- **Terminal:** the app where you type commands.
- **Virtual environment (venv):** a private folder of packages for one project.
- **Flask:** the Python framework that runs the website.
- **Database:** where users and complaints are stored (a file called `civicconnect.db`).
