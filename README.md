# Al Huda Madrasa Attendance System

## Included
- 277 students imported from `1HAJAR.xlsx`
- Parent view-only attendance page
- Class-specific Usthad PIN login
- Master Admin PIN
- Daily attendance: Present / Absent / Leave
- SQLite database
- Class reports

## Run locally
1. Install Python 3.10+.
2. `pip install -r requirements.txt`
3. `python app.py`
4. Open `http://localhost:5000`

## Security before public deployment
Set environment variables:
- `SECRET_KEY`
- `MASTER_PIN`
- `CLASS_1_PIN` ... `CLASS_12_PIN`

Do not use the demo PINs in production. Put the site behind HTTPS and use a production WSGI server.
