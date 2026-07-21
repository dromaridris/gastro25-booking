# Deploying to PythonAnywhere

## 1. Upload the files
1. Log in to https://www.pythonanywhere.com
2. Go to the **Files** tab and create a folder, e.g. `gastro_booking`.
3. Upload every file in this project **preserving the folder structure**:
   ```
   gastro_booking/
     app.py
     requirements.txt
     templates/   (all .html files)
     static/
       css/style.css
       js/app.js
       logos/jpmc_gastro_logo.jpeg
       logos/jpmc_logo1.png
   ```
   Easiest way: zip this whole folder locally, upload the zip via the Files tab,
   then in a **Bash console** run `unzip gastro_booking.zip`.

## 2. Create a virtualenv and install dependencies
The app only depends on Flask/Werkzeug (data is stored with Python's built-in
`sqlite3` module, no ORM needed — nothing else to install).
Open a **Bash console** on PythonAnywhere and run:
```bash
cd gastro_booking
mkvirtualenv --python=/usr/bin/python3.10 gastro-venv
pip install -r requirements.txt
```
(If `mkvirtualenv` isn't available, use: `python3.10 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`)

## 3. Create the Web App
1. Go to the **Web** tab → **Add a new web app**.
2. Choose **Manual configuration** (not "Flask" auto-wizard) → pick Python 3.10.
3. Set **Source code** to `/home/YOURUSERNAME/gastro_booking`.
4. Set **Virtualenv** to `/home/YOURUSERNAME/.virtualenvs/gastro-venv`
   (or the path to the venv you created in step 2).

## 4. Edit the WSGI file
Click the WSGI configuration file link on the Web tab and replace its contents with:
```python
import sys
path = '/home/YOURUSERNAME/gastro_booking'
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application
```

## 5. Set a real SECRET_KEY (recommended)
On the **Web** tab, under "Environment variables", add:
```
SECRET_KEY = <a long random string>
```

## 6. Reload
Click the green **Reload** button on the Web tab. Your app is now live at
`https://YOURUSERNAME.pythonanywhere.com`.

## 7. First login
A default admin account is created automatically on first run:
- **Username:** `admin`
- **Password:** `admin123`

**Log in immediately and change this password** (or create a new admin account
and delete the default one) — the app doesn't yet expose a "change password"
screen, so if you want a different admin password, either:
- edit `bootstrap_db()` in `app.py` before first launch, or
- delete `gastro_booking.db` (resets ALL data) and set a new password there, or
- ask for a "change password" feature to be added.

## 8. Data persistence
The SQLite file `gastro_booking.db` is created automatically next to `app.py`
on first run and persists across reloads — this is your permanent database.
**Back it up regularly** (Files tab → download `gastro_booking.db`) since
PythonAnywhere free-tier disks are still just a regular filesystem, not
automatically backed up.

## Notes
- Tailwind isn't used — the UI ships with its own lightweight stylesheet
  (`static/css/style.css`), so there's no CDN/build step needed.
- All business rules (global caps, scheduler quota, Saturday-only ERCP,
  bleeding flag, nurse-manager special cases, admin/specialist override)
  are enforced server-side in `validate_booking()` inside `app.py` — the
  frontend only hides irrelevant options for convenience, it is not the
  security boundary.
