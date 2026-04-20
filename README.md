# ADEX - Smart Academic Scheduling System

AI-powered academic timetable generator using Greedy Construction algorithm.

## 🚀 Quick Start

### Installation
```bash
# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Test with real data from .NET API
python test_full_system.py
```

### Production
```bash
# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or
python -m app.main
```

## 📡 API Endpoints

- `GET /` - Health check
- `GET /health` - Health status
- `GET /config` - System configuration
- `POST /api/generate-schedule` - Generate timetable
- `GET /docs` - Swagger UI documentation

## 📊 Features

- Group Management (G1, G2, G3, G4)
- Section Creation (G1A, G1B, G1C, G1D)
- Room Types (GENERAL, LAB_ONLY, PH101_LAB)
- Online Courses (7-9 PM)
- Conflict Detection

## 🔗 Integration

.NET API: `http://nub-adex.runasp.net/api/Instructors/all-with-availability`

Python API: `http://localhost:8000/api/generate-schedule`

## 👥 Team

- **Python Developer**: Ali
- **.NET Developer**: [Friend's name]

---

**Version**: 1.0.0
```

---

## ✅ **الملخص:**
```
الملفات الكاملة:
  ✅ __init__.py        - Package init
  ✅ config.py          - Configuration (120 lines)
  ✅ models.py          - Data models (250 lines)
  ✅ scheduler.py       - Scheduling engine (614 lines) - استخدم المرفق
  ✅ genetic_algorithm.py - GA optimization - استخدم المرفق
  ✅ main.py            - FastAPI server (100 lines)
  ✅ test_full_system.py - Testing script (300 lines)
  ✅ requirements.txt   - Dependencies
  ✅ .env               - Environment variables
  ✅ README.md          - Documentation

Total: ~1,600 lines of code