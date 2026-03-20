from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI(title="Medical Appointment System", description="Manage doctors, patients, and appointments")

# -----------------------------
# Data Models
# -----------------------------
class Doctor(BaseModel):
    id: int
    name: str = Field(..., min_length=2)
    specialization: str = Field(..., min_length=2)
    fee: float = Field(..., gt=0)
    experience: Optional[int] = Field(default=1, ge=1)  # extended field
    available: bool = True

class Patient(BaseModel):
    id: int
    name: str = Field(..., min_length=2)
    active: bool = True

class Appointment(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    status: str = "booked"  # booked, confirmed, completed

# -----------------------------
# In-Memory Data
# -----------------------------
doctors: List[Doctor] = []
patients: List[Patient] = []
appointments: List[Appointment] = []

# -----------------------------
# Day 1 — GET Endpoints
# -----------------------------
@app.get("/home")
def home():
    return {"message": "Welcome to Medical Appointment System"}

@app.get("/doctors")
def get_doctors():
    return doctors

@app.get("/doctors/{id}")
def get_doctor(id: int):
    doctor = next((d for d in doctors if d.id == id), None)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

@app.get("/appointments/count")
def count_appointments():
    return {"count": len(appointments)}

@app.get("/patients")
def get_patients():
    return patients

# -----------------------------
# Day 2 — POST + Pydantic
# -----------------------------
@app.post("/doctors", status_code=201)
def add_doctor(doctor: Doctor):
    if any(d.id == doctor.id for d in doctors):
        raise HTTPException(status_code=400, detail="Duplicate doctor ID")
    doctors.append(doctor)
    return doctor

@app.post("/patients", status_code=201)
def add_patient(patient: Patient):
    if any(p.id == patient.id for p in patients):
        raise HTTPException(status_code=400, detail="Duplicate patient ID")
    patients.append(patient)
    return patient

# -----------------------------
# Day 3 — Helpers + Filter
# -----------------------------
def find_doctor(doctor_id: int):
    return next((d for d in doctors if d.id == doctor_id), None)

@app.get("/doctors/filter")
def filter_doctors(specialization: Optional[str] = None, max_fee: Optional[float] = None):
    result = doctors
    if specialization is not None:
        result = [d for d in result if d.specialization.lower() == specialization.lower()]
    if max_fee is not None:
        result = [d for d in result if d.fee <= max_fee]
    return result

# -----------------------------
# Day 4 — CRUD
# -----------------------------
@app.put("/doctors/{id}")
def update_doctor(id: int, doctor: Doctor):
    existing = find_doctor(id)
    if not existing:
        raise HTTPException(status_code=404, detail="Doctor not found")
    existing.name = doctor.name or existing.name
    existing.specialization = doctor.specialization or existing.specialization
    existing.fee = doctor.fee or existing.fee
    existing.experience = doctor.experience or existing.experience
    existing.available = doctor.available
    return existing

@app.delete("/doctors/{id}")
def delete_doctor(id: int):
    existing = find_doctor(id)
    if not existing:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if any(a.doctor_id == id and a.status != "completed" for a in appointments):
        raise HTTPException(status_code=400, detail="Cannot delete doctor with active appointments")
    doctors.remove(existing)
    return {"message": "Doctor deleted"}

@app.put("/patients/{id}")
def update_patient(id: int, patient: Patient):
    existing = next((p for p in patients if p.id == id), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Patient not found")
    existing.name = patient.name or existing.name
    existing.active = patient.active
    return existing

@app.delete("/patients/{id}")
def delete_patient(id: int):
    existing = next((p for p in patients if p.id == id), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Patient not found")
    if any(a.patient_id == id and a.status != "completed" for a in appointments):
        raise HTTPException(status_code=400, detail="Cannot delete patient with active appointments")
    patients.remove(existing)
    return {"message": "Patient deleted"}

# -----------------------------
# Day 5 — Workflow (Book → Confirm → Consult)
# -----------------------------
@app.post("/appointments/book", status_code=201)
def book_appointment(appointment: Appointment):
    doctor = find_doctor(appointment.doctor_id)
    if not doctor or not doctor.available:
        raise HTTPException(status_code=400, detail="Doctor not available")
    if any(a.id == appointment.id for a in appointments):
        raise HTTPException(status_code=400, detail="Duplicate appointment ID")
    appointments.append(appointment)
    return {"message": "Appointment booked", "appointment": appointment}

@app.post("/appointments/confirm/{id}")
def confirm_appointment(id: int):
    appt = next((a for a in appointments if a.id == id), None)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = "confirmed"
    return {"message": "Appointment confirmed", "appointment": appt}

@app.post("/appointments/consult/{id}")
def complete_consultation(id: int):
    appt = next((a for a in appointments if a.id == id), None)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = "completed"
    return {"message": "Consultation completed", "appointment": appt}

# -----------------------------
# Day 6 — Search, Sort, Pagination
# -----------------------------
@app.get("/doctors/search")
def search_doctors(keyword: str):
    result = [d for d in doctors if keyword.lower() in d.name.lower() or keyword.lower() in d.specialization.lower()]
    if not result:
        return {"message": "No doctors found"}
    return result

@app.get("/doctors/sort")
def sort_doctors(sort_by: str = "name", order: str = "asc"):
    if sort_by not in ["name", "specialization", "fee", "experience"]:
        raise HTTPException(status_code=400, detail="Invalid sort field")
    result = sorted(doctors, key=lambda x: getattr(x, sort_by), reverse=(order == "desc"))
    return result

@app.get("/appointments/paginate")
def paginate_appointments(page: int = 1, limit: int = 5):
    start = (page - 1) * limit
    end = start + limit
    total_pages = (len(appointments) + limit - 1) // limit
    return {"page": page, "total_pages": total_pages, "data": appointments[start:end]}

@app.get("/browse")
def browse_doctors(
    keyword: Optional[str] = None,
    sort_by: Optional[str] = "name",
    order: Optional[str] = "asc",
    page: int = 1,
    limit: int = 5
):
    result = doctors
    if keyword:
        result = [d for d in result if keyword.lower() in d.name.lower() or keyword.lower() in d.specialization.lower()]
    if sort_by in ["name", "specialization", "fee", "experience"]:
        result = sorted(result, key=lambda x: getattr(x, sort_by), reverse=(order == "desc"))
    start = (page - 1) * limit
    end = start + limit
    total_pages = (len(result) + limit - 1) // limit
    return {"page": page, "total_pages": total_pages, "data": result[start:end]}