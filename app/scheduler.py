"""
Final Scheduler (Conflict-Free Initial Builder)
With online courses support (7-9 PM)
"""

import math
from datetime import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from app.models import (
    SchedulingInput,
    TimetableOutput,
    ScheduledSession,
    SessionType,
    RoomType,
    InstructorType,
    GroupSchedule,
    InstructorSchedule,
    RoomSchedule,
)
from app.config import settings, ONLINE_COURSES 


def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def _slot_to_range(slot: str) -> Tuple[time, time]:
    a, b = slot.split("-")
    return _parse_hhmm(a), _parse_hhmm(b)


class Scheduler:
    def __init__(self, input_data: SchedulingInput):
        self.input_data = input_data
        self.session_counter = 0

        self.courses = {c.courseCode: c for c in input_data.courses}
        self.instructors = {i.instructorId: i for i in input_data.instructors}
        self.rooms = {r.roomId: r for r in input_data.rooms}
        self.group_busy = set()
        self.instructor_busy = set()
        self.room_busy = set()

        self.group_schedules: Dict[str, List[ScheduledSession]] = defaultdict(list)
        self.instructor_schedules: Dict[int, List[ScheduledSession]] = defaultdict(list)
        self.room_schedules: Dict[int, List[ScheduledSession]] = defaultdict(list)


        self.level_groups: Dict[int, List[dict]] = defaultdict(list)
        self.group_sizes: Dict[str, int] = {}
        self.group_details: Dict[str, dict] = {}

        self.unscheduled_reasons: List[str] = []

        self.days = settings.DAYS_OF_WEEK
        self.regular_slots = settings.REGULAR_TIME_SLOTS
        self.online_slots = settings.ONLINE_TIME_SLOTS
        self.time_slots = self.regular_slots + self.online_slots

    def build(self) -> TimetableOutput:
        self._create_level_groups()

        demands = self._build_demands()
        demands.sort(key=lambda d: d["difficulty"], reverse=True)

        for d in demands:
            if not self._schedule_one_demand(d):
                self.unscheduled_reasons.append(
                    f"Could not schedule {d['session_type']} for {d['course_code']} group={d['group_id']}"
                )

        conflicts = self.validate_no_conflicts()
        success = (len(conflicts) == 0 and len(self.unscheduled_reasons) == 0)

        return TimetableOutput(
            success=success,
            message=" Schedule generated successfully" if success else " Schedule generated with issues",
            groupSchedules=self._build_group_schedules_output(),
            instructorSchedules=self._build_instructor_schedules_output(),
            roomSchedules=self._build_room_schedules_output(),
            totalSessions=sum(len(sessions) for sessions in self.group_schedules.values()),
            totalGroups=len(self.group_schedules),
            metadata={
                "unscheduled_count": len(self.unscheduled_reasons),
                "unscheduled_reasons": self.unscheduled_reasons,
                "conflicts": conflicts,
            },
        )
    def _create_level_groups(self):
        level_max = defaultdict(int)
        for c in self.input_data.courses:
            level_max[c.level] = max(level_max[c.level], c.enrollmentCount)

        target_group_size = settings.TARGET_GROUP_SIZE

        for level, max_enroll in level_max.items():
            if max_enroll <= 0:
                continue

            num_groups = max(1, math.ceil(max_enroll / target_group_size))
            base = max_enroll // num_groups
            rem = max_enroll % num_groups

            for g in range(1, num_groups + 1):
                size = base + (1 if g <= rem else 0)
                gid = f"L{level}-G{g}"
                self.level_groups[level].append({"group_id": gid, "size": size})
                self.group_sizes[gid] = size
                self.group_details[gid] = {
                    "level": level,
                    "group_id": gid,
                    "student_count": size,
                    "department": None,
                }
    def _build_demands(self) -> List[dict]:
        demands: List[dict] = []

        for course in self.input_data.courses:
            level_groups = self.level_groups.get(course.level, [])
            is_online = course.courseCode in ONLINE_COURSES 

            for g in level_groups:
                group_id = g["group_id"]
                group_size = g["size"]

          
                demands.append({
                    "course_code": course.courseCode,
                    "course_name": course.courseName,
                    "group_id": group_id,
                    "student_count": group_size,
                    "session_type": SessionType.LECTURE,
                    "difficulty": 70,
                    "is_online": is_online,
                })

                if is_online:
                    continue

                if course.labType is not None:
                    section_capacity = settings.SECTION_CAPACITY
                    sections_needed = max(1, math.ceil(group_size / section_capacity))
                    for s_idx in range(1, sections_needed + 1):
                        sec_size = min(section_capacity, group_size - (s_idx - 1) * section_capacity)
                        if sec_size <= 0:
                            continue
                        demands.append({
                            "course_code": course.courseCode,
                            "course_name": course.courseName,
                            "group_id": group_id,
                            "student_count": sec_size,
                            "section_id": f"{group_id}-{course.courseCode}-S{s_idx}",
                            "session_type": SessionType.SECTION,
                            "difficulty": 90 if course.labType in ("LAB_ONLY", "PH101_LAB") else 60,
                            "is_online": False,
                        })

        return demands
    def _generate_session_id(self) -> str:
        """توليد معرّف فريد لكل جلسة"""
        self.session_counter += 1
        return f"SESSION_{self.session_counter:06d}"

    def _schedule_one_demand(self, d: dict) -> bool:
        course = self.courses[d["course_code"]]
        group_id = d["group_id"]
        session_type = d["session_type"]
        student_count = d["student_count"]
        section_id = d.get("section_id")
        is_online = d.get("is_online", False)
        course_name = d.get("course_name", course.courseName)

        candidate_instructors = self._get_matching_instructors(course.courseCode, session_type)
        candidate_rooms = self._get_matching_rooms(course, session_type, student_count, is_online)

        if not candidate_instructors:
            return False
        if not is_online and not candidate_rooms:
            return False

        time_slots = self.online_slots if is_online else self.regular_slots

        for day in self.days:
            for slot in time_slots:
                for inst in candidate_instructors:
                    if not self._is_instructor_available(inst, day, slot):
                        continue

                    if is_online:
                        if self._can_place_online(group_id, inst.instructorId, day, slot):
                            session = ScheduledSession(
                                sessionId=self._generate_session_id(),
                                sessionType=session_type,
                                courseCode=course.courseCode,
                                courseName=course_name,
                                groupId=group_id,
                                sectionId=section_id,
                                instructorId=inst.instructorId,
                                instructorName=inst.name,
                                roomId=None,  #  أونلاين لا قاعة
                                roomNumber=None,  #  أونلاين لا قاعة
                                dayOfWeek=day,
                                timeSlot=slot,
                                studentCount=student_count,
                            )
                            self._place_session(group_id, session)
                            return True
                    else:
                        for room in candidate_rooms:
                            if self._can_place(group_id, inst.instructorId, room.roomId, day, slot):
                                session = ScheduledSession(
                                    sessionId=self._generate_session_id(),
                                    sessionType=session_type,
                                    courseCode=course.courseCode,
                                    courseName=course_name,
                                    groupId=group_id,
                                    sectionId=section_id,
                                    instructorId=inst.instructorId,
                                    instructorName=inst.name,
                                    roomId=room.roomId,
                                    roomNumber=room.roomNumber,
                                    dayOfWeek=day,
                                    timeSlot=slot,
                                    studentCount=student_count,
                                )
                                self._place_session(group_id, session)
                                return True
        return False

    def _can_place(self, group_id: str, instructor_id: int, room_id: int, day: str, slot: str) -> bool:
        if (group_id, day, slot) in self.group_busy:
            return False
        if (instructor_id, day, slot) in self.instructor_busy:
            return False
        if (room_id, day, slot) in self.room_busy:
            return False
        return True

    def _can_place_online(self, group_id: str, instructor_id: int, day: str, slot: str) -> bool:
        if (group_id, day, slot) in self.group_busy:
            return False
        if (instructor_id, day, slot) in self.instructor_busy:
            return False
        return True

    def _place_session(self, group_id: str, session: ScheduledSession):
        self.group_schedules[group_id].append(session)
        self.instructor_schedules[session.instructorId].append(session)
        if session.roomId is not None:
            self.room_schedules[session.roomId].append(session)

        self.group_busy.add((group_id, session.dayOfWeek, session.timeSlot))
        self.instructor_busy.add((session.instructorId, session.dayOfWeek, session.timeSlot))
        if session.roomId is not None:
            self.room_busy.add((session.roomId, session.dayOfWeek, session.timeSlot))

    def _get_matching_instructors(self, course_code: str, session_type: SessionType):
        assigned = []
        for i in self.instructors.values():
            assigned_courses = [ac if isinstance(ac, str) else ac.courseCode for ac in i.assignedCourses]
            if course_code in assigned_courses:
                assigned.append(i)

        if session_type == SessionType.LECTURE:
            doctors = [i for i in assigned if i.instructorType == InstructorType.DOCTOR]
            return doctors if doctors else assigned

        tas = [i for i in assigned if i.instructorType == InstructorType.TA]
        return tas if tas else assigned

    def _get_matching_rooms(self, course, session_type: SessionType, student_count: int, is_online: bool = False):
        if is_online:
            return []

        all_rooms = list(self.rooms.values())

        if session_type == SessionType.LECTURE:
            rooms = [r for r in all_rooms if r.roomType == RoomType.GENERAL]
            return [r for r in rooms if r.capacity >= student_count]

        lab_type = course.labType
        if lab_type == "GENERAL_LAB":  # ✅ الصحيح: GENERAL_LAB
            rooms = [r for r in all_rooms if r.roomType in (RoomType.GENERAL, RoomType.LAB_ONLY)]
        elif lab_type == "LAB_ONLY":
            rooms = [r for r in all_rooms if r.roomType == RoomType.LAB_ONLY]
        elif lab_type == "PH101_LAB":
            rooms = [r for r in all_rooms if r.roomType == RoomType.PH101_LAB]
        else:
            rooms = []

        return [r for r in rooms if r.capacity >= student_count]

    def _is_instructor_available(self, instructor, day: str, slot: str) -> bool:
        slot_start, slot_end = _slot_to_range(slot)

        for a in instructor.availabilities:
            if a.dayOfWeek != day:
                continue
            if not getattr(a, "isAvailable", True):
                continue

            a_start = _parse_hhmm(a.startTime)
            a_end = _parse_hhmm(a.endTime)
            if a_start <= slot_start and slot_end <= a_end:
                return True
        return False

    def validate_no_conflicts(self) -> List[str]:
        seen_group = set()
        seen_inst = set()
        seen_room = set()
        conflicts = []

        for gid, sessions in self.group_schedules.items():
            for s in sessions:
                k_group = (gid, s.dayOfWeek, s.timeSlot)
                k_inst = (s.instructorId, s.dayOfWeek, s.timeSlot)

                if k_group in seen_group:
                    conflicts.append(f"GROUP conflict: {k_group}")
                else:
                    seen_group.add(k_group)

                if k_inst in seen_inst:
                    conflicts.append(f"INSTRUCTOR conflict: {k_inst}")
                else:
                    seen_inst.add(k_inst)

                if s.roomId is not None:
                    k_room = (s.roomId, s.dayOfWeek, s.timeSlot)
                    if k_room in seen_room:
                        conflicts.append(f"ROOM conflict: {k_room}")
                    else:
                        seen_room.add(k_room)

        return conflicts
    def _build_group_schedules_output(self) -> List[GroupSchedule]:
        """ملء جميع الحقول المطلوبة"""
        result = []
        for gid, sessions in self.group_schedules.items():
            group_meta = self.group_details.get(gid, {})
            result.append(
                GroupSchedule(
                    groupId=gid,
                    level=group_meta.get("level", 1),
                    department=group_meta.get("department"),
                    studentCount=group_meta.get("student_count", 0),
                    sessions=sessions,
                    totalSessions=len(sessions),
                )
            )
        return result

    def _build_instructor_schedules_output(self) -> List[InstructorSchedule]:
        """ملء جميع الحقول المطلوبة"""
        result = []
        for iid, sessions in self.instructor_schedules.items():
            instructor = self.instructors.get(iid)
            if instructor:
                result.append(
                    InstructorSchedule(
                        instructorId=iid,
                        instructorName=instructor.name or f"Instructor {iid}",
                        instructorType=instructor.instructorType,
                        sessions=sessions,
                        totalSessions=len(sessions),
                    )
                )
        return result

    def _build_room_schedules_output(self) -> List[RoomSchedule]:
        result = []
        for rid, sessions in self.room_schedules.items():
            room = self.rooms.get(rid)
            if room:
                total_slots = len(self.days) * len(self.regular_slots)
                hours_used = len(sessions) * 2
                max_hours = total_slots * 2
                utilization = min(1.0, hours_used / max_hours) if max_hours > 0 else 0.0
                
                result.append(
                    RoomSchedule(
                        roomId=rid,
                        roomNumber=room.roomNumber,
                        sessions=sessions,
                        utilizationRate=utilization,
                    )
                )
        return result
    
print("✅ Scheduler class defined successfully")