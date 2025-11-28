from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class AppointmentType(Base):
    __tablename__ = "appointment_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)

    bookings = relationship("Booking", back_populates="appointment_type")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(String, unique=True, index=True)
    date = Column(DateTime, nullable=False)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)

    patient_name = Column(String, nullable=False)
    patient_email = Column(String, nullable=False)

    appointment_type_id = Column(Integer, ForeignKey("appointment_types.id"))
    appointment_type = relationship("AppointmentType", back_populates="bookings")
