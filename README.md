# Personal Subscription Tracker

Python (backend logic) + Streamlit (web UI) + MySQL (database).

## Features
- Add, edit, delete subscriptions (weekly / monthly / quarterly / yearly)
- Monthly and yearly spend totals, spend by category chart
- Upcoming renewals in the next 30 days (calculated automatically)
- Usage log, plus a "cancel candidates" list with cost-per-use and potential savings

## Setup
1. Install Python 3.9+ and MySQL 8 (make sure the MySQL server is running).
2. In this folder:
   ```
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and put in your MySQL user and password.
4. Run:
   ```
   streamlit run app.py
   ```
   The database and tables are created automatically on first start.

## Files
- `app.py`: Streamlit pages and business logic (renewal dates, cost normalisation)
- `db.py`: all MySQL access
- `schema.sql`: tables (categories, subscriptions, usage_log)
