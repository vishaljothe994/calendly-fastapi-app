from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Booking, AppointmentType

WORK_START = 9
WORK_END = 17


def generate_slots(db: Session, date: datetime, appointment_type: AppointmentType):

    duration = appointment_type.duration_minutes
    slots = []

    day_start = datetime(date.year, date.month, date.day, WORK_START, 0)
    day_end = datetime(date.year, date.month, date.day, WORK_END, 0)

    current = day_start

    # fetch booked slots for the day using start timestamps (covers same-day bookings)
    booked = db.query(Booking).filter(
        Booking.start >= day_start,
        Booking.start < day_end
    ).all()

    def is_conflict(slot_start, slot_end):
        for b in booked:
            if not (slot_end <= b.start or slot_start >= b.end):
                return True
        return False

    while current + timedelta(minutes=duration) <= day_end:
        slot_start = current
        slot_end = current + timedelta(minutes=duration)

        if not is_conflict(slot_start, slot_end):
            slots.append({
                "start": slot_start.strftime("%H:%M"),
                "end": slot_end.strftime("%H:%M")
            })

        current += timedelta(minutes=duration)

    return slots


def create_booking(db: Session, date, start_time, appointment_type: AppointmentType, req):

    # Accept start_time as either a simple time string like "HH:MM" or
    # a full ISO datetime string (e.g. "2025-11-29T17:41:12.261Z"). If a
    # datetime is passed in, use its time fields.
    if isinstance(start_time, datetime):
        st = start_time
    else:
        if not isinstance(start_time, str):
            raise ValueError("start_time must be a string or datetime")

        # First try plain HH:MM
        try:
            st = datetime.strptime(start_time, "%H:%M")
        except Exception:
            # Try ISO formats. Allow trailing Z for UTC by replacing with +00:00
            iso = start_time
            if iso.endswith("Z"):
                iso = iso[:-1] + "+00:00"
            try:
                st = datetime.fromisoformat(iso)
            except Exception:
                # Last resort: try a common ISO format without offset
                try:
                    st = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%f")
                except Exception:
                    raise ValueError("start_time format not recognised")

    # Build booking start using the provided date but time from the parsed start
    start_full = datetime(date.year, date.month, date.day, st.hour, st.minute, st.second)

    # Prevent booking in the past. If start_full is earlier than now, raise
    # an error so the API can return an appropriate 400 response.
    if start_full < datetime.now():
        raise ValueError("Cannot book appointments in the past")
    end_full = start_full + timedelta(minutes=appointment_type.duration_minutes)

    # use a higher-resolution timestamp to avoid collisions when multiple
    # bookings are created within the same second (helps tests & concurrent calls)
    booking_id = f"BK-{int(datetime.now().timestamp() * 1_000_000)}"

    # before persisting, check for conflicts (overlaps) with existing bookings
    conflict = db.query(Booking).filter(
        Booking.start < end_full,
        Booking.end > start_full
    ).first()

    if conflict:
        # raise a simple exception which the endpoint will convert into a 400 response
        raise ValueError("Slot not available")

    booking = Booking(
        booking_id=booking_id,
        date=date,
        start=start_full,
        end=end_full,
        patient_name=req.patient_name,
        patient_email=req.patient_email,
        appointment_type_id=appointment_type.id
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return booking
