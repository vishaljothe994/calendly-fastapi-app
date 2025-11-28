# Calendly-style Booking API (SQLite)

Project: a small FastAPI service that implements availability and booking endpoints backed by SQLite. It supports appointment types, slot generation, booking creation and listing booked slots.

---

## Features
- Create and list appointment types (duration is used to build time slots)
- Get daily availability (returns only free slots)
- Create bookings (accepts `HH:MM` or ISO datetime for start time)
- List booked slots with user details
  
Built with: Python, FastAPI, SQLAlchemy, SQLite, Uvicorn

---

## Local setup

Prerequisites: Python 3.11+, git

1) Create and activate a virtual environment (PowerShell):

```powershell
python -m venv venv
# Activate
.\venv\Scripts\Activate.ps1
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Initialize the database (SQLite file will be created by the app automatically):

The app automatically creates tables on startup with metadata.create_all(), but you can also seed the DB from a small script or the interactive shell if you want.

4) Run the server

```powershell
D:/supersourcing/Appointment_booking/venv/Scripts/python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open the interactive API docs: http://127.0.0.1:8000/docs (Swagger UI) or /redoc

---

## Database
- Uses a local SQLite file `calendly.db` (configured in `database.py`).
- In-memory DB is used by the tests.

Note: for heavy concurrency or production use, switch to Postgres / MySQL.

---

## API: Request / Response examples (summary)

1) GET availability

- Path: `/api/calendly/availability`
- Query params: `date=YYYY-MM-DD` and `appointment_type_id=<id>`

Example request:
```
GET /api/calendly/availability?date=2025-12-01&appointment_type_id=1
```

Success response (200):
```json
{
  "date": "2025-12-01",
  "appointment_type": "Initial Consultation",
  "available_slots": [
    {"start":"09:00","end":"09:30"},
    {"start":"09:30","end":"10:00"}
  ]
}
```

If appointment type not found the API currently returns 404:
```json
{ "detail": "Appointment type not found" }
```

2) POST create booking

- Path: `/api/calendly/book`
- Body (JSON):

```json
{
  "appointment_type_id": 1,
  "date": "2025-12-01",
  "start_time": "14:00",           // or ISO datetimes like 2025-12-01T14:00:00Z
  "patient_name": "Alice",
  "patient_email": "alice@example.com"
}
```

Success response (200):
```json
{
  "message": "Booking confirmed",
  "booking_id": "BK-<timestamp>",
  "date": "2025-12-01",
  "start_time": "14:00",
  "end_time": "14:30",
  "appointment_type": "Initial Consultation"
}
```

Errors:
- 400: { "detail": "Slot not available" }
- 400: { "detail": "Cannot book appointments in the past" }
- 404: { "detail": "Appointment type not found" }

3) Appointment types

- GET `/api/calendly/appointment-types` — list types
- POST `/api/calendly/appointment-types` — create type

POST example body:
```json
{ "name": "General Consultation", "duration_minutes": 30 }
```

4) Bookings list

- GET `/api/calendly/bookings` — list all bookings
- Optional filters: `date=YYYY-MM-DD` and `appointment_type_id` to limit results

Success response example (list item):
```json
{
  "booking_id": "BK-123456",
  "date": "2025-12-10",
  "start_time": "09:00",
  "end_time": "09:30",
  "patient_name": "Alice",
  "patient_email": "alice@example.com",
  "appointment_type_id": 1,
  "appointment_type": "General Consultation"
}
```

When no bookings found for the query the endpoint returns:
```json
{ "message": "no slots booked" }
```

---
