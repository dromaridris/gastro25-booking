"""
Standalone holiday-sync script for PythonAnywhere's Scheduled Tasks feature.

Uses the Calendarific API (https://calendarific.com) to fetch Pakistan's
public holidays. Does NOT need the Flask app to be running — it connects
to the same SQLite database file directly.

Set this up on PythonAnywhere (Tasks tab → Add a new scheduled task):

  Recommended schedule: WEEKLY (e.g. every Monday at 03:00) rather than daily —
  holidays don't change often, and this keeps you well within Calendarific's
  free-tier request budget (each run only makes 1-2 API calls, one per year
  covered by the sync window).

  Recommended — pass the key inline so it doesn't depend on how PythonAnywhere
  propagates environment variables to scheduled tasks:

    CALENDARIFIC_API_KEY=your_key_here /home/YOURUSERNAME/.virtualenvs/gastro-venv/bin/python3 /home/YOURUSERNAME/gastro_booking/sync_holidays_task.py

  Alternative — pass the key as a plain command-line argument instead:

    /home/YOURUSERNAME/.virtualenvs/gastro-venv/bin/python3 /home/YOURUSERNAME/gastro_booking/sync_holidays_task.py your_key_here

You can also just run it manually any time:
    python3 sync_holidays_task.py your_key_here
"""

import os
import sys
import sqlite3
from datetime import datetime, date, timedelta

import requests

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'gastro_booking.db')
COUNTRY = 'PK'


def get_api_key():
    try:
        from config import CALENDARIFIC_API_KEY
        key = CALENDARIFIC_API_KEY
    except ImportError:
        key = os.environ.get('CALENDARIFIC_API_KEY', '')

    if not key and len(sys.argv) > 1:
        key = sys.argv[1]

    return key


def fetch_holidays(api_key, years, timeout=15):
    events = []
    for year in years:
        resp = requests.get(
            'https://calendarific.com/api/v2/holidays',
            params={'api_key': api_key, 'country': COUNTRY, 'year': year},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        meta = data.get('meta', {})
        if meta.get('code') != 200:
            raise RuntimeError(f"Calendarific error: {meta.get('error_detail', 'unknown error')}")

        for h in data.get('response', {}).get('holidays', []):
            types = [t.lower() for t in h.get('type', [])]
            if not any('national' in t or 'public' in t for t in types):
                continue
            iso = h.get('date', {}).get('iso', '')
            try:
                d = datetime.strptime(iso[:10], '%Y-%m-%d').date()
            except ValueError:
                continue
            name = h.get('name', '').strip()
            if name:
                events.append((d, name))
    return events


def main():
    api_key = get_api_key()
    if not api_key:
        print('No API key found. Set CALENDARIFIC_API_KEY env var or pass it as an argument.')
        return

    if not os.path.exists(DB_PATH):
        print(f'Database not found at {DB_PATH} — has the Flask app run at least once?')
        return

    today = date.today()
    window_start = today - timedelta(days=30)
    window_end = today + timedelta(days=730)
    years = sorted({window_start.year, window_end.year})

    events = fetch_holidays(api_key, years)
    print(f'Fetched {len(events)} national/public holidays for {years}.')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('''
        CREATE TABLE IF NOT EXISTS holiday (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holiday_date TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT NOT NULL
        );
    ''')

    count = 0
    for d, name in events:
        if window_start <= d <= window_end:
            conn.execute(
                'INSERT INTO holiday (holiday_date, name, source, created_at) VALUES (?,?,?,?) '
                "ON CONFLICT(holiday_date) DO UPDATE SET name=excluded.name, source='auto_sync' "
                "WHERE holiday.source = 'auto_sync'",
                (d.isoformat(), name, 'auto_sync', datetime.utcnow().isoformat())
            )
            count += 1
    conn.commit()
    conn.close()
    print(f'Synced {count} holidays into the database ({window_start} to {window_end}).')


if __name__ == '__main__':
    main()
