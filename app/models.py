"""
Data Models for ADEX Scheduling System
Pydantic models for input/output validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum
import re
class InstructorType(str, Enum):
    """Instructor type enumeration"""
    DOCTOR = "DOCTOR"
    TA = "TA"
class RoomType(str, Enum):
    """Room type enumeration"""
    GENERAL = "GENERAL"
    LAB_ONLY = "LAB_ONLY"
    PH101_LAB = "PH101_LAB"
class SessionType(str, Enum):
    """Session type enumeration"""
    LECTURE = "LECTURE"
    SECTION = "SECTION"
class Availability(BaseModel):
    """Instructor availability window"""
    availabilityId: Optional[int] = None
    dayOfWeek: str
    startTime: str  # HH:MM format
    endTime: str    # HH:MM format
    isAvailable: bool = True

    @field_validator("startTime", "endTime", mode="before")
    @classmethod
    def validate_time_format(cls, v):
        """Validate time format HH:MM and remove seconds if present"""
        if v:
            if isinstance(v, str) and len(v) > 5:
                v = v[:5]  # "09:00:00" -> "09:00"
            if isinstance(v, str) and not re.match(r"^\d{2}:\d{2}$", v):
                raise ValueError("Time must be in HH:MM format (e.g., 09:00)")
        return v
class AssignedCourse(BaseModel):
    """Course assigned to an instructor"""
    courseCode: str
    courseName: Optional[str] = ""
class Instructor(BaseModel):
    """Instructor (Doctor or TA)"""
    instructorId: int
    name: Optional[str] = None
    instructorType: InstructorType
    assignedCourses: Union[List[str], List[AssignedCourse]] = []
    availabilities: List[Availability] = []


class Course(BaseModel):
    """Course information"""
    courseCode: str
    courseName: str
    level: int = Field(ge=1, le=4)
    enrollmentCount: int = Field(ge=0)
    creditHours: int = Field(ge=1, le=6)
    department: Optional[str] = None
    labType: Optional[Literal["LAB_ONLY", "GENERAL_LAB", "PH101_LAB"]] = None
class Room(BaseModel):
    """Room/Classroom"""
    roomId: int
    roomNumber: str
    roomType: RoomType
    capacity: int = Field(gt=0)

class SchedulingInput(BaseModel):
    """Input data for scheduling"""
    instructors: List[Instructor]
    courses: List[Course]
    rooms: List[Room]

class ScheduledSession(BaseModel):
    """A scheduled session (lecture or section)"""
    sessionId: str
    sessionType: SessionType
    courseCode: str
    courseName: str
    groupId: str
    sectionId: Optional[str] = None
    instructorId: int
    instructorName: Optional[str] = None
    roomId: Optional[int] = None
    roomNumber: Optional[str] = None
    dayOfWeek: str
    timeSlot: str
    studentCount: int = 0


class GroupSchedule(BaseModel):
    """Schedule for a group"""
    groupId: str
    level: int
    department: Optional[str] = None
    studentCount: int
    sessions: List[ScheduledSession] = []
    totalSessions: int = 0


class InstructorSchedule(BaseModel):
    """Schedule for an instructor"""
    instructorId: int
    instructorName: str
    instructorType: InstructorType
    sessions: List[ScheduledSession] = []
    totalSessions: int = 0


class RoomSchedule(BaseModel):
    """Schedule for a room"""
    roomId: int
    roomNumber: str
    sessions: List[ScheduledSession] = []
    utilizationRate: float = Field(ge=0.0, le=1.0, default=0.0)


class TimetableOutput(BaseModel):
    """Complete timetable output"""
    success: bool = True
    message: str = "Schedule generated successfully"
    groupSchedules: List[GroupSchedule] = []
    instructorSchedules: List[InstructorSchedule] = []
    roomSchedules: List[RoomSchedule] = []
    totalSessions: int = 0
    totalGroups: int = 0
    fitnessScore: float = 0.0
    generationsUsed: int = 0
    metadata: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    details: Optional[str] = None

class LevelGroup(BaseModel):
    """Academic group (150 students max)"""
    level: int
    group_number: int
    group_id: str
    department: Optional[str] = None
    student_count: int
    courses: List[str] = []

class Section(BaseModel):
    """Section within a group"""
    section_id: str
    group_id: str
    course_code: str
    student_count: int
    assigned_ta: Optional[int] = None

class Session(BaseModel):
    """Session to be scheduled"""
    session_id: str
    session_type: SessionType
    course_code: str
    group_id: Optional[str] = None
    section_id: Optional[str] = None
    instructor_id: int
    required_room_type: Optional[Literal["GENERAL", "LAB_ONLY", "PH101_LAB"]] = None
    student_count: int = Field(gt=0)
    scheduled_day: Optional[str] = None
    scheduled_time: Optional[str] = None
    assigned_room_id: Optional[int] = None
print("✅ ADEX Data Models loaded successfully!")