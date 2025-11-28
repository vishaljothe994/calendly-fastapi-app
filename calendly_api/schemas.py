from pydantic import BaseModel
from datetime import datetime
from typing import List


class TimeSlot(BaseModel):
    start: str
    end: str


class AvailabilityResponse(BaseModel):
    date: str
    appointment_type: str
    available_slots: List[TimeSlot]


class BookingRequest(BaseModel):
    appointment_type_id: int
    date: datetime
    start_time: str
    patient_name: str
    patient_email: str


class BookingResponse(BaseModel):
    message: str
    booking_id: str
    date: str
    start_time: str
    end_time: str
    appointment_type: str


class AppointmentTypeResponse(BaseModel):
    id: int
    name: str
    duration_minutes: int


class AppointmentTypeCreate(BaseModel):
    name: str
    duration_minutes: int


class BookingDetailsResponse(BaseModel):
    booking_id: str
    date: str
    start_time: str
    end_time: str
    patient_name: str
    patient_email: str
    appointment_type_id: int
    appointment_type: str
