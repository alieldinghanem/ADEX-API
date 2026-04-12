"""
Genetic Algorithm for Timetable Optimization
Safe version: preserves hard constraints (no conflicts) after any mutation/crossover.
"""

import random
import copy
from typing import List, Dict, Tuple

from app.models import TimetableOutput, SchedulingInput
from app.config import settings


class GeneticAlgorithm:
    """
    Genetic Algorithm to optimize timetable
    Goals:
    - Reduce gaps between sessions for each group
    - Reduce number of attendance days per group
    - Maintain all hard constraints
    """

    def __init__(self):
        self.population_size = settings.GA_POPULATION_SIZE
        self.generations = settings.GA_GENERATIONS
        self.mutation_rate = settings.GA_MUTATION_RATE
        self.crossover_rate = settings.GA_CROSSOVER_RATE
        self.elite_size = settings.GA_ELITE_SIZE

        self.best_fitness = 0.0
        self.best_schedule = None

        # Slot ordering for gap calculations
        self.time_order = {
            "09:00-11:00": 1,
            "11:00-13:00": 2,
            "13:00-15:00": 3,
            "19:00-21:00": 4,
        }

    # =========================
    # Public API
    # =========================
    def optimize(self, initial_schedule: TimetableOutput, input_data: SchedulingInput) -> TimetableOutput:
        """
        Main optimization method
        Takes initial schedule and returns optimized version
        """
        print("\n🧬 Starting Genetic Algorithm optimization...")
        print(f"   Population: {self.population_size}")
        print(f"   Generations: {self.generations}")

        # If initial is already invalid, return it safely
        if self._has_conflicts(initial_schedule):
            print("⚠️ Initial schedule has conflicts. Skipping GA and returning initial schedule.")
            initial_schedule.metadata = {
                **(initial_schedule.metadata or {}),
                "ga_skipped": True,
                "reason": "Initial schedule contains conflicts",
            }
            return initial_schedule

        population = self._create_initial_population(initial_schedule, input_data)

        for generation in range(self.generations):
            fitness_scores = [self._calculate_fitness(ind) for ind in population]

            best_idx = fitness_scores.index(max(fitness_scores))
            if fitness_scores[best_idx] > self.best_fitness:
                self.best_fitness = fitness_scores[best_idx]
                self.best_schedule = copy.deepcopy(population[best_idx])

            if generation % 50 == 0 or generation == self.generations - 1:
                avg_fitness = sum(fitness_scores) / len(fitness_scores)
                print(f"   Gen {generation:3d}: Best={self.best_fitness:.3f}, Avg={avg_fitness:.3f}")

            selected = self._tournament_selection(population, fitness_scores)
            new_population: List[TimetableOutput] = []

            # Elitism
            elite_indices = sorted(
                range(len(fitness_scores)),
                key=lambda i: fitness_scores[i],
                reverse=True
            )[:self.elite_size]

            for idx in elite_indices:
                new_population.append(copy.deepcopy(population[idx]))

            # Fill remaining
            while len(new_population) < self.population_size:
                parent1 = random.choice(selected)
                parent2 = random.choice(selected)

                if random.random() < self.crossover_rate:
                    child = self._crossover(parent1, parent2)
                else:
                    child = copy.deepcopy(parent1)

                if random.random() < self.mutation_rate:
                    child = self._mutate(child, mutation_strength=0.1)

                # Repair + keep only valid children
                self._rebuild_derived_views(child)
                if not self._has_conflicts(child):
                    new_population.append(child)
                else:
                    # Fallback to safe parent
                    safe_parent = copy.deepcopy(parent1)
                    self._rebuild_derived_views(safe_parent)
                    new_population.append(safe_parent)

            population = new_population

        if self.best_schedule is None:
            self.best_schedule = copy.deepcopy(initial_schedule)

        self._rebuild_derived_views(self.best_schedule)

        self.best_schedule.fitnessScore = self.best_fitness
        self.best_schedule.generationsUsed = self.generations
        self.best_schedule.metadata = {
            **(self.best_schedule.metadata or {}),
            "algorithm": "Genetic Algorithm (Safe)",
            "population_size": self.population_size,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
            "elite_size": self.elite_size,
            "final_conflicts": self.validate_no_conflicts(self.best_schedule),
        }

        print(f"✅ Optimization complete! Best fitness: {self.best_fitness:.3f}")
        return self.best_schedule

    # =========================
    # Population
    # =========================
    def _create_initial_population(self, base_schedule: TimetableOutput, input_data: SchedulingInput) -> List[TimetableOutput]:
        population = [copy.deepcopy(base_schedule)]

        for _ in range(self.population_size - 1):
            variant = copy.deepcopy(base_schedule)
            variant = self._mutate(variant, mutation_strength=0.2)
            self._rebuild_derived_views(variant)

            if self._has_conflicts(variant):
                variant = copy.deepcopy(base_schedule)

            population.append(variant)

        return population

    # =========================
    # Fitness
    # =========================
    def _calculate_fitness(self, schedule: TimetableOutput) -> float:
        fitness = 100.0

        # Hard-constraint penalty (very large)
        conflicts = len(self.validate_no_conflicts(schedule))
        if conflicts > 0:
            return max(0.0, fitness - conflicts * 50)

        gaps_penalty = self._calculate_gaps_penalty(schedule)
        days_penalty = self._calculate_days_penalty(schedule)
        utilization_bonus = self._calculate_utilization_bonus(schedule)

        fitness -= gaps_penalty * 5
        fitness -= days_penalty * 10
        fitness += utilization_bonus * 2

        return max(0.0, fitness)

    def _calculate_gaps_penalty(self, schedule: TimetableOutput) -> float:
        total_gaps = 0

        for gs in schedule.groupSchedules:
            by_day: Dict[str, List[int]] = {}
            for s in gs.sessions:
                by_day.setdefault(s.dayOfWeek, []).append(self.time_order.get(s.timeSlot, 0))

            for _, slots in by_day.items():
                slots = sorted([x for x in slots if x > 0])
                for i in range(len(slots) - 1):
                    if slots[i + 1] - slots[i] > 1:
                        total_gaps += 1

        return total_gaps / max(1, len(schedule.groupSchedules))

    def _calculate_days_penalty(self, schedule: TimetableOutput) -> float:
        total_extra_days = 0

        for gs in schedule.groupSchedules:
            days = set(s.dayOfWeek for s in gs.sessions)
            if len(days) > 4:
                total_extra_days += (len(days) - 4)

        return total_extra_days / max(1, len(schedule.groupSchedules))

    def _calculate_utilization_bonus(self, schedule: TimetableOutput) -> float:
        if not schedule.roomSchedules:
            return 0.0

        utilizations = [rs.utilizationRate for rs in schedule.roomSchedules]
        if not utilizations:
            return 0.0

        avg_util = sum(utilizations) / len(utilizations)
        variance = sum((u - avg_util) ** 2 for u in utilizations) / len(utilizations)
        return max(0.0, 1.0 - variance)

    # =========================
    # GA Operators
    # =========================
    def _tournament_selection(
        self,
        population: List[TimetableOutput],
        fitness_scores: List[float],
        tournament_size: int = 3
    ) -> List[TimetableOutput]:
        selected = []
        for _ in range(len(population)):
            tournament = random.sample(list(enumerate(population)), k=min(tournament_size, len(population)))
            winner = max(tournament, key=lambda x: fitness_scores[x[0]])
            selected.append(winner[1])
        return selected

    def _crossover(self, parent1: TimetableOutput, parent2: TimetableOutput) -> TimetableOutput:
        child = copy.deepcopy(parent1)

        if len(child.groupSchedules) == 0 or len(parent2.groupSchedules) == 0:
            return child

        group_idx = random.randint(0, len(child.groupSchedules) - 1)
        if group_idx < len(parent2.groupSchedules):
            child.groupSchedules[group_idx].sessions = copy.deepcopy(parent2.groupSchedules[group_idx].sessions)
            child.groupSchedules[group_idx].totalSessions = len(child.groupSchedules[group_idx].sessions)

        return child

    def _mutate(self, schedule: TimetableOutput, mutation_strength: float = 0.1) -> TimetableOutput:
        """
        Safe mutate: swap time slots only between sessions of the SAME group.
        """
        for gs in schedule.groupSchedules:
            if random.random() < mutation_strength and len(gs.sessions) > 1:
                idx1, idx2 = random.sample(range(len(gs.sessions)), 2)

                gs.sessions[idx1].timeSlot, gs.sessions[idx2].timeSlot = (
                    gs.sessions[idx2].timeSlot,
                    gs.sessions[idx1].timeSlot,
                )
                gs.sessions[idx1].dayOfWeek, gs.sessions[idx2].dayOfWeek = (
                    gs.sessions[idx2].dayOfWeek,
                    gs.sessions[idx1].dayOfWeek,
                )

        return schedule

    # =========================
    # Rebuild / Validation
    # =========================
    def _rebuild_derived_views(self, schedule: TimetableOutput) -> None:
        """
        Rebuild instructorSchedules and roomSchedules from groupSchedules.
        Also refresh totals and room utilization.
        """
        # instructor map
        inst_map = {}
        for inst in schedule.instructorSchedules:
            inst_map[inst.instructorId] = inst

        # room map
        room_map = {}
        for room in schedule.roomSchedules:
            room_map[room.roomId] = room

        # clear sessions
        for inst in inst_map.values():
            inst.sessions = []
            inst.totalSessions = 0

        for room in room_map.values():
            room.sessions = []
            room.utilizationRate = 0.0

        total_sessions = 0

        for gs in schedule.groupSchedules:
            gs.totalSessions = len(gs.sessions)
            total_sessions += len(gs.sessions)

            for s in gs.sessions:
                if s.instructorId in inst_map:
                    inst_map[s.instructorId].sessions.append(s)

                if s.roomId is not None and s.roomId in room_map:
                    room_map[s.roomId].sessions.append(s)

        for inst in inst_map.values():
            inst.totalSessions = len(inst.sessions)

        # utilization based on configured regular slots only (same as scheduler.py)
        total_slots = len(settings.DAYS_OF_WEEK) * len(settings.REGULAR_TIME_SLOTS)
        max_hours = total_slots * 2

        for room in room_map.values():
            hours_used = len(room.sessions) * 2
            room.utilizationRate = min(1.0, hours_used / max_hours) if max_hours > 0 else 0.0

        schedule.totalSessions = total_sessions
        schedule.totalGroups = len(schedule.groupSchedules)

    def _has_conflicts(self, schedule: TimetableOutput) -> bool:
        return len(self.validate_no_conflicts(schedule)) > 0

    def validate_no_conflicts(self, timetable: TimetableOutput) -> List[str]:
        """
        Validate hard constraints:
        - Group cannot have two sessions at same day/time
        - Instructor cannot have two sessions at same day/time
        - Room cannot have two sessions at same day/time (ignore roomId=None)
        """
        seen_instructor = set()
        seen_room = set()
        seen_group = set()
        conflicts = []

        for gs in timetable.groupSchedules:
            for s in gs.sessions:
                k_group = (gs.groupId, s.dayOfWeek, s.timeSlot)
                k_inst = (s.instructorId, s.dayOfWeek, s.timeSlot)

                if k_group in seen_group:
                    conflicts.append(f"GROUP conflict: {k_group}")
                else:
                    seen_group.add(k_group)

                if k_inst in seen_instructor:
                    conflicts.append(f"INSTRUCTOR conflict: {k_inst}")
                else:
                    seen_instructor.add(k_inst)

                if s.roomId is not None:
                    k_room = (s.roomId, s.dayOfWeek, s.timeSlot)
                    if k_room in seen_room:
                        conflicts.append(f"ROOM conflict: {k_room}")
                    else:
                        seen_room.add(k_room)

        return conflicts


print("✅ Genetic Algorithm module loaded successfully (safe version)!")