from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database import Base, engine, SessionLocal
from sqlalchemy.exc import InvalidRequestError as SAInvalidRequestError
from models import AppointmentType, Booking
from schemas import BookingRequest, BookingResponse, AvailabilityResponse, AppointmentTypeResponse, AppointmentTypeCreate, BookingDetailsResponse
from typing import Optional, Union
from scheduler import generate_slots, create_booking

app = FastAPI(title="Calendly API with SQLite")

# Create tables
Base.metadata.create_all(bind=engine)


# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/calendly/availability", response_model=AvailabilityResponse)
def availability(date: str, appointment_type_id: int, db: Session = Depends(get_db)):

    # Accept either raw YYYY-MM-DD or a quoted string (clients sometimes send %22...%22)
    raw = date.strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        raw = raw[1:-1]

    # Try multiple common formats
    try:
        parsed_date = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        # allow full ISO datetimes (take the date portion)
        try:
            parsed_date = datetime.fromisoformat(raw).date()
            # fromisoformat returns date when string contains only date; ensure datetime
            if isinstance(parsed_date, type(datetime.now().date())):
                # convert to datetime for downstream usage
                parsed_date = datetime(parsed_date.year, parsed_date.month, parsed_date.day)
        except Exception:
            # final attempt — try to parse date portion
            raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD or ISO format")

    appt_type = db.query(AppointmentType).filter(AppointmentType.id == appointment_type_id).first()

    if not appt_type:
        raise HTTPException(status_code=404, detail="Appointment type not found")

    slots = generate_slots(db, parsed_date, appt_type)

    return AvailabilityResponse(
        date=date,
        appointment_type=appt_type.name,
        available_slots=slots
    )


@app.post("/api/calendly/book", response_model=BookingResponse)
def book(req: BookingRequest, db: Session = Depends(get_db)):

    print("db", db)

    appt_type = db.query(AppointmentType).filter(
        AppointmentType.id == req.appointment_type_id
    ).first()

    print("appt_type", appt_type)

    if not appt_type:
        raise HTTPException(status_code=404, detail="Appointment type not found")

    try:
        booking = create_booking(db, req.date, req.start_time, appt_type, req)
    except ValueError as exc:
        # A ValueError from create_booking is used to indicate an unavailable slot
        raise HTTPException(status_code=400, detail=str(exc))

    return BookingResponse(
        message="Booking confirmed",
        booking_id=booking.booking_id,
        date=booking.date.strftime("%Y-%m-%d"),
        start_time=booking.start.strftime("%H:%M"),
        end_time=booking.end.strftime("%H:%M"),
        appointment_type=appt_type.name
    )


@app.get("/api/calendly/appointment-types", response_model=List[AppointmentTypeResponse])
def list_appointment_types(db: Session = Depends(get_db)):
    """Return all appointment types in the database."""
    appt_types = db.query(AppointmentType).all()

    # Convert SQLAlchemy models to pydantic response models
    return [
        AppointmentTypeResponse(
            id=a.id,
            name=a.name,
            duration_minutes=a.duration_minutes,
        )
        for a in appt_types
    ]


@app.get("/api/calendly/bookings", response_model=Union[List[BookingDetailsResponse], dict])
def list_bookings(date: Optional[str] = None, appointment_type_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Return bookings. Optional filters: date (YYYY-MM-DD or ISO) and appointment_type_id."""

    query = db.query(Booking)

    if date:
        raw = date.strip()
        if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
            raw = raw[1:-1]

        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            try:
                parsed = datetime.fromisoformat(raw)
            except Exception:
                raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD or ISO format")

        day_start = datetime(parsed.year, parsed.month, parsed.day, 0, 0)
        day_end = day_start.replace(hour=23, minute=59, second=59)
        query = query.filter(Booking.start >= day_start, Booking.start <= day_end)

    if appointment_type_id:
        query = query.filter(Booking.appointment_type_id == appointment_type_id)

    bookings = query.all()

    if not bookings:
        return {"message": "no slots booked"}

    result = []
    for b in bookings:
        appt_name = None
        try:
            appt_name = b.appointment_type.name if b.appointment_type else None
        except Exception:
            appt_name = None

        result.append(BookingDetailsResponse(
            booking_id=b.booking_id,
            date=b.date.strftime("%Y-%m-%d") if b.date else None,
            start_time=b.start.strftime("%H:%M") if b.start else None,
            end_time=b.end.strftime("%H:%M") if b.end else None,
            patient_name=b.patient_name,
            patient_email=b.patient_email,
            appointment_type_id=b.appointment_type_id,
            appointment_type=appt_name
        ))

    return result


@app.post("/api/calendly/appointment-types", response_model=AppointmentTypeResponse)
def create_appointment_type(payload: AppointmentTypeCreate, db: Session = Depends(get_db)):
    """Create a new appointment type. Name must be unique."""

    existing = db.query(AppointmentType).filter(AppointmentType.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Appointment type with that name already exists")

    new = AppointmentType(name=payload.name, duration_minutes=payload.duration_minutes)
    db.add(new)

    # Persist the new appointment type in a single commit. The project no longer
    # requires transient-retry handling for sqlite locks because database
    # configuration has been stabilized externally.
    try:
        db.commit()
    except Exception as exc:
        # If something unexpected happens raise an HTTP 500 to the client.
        raise HTTPException(status_code=500, detail="Failed to create appointment type")

    # Refresh the instance so we have the final database-assigned id. If a
    # refresh fails for any reason, fall back to querying the persisted record.
    try:
        db.refresh(new)
    except SAInvalidRequestError:
        persisted = db.query(AppointmentType).filter(AppointmentType.name == new.name).first()
        if persisted:
            new = persisted
        else:
            raise HTTPException(status_code=500, detail="Failed to persist appointment type")

    return AppointmentTypeResponse(id=new.id, name=new.name, duration_minutes=new.duration_minutes)
