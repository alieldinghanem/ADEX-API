"""
FastAPI Application - Main API Server
ADEX Smart Academic Scheduling System
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import requests
import os
import json
from uuid import uuid4
from datetime import datetime, timezone

from app.config import settings
from app.models import (
    SchedulingInput,
    TimetableOutput,
    Instructor,
    Course,
    Room,
)
from app.scheduler import Scheduler

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)


@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "ADEX - Smart Academic Scheduling System",
        "version": settings.API_VERSION,
        "endpoints": {
            "health": "/health",
            "config": "/config",
            "docs": "/docs",
            "generate": "/api/generate-schedule",
            "generateFromNub": "/api/generate-schedule/from-nub",
            "generateFromNubExport": "/api/generate-schedule/from-nub/export",
            "exports": "/api/exports/{file_name}"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ADEX Scheduling API",
        "version": settings.API_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/config")
async def get_configuration():
    return {
        "scheduling": {
            "days": settings.DAYS_OF_WEEK,
            "regularTimeSlots": settings.REGULAR_TIME_SLOTS,
            "onlineTimeSlots": settings.ONLINE_TIME_SLOTS,
            "totalTimeSlots": settings.TIME_SLOTS
        },
        "groups": {
            "targetGroupSize": settings.TARGET_GROUP_SIZE,
            "sectionCapacity": settings.SECTION_CAPACITY,
            "minSections": settings.MIN_SECTIONS_PER_GROUP,
            "maxSections": settings.MAX_SECTIONS_PER_GROUP
        },
        "integration": {
            "nubBaseUrl": getattr(settings, "NUB_BASE_URL", "http://nub-adex.runasp.net"),
            "nubInstructorsPath": getattr(settings, "NUB_INSTRUCTORS_PATH", "/api/Instructors/all-with-availability"),
            "nubCoursesPath": getattr(settings, "NUB_COURSES_PATH", ""),
            "nubRoomsPath": getattr(settings, "NUB_ROOMS_PATH", ""),
            "nubTimeoutSeconds": getattr(settings, "NUB_TIMEOUT_SECONDS", 30),
        }
    }


@app.post("/api/generate-schedule", response_model=TimetableOutput)
async def generate_schedule(input_data: SchedulingInput):
    """Generate schedule from direct input (manual data)"""
    try:
        if not input_data.instructors:
            raise HTTPException(status_code=400, detail="No instructors provided")
        if not input_data.courses:
            raise HTTPException(status_code=400, detail="No courses provided")
        if not input_data.rooms:
            raise HTTPException(status_code=400, detail="No rooms provided")

        engine = Scheduler(input_data)
        return engine.build()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")


@app.post("/api/generate-schedule/from-nub", response_model=TimetableOutput)
async def generate_schedule_from_nub():
    """Generate schedule from NUB backend automatically"""
    try:
        nub_base_url = getattr(settings, "NUB_BASE_URL", "http://nub-adex.runasp.net")
        nub_instructors_path = getattr(settings, "NUB_INSTRUCTORS_PATH", "/api/Instructors/all-with-availability")
        nub_courses_path = getattr(settings, "NUB_COURSES_PATH", "")
        nub_rooms_path = getattr(settings, "NUB_ROOMS_PATH", "")
        nub_timeout = getattr(settings, "NUB_TIMEOUT_SECONDS", 30)

        # 1) Fetch Instructors
        instructors_url = f"{nub_base_url}{nub_instructors_path}"
        resp = requests.get(instructors_url, timeout=nub_timeout)
        resp.raise_for_status()
        payload = resp.json()

        if isinstance(payload, dict):
            raw_instructors = payload.get("data") or payload.get("items") or payload.get("instructors") or []
        elif isinstance(payload, list):
            raw_instructors = payload
        else:
            raw_instructors = []

        if not raw_instructors:
            raise HTTPException(status_code=502, detail="NUB returned no instructors")

        instructors: list[Instructor] = []
        courses_map: dict[str, dict] = {}
        rooms_map: dict[int, dict] = {}

        # Map instructors and extract courses
        for idx, ri in enumerate(raw_instructors, start=1):
            if not isinstance(ri, dict):
                continue

            instructor_id = ri.get("instructorId") or ri.get("id") or ri.get("staffId") or idx
            try:
                instructor_id = int(instructor_id)
            except Exception:
                instructor_id = idx

            name = ri.get("name") or ri.get("fullName") or f"Instructor {instructor_id}"
            itype = (ri.get("instructorType") or ri.get("type") or "DOCTOR").upper()
            if itype not in ("DOCTOR", "TA"):
                itype = "DOCTOR"

            assigned = ri.get("assignedCourses") or ri.get("courses") or []
            assigned_codes = []

            if isinstance(assigned, list):
                for c in assigned:
                    if isinstance(c, str):
                        code = c.strip()
                        cname = c.strip()
                    elif isinstance(c, dict):
                        code = c.get("courseCode") or c.get("code") or c.get("id") or ""
                        cname = c.get("courseName") or c.get("name") or str(code)
                    else:
                        continue

                    if code:
                        assigned_codes.append(code)
                        if code not in courses_map:
                            courses_map[code] = {
                                "courseCode": code,
                                "courseName": cname or code,
                                "level": 1,
                                "enrollmentCount": 150,
                                "creditHours": 2,
                                "department": None,
                                "labType": None,
                            }

            availabilities = ri.get("availabilities") or ri.get("availability") or []
            instructors.append(
                Instructor(
                    instructorId=instructor_id,
                    name=name,
                    instructorType=itype,
                    assignedCourses=assigned_codes,
                    availabilities=availabilities if isinstance(availabilities, list) else []
                )
            )

        # 2) Fetch Courses (optional endpoint)
        if nub_courses_path:
            try:
                c_url = f"{nub_base_url}{nub_courses_path}"
                c_resp = requests.get(c_url, timeout=nub_timeout)
                c_resp.raise_for_status()
                c_payload = c_resp.json()

                if isinstance(c_payload, dict):
                    raw_courses = c_payload.get("data") or c_payload.get("items") or []
                elif isinstance(c_payload, list):
                    raw_courses = c_payload
                else:
                    raw_courses = []

                for rc in raw_courses:
                    if not isinstance(rc, dict):
                        continue
                    code = rc.get("courseCode") or rc.get("code")
                    if not code:
                        continue

                    level_val = max(1, min(4, int(rc.get("level", 1) or 1)))
                    students_val = max(0, int(rc.get("enrollmentCount", rc.get("students", 150)) or 150))
                    credit_val = max(1, min(6, int(rc.get("creditHours", 2) or 2)))
                    lab_raw = rc.get("labType")
                    lab_val = lab_raw if lab_raw in ("LAB_ONLY", "GENERAL_LAB", "PH101_LAB") else None

                    courses_map[code] = {
                        "courseCode": code,
                        "courseName": rc.get("courseName") or rc.get("name") or code,
                        "level": level_val,
                        "enrollmentCount": students_val,
                        "creditHours": credit_val,
                        "department": rc.get("department"),
                        "labType": lab_val,
                    }
            except Exception:
                pass

        # 3) Fetch Rooms (optional endpoint)
        used_fallback_rooms = False
        if nub_rooms_path:
            try:
                r_url = f"{nub_base_url}{nub_rooms_path}"
                r_resp = requests.get(r_url, timeout=nub_timeout)
                r_resp.raise_for_status()
                r_payload = r_resp.json()

                if isinstance(r_payload, dict):
                    raw_rooms = r_payload.get("data") or r_payload.get("items") or []
                elif isinstance(r_payload, list):
                    raw_rooms = r_payload
                else:
                    raw_rooms = []

                for rr in raw_rooms:
                    if not isinstance(rr, dict):
                        continue

                    rid = rr.get("roomId") or rr.get("id")
                    if rid is None:
                        continue
                    try:
                        rid = int(rid)
                    except Exception:
                        continue

                    rtype = (rr.get("roomType") or "GENERAL").upper()
                    if rtype not in ("GENERAL", "LAB_ONLY", "PH101_LAB"):
                        rtype = "GENERAL"

                    capacity_val = max(1, int(rr.get("capacity", 100) or 100))

                    rooms_map[rid] = {
                        "roomId": rid,
                        "roomNumber": str(rr.get("roomNumber") or rr.get("name") or f"R{rid}"),
                        "roomType": rtype,
                        "capacity": capacity_val,
                    }
            except Exception:
                used_fallback_rooms = True

        # Use fallback rooms if none available
        if not rooms_map:
            used_fallback_rooms = True
            rooms_map = {
                1: {"roomId": 1, "roomNumber": "R-101", "roomType": "GENERAL", "capacity": 200},
                2: {"roomId": 2, "roomNumber": "R-102", "roomType": "GENERAL", "capacity": 150},
                3: {"roomId": 3, "roomNumber": "R-103", "roomType": "GENERAL", "capacity": 120},
                4: {"roomId": 4, "roomNumber": "LAB-1", "roomType": "LAB_ONLY", "capacity": 50},
                5: {"roomId": 5, "roomNumber": "LAB-2", "roomType": "LAB_ONLY", "capacity": 40},
                6: {"roomId": 6, "roomNumber": "PH-2104", "roomType": "PH101_LAB", "capacity": 35},
            }

        courses = [Course(**c) for c in courses_map.values()]
        rooms = [Room(**r) for r in rooms_map.values()]

        if not instructors:
            raise HTTPException(status_code=502, detail="No instructors available after mapping")
        if not courses:
            raise HTTPException(status_code=502, detail="No courses available after mapping")
        if not rooms:
            raise HTTPException(status_code=502, detail="No rooms available after mapping")

        input_data = SchedulingInput(instructors=instructors, courses=courses, rooms=rooms)
        schedule = Scheduler(input_data).build()

        schedule.metadata = {
            **(schedule.metadata or {}),
            "source": "nub_with_fallback_rooms" if used_fallback_rooms else "nub_full",
            "instructors_count": len(instructors),
            "courses_count": len(courses),
            "rooms_count": len(rooms),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        return schedule

    except HTTPException:
        raise
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"NUB API request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generate_schedule_from_nub failed: {str(e)}")


@app.get("/api/generate-schedule/from-nub/export")
async def generate_schedule_from_nub_export(request: Request):
    """Generate schedule from NUB and export as JSON file"""
    schedule = await generate_schedule_from_nub()

    file_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    file_name = f"schedule_{file_id}.json"
    file_path = os.path.join(EXPORT_DIR, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(schedule.model_dump(), f, ensure_ascii=False, indent=2)

    base_url = str(request.base_url).rstrip("/")

    return {
        "success": True,
        "message": "Schedule exported successfully",
        "fileName": file_name,
        "fileUrl": f"/api/exports/{file_name}",
        "downloadUrl": f"{base_url}/api/exports/{file_name}",
        "metadata": schedule.metadata
    }


@app.get("/api/exports/{file_name}")
async def get_exported_file(file_name: str):
    """Download exported schedule file"""
    if ".." in file_name or file_name.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file name")

    file_path = os.path.join(EXPORT_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="application/json", filename=file_name)


@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 80)
    print("🚀 ADEX SCHEDULING API - STARTING UP")
    print("=" * 80)
    print(f"   Version: {settings.API_VERSION}")
    print("=" * 80)
    print("\n📍 Available Endpoints:")
    print("   - GET  /health")
    print("   - GET  /config")
    print("   - POST /api/generate-schedule")
    print("   - POST /api/generate-schedule/from-nub")
    print("   - GET  /api/generate-schedule/from-nub/export  ✅ CHANGED TO GET")
    print("   - GET  /api/exports/{file_name}")
    print("   - GET  /docs")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)