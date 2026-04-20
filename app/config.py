"""
Configuration and Constants for ADEX Scheduling System
"""

from typing import List
from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support
    """

    # ----------------------------
    # API Metadata
    # ----------------------------
    API_TITLE: str = "ADEX - Smart Academic Scheduling System"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "AI-powered academic timetable generator"

    # ----------------------------
    # CORS
    # ----------------------------
    CORS_ORIGINS: List[str] = ["*"]

    # ----------------------------
    # Genetic Algorithm
    # ----------------------------
    GA_POPULATION_SIZE: int = 60
    GA_GENERATIONS: int = 200
    GA_MUTATION_RATE: float = 0.25
    GA_CROSSOVER_RATE: float = 0.8
    GA_ELITE_SIZE: int = 6

    # ----------------------------
    # Time Configuration
    # ----------------------------
    DAYS_OF_WEEK: List[str] = [
        "Saturday",
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
    ]

    REGULAR_TIME_SLOTS: List[str] = [
        "09:00-11:00",
        "11:00-13:00",
        "13:00-15:00",
    ]

    ONLINE_TIME_SLOTS: List[str] = ["19:00-21:00"]

    TIME_SLOTS: List[str] = REGULAR_TIME_SLOTS + ONLINE_TIME_SLOTS

    # ----------------------------
    # Group / Section Constraints
    # ----------------------------
    TARGET_GROUP_SIZE: int = 150
    SECTION_CAPACITY: int = 50
    MIN_SECTIONS_PER_GROUP: int = 2
    MAX_SECTIONS_PER_GROUP: int = 4

    # ----------------------------
    # NUB Integration (NEW)
    # ----------------------------
    NUB_BASE_URL: str = "http://nub-adex.runasp.net"
    NUB_INSTRUCTORS_PATH: str = "/api/Instructors/all-with-availability"
    NUB_TIMEOUT_SECONDS: int = 30

    # Optional (when backend provides them)
    NUB_COURSES_PATH: str = ""
    NUB_ROOMS_PATH: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = "utf-8"


settings = Settings()

ONLINE_COURSES = [
    "REM101",
    "MGT101",
    "HUM101",
    "ETS401",
]

print("✅ ADEX Configuration loaded successfully!")
print(f"- GA Population: {settings.GA_POPULATION_SIZE}")
print(f"- GA Generations: {settings.GA_GENERATIONS}")
print(f"- Days: {len(settings.DAYS_OF_WEEK)} days")
print(f"- Regular Slots: {len(settings.REGULAR_TIME_SLOTS)} slots")
print(f"- Online Slots: {len(settings.ONLINE_TIME_SLOTS)} slot(s)")
print(f"- Total Slots: {len(settings.TIME_SLOTS)} slots")
print(f"- Online Courses: {len(ONLINE_COURSES)} courses")
print(f"- NUB Base URL: {settings.NUB_BASE_URL}")
print(f"- NUB Instructors Path: {settings.NUB_INSTRUCTORS_PATH}")
print(f"- NUB Timeout: {settings.NUB_TIMEOUT_SECONDS}s")
