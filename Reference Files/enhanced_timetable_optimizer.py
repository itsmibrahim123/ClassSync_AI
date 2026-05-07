import pandas as pd
import random
from tqdm import tqdm
from datetime import time, datetime, timedelta
from collections import Counter
import numpy as np
import os

VERBOSE = False

# ==============================
# Enhanced Configuration Settings - UPDATED FOR 30-MIN SLOTS
# ==============================
CONFIG = {
    "working_days": ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    "daily_start": time(8, 0),
    "daily_end": time(18, 30),
    "slot_duration_minutes": 30,  # Changed to 30 minutes
    "theory_duration_slots": 4,   # 2 hours = 4 × 30-min slots
    "lab_duration_slots": 6,      # 3 hours = 6 × 30-min slots
    "vc_slot_days": ['Monday', 'Tuesday', 'Friday'],
    "vc_slot_time": (time(12, 30), time(14, 0)),  # 3 consecutive 30-min slots
    "disallow_weekends": True,
    "max_daily_hours_per_instructor": 8,
    "preferred_gap_minutes": 30,
    "evening_penalty_threshold": time(17, 0)
}

# ==============================
# Function: Load and clean data - UPDATED FOR HOURS PER WEEK COLUMN
# ==============================
def load_course_and_room_data(course_path, room_path):
    courses_df = pd.read_csv(course_path)
    rooms_df = pd.read_csv(room_path)

    courses_df.columns = courses_df.columns.str.strip()
    rooms_df.columns = rooms_df.columns.str.strip()

    courses_df['Course_Key'] = (
        courses_df['Course Name'].str.strip() + " - " +
        courses_df['Program'].str.strip() + courses_df['Section'].str.strip()
    )
    
    # Handle the Type column - should already exist in the new CSV
    if 'Type' not in courses_df.columns:
        # Fallback: infer from course name if Type column doesn't exist
        courses_df['Type'] = courses_df['Course Name'].apply(
            lambda x: 'Lab' if 'Lab' in str(x) else 'Theory'
        )
    
    # Ensure Type column values are standardized
    courses_df['Type'] = courses_df['Type'].str.strip()
    
    # Ensure Hours per week column exists
    if 'Hours per week' not in courses_df.columns:
        # Default to 3 hours if not specified
        courses_df['Hours per week'] = 3
        print("⚠️ Warning: 'Hours per week' column not found, defaulting to 3 hours")

    return courses_df, rooms_df

# ==============================
# Enhanced Function: Generate 30-minute time slots
# ==============================
def generate_time_slots(config):
    slots = []
    start_dt = datetime.combine(datetime.today(), config["daily_start"])
    end_dt = datetime.combine(datetime.today(), config["daily_end"])
    delta = timedelta(minutes=config["slot_duration_minutes"])

    while start_dt + delta <= end_dt:
        slot_start = start_dt.time()
        slot_end = (start_dt + delta).time()
        slots.append((slot_start, slot_end))
        start_dt += delta

    filtered_slots = []
    vc_start, vc_end = config["vc_slot_time"]
    
    for day in config["working_days"]:
        for start, end in slots:
            # Skip VC slots on specified days (now handled in 30-min increments)
            if day in config["vc_slot_days"] and vc_start <= start < vc_end:
                continue
            filtered_slots.append((day, start, end))

    return filtered_slots

# ==============================
# Function: Create session entries - UPDATED FOR HOURS PER WEEK LOGIC
# ==============================
def create_sessions_from_courses(courses_df):
    sessions = []
    for _, row in courses_df.iterrows():
        course_type = row['Type']
        hours_per_week = row['Hours per week']
        
        if course_type == 'Theory':
            if hours_per_week == 2:
                # Single 2-hour theory session
                sessions.append({
                    "Course_Key": row['Course_Key'],
                    "Course_Name": row['Course Name'],
                    "Instructor": row['Instructor'],
                    "Section": row['Section'],
                    "Program": row['Program'],
                    "Type": 'Theory',
                    "Duration_Slots": 4,  # 4 slots (2 hours)
                    "Hours_Per_Week": hours_per_week,
                    "Session_Number": 1
                })
            elif hours_per_week == 3:
                # Two 90-minute theory sessions
                for session_num in range(2):
                    sessions.append({
                        "Course_Key": row['Course_Key'],
                        "Course_Name": row['Course Name'],
                        "Instructor": row['Instructor'],
                        "Section": row['Section'],
                        "Program": row['Program'],
                        "Type": 'Theory',
                        "Duration_Slots": 3,  # 3 slots (90 minutes)
                        "Hours_Per_Week": hours_per_week,
                        "Session_Number": session_num + 1
                    })
            else:
                # Fallback for other hour values - treat as single session
                slots_needed = max(2, int(hours_per_week * 2))  # 2 slots per hour
                sessions.append({
                    "Course_Key": row['Course_Key'],
                    "Course_Name": row['Course Name'],
                    "Instructor": row['Instructor'],
                    "Section": row['Section'],
                    "Program": row['Program'],
                    "Type": 'Theory',
                    "Duration_Slots": slots_needed,
                    "Hours_Per_Week": hours_per_week,
                    "Session_Number": 1
                })
        
        elif course_type == 'Lab':
            # Single 3-hour lab session (regardless of hours per week)
            sessions.append({
                "Course_Key": row['Course_Key'],
                "Course_Name": row['Course Name'],
                "Instructor": row['Instructor'],
                "Section": row['Section'],
                "Program": row['Program'],
                "Type": 'Lab',
                "Duration_Slots": 6,  # 6 slots (3 hours)
                "Hours_Per_Week": hours_per_week,
                "Session_Number": 1
            })
    
    return pd.DataFrame(sessions)

# ==============================
# Enhanced Function: Generate individual with consecutive slot logic
# ==============================
def generate_individual(sessions_df, available_slots, rooms_df, max_trials=1000, show_progress=False):
    schedule = []
    forced_log = []
    missed_sessions = []
    
    lab_rooms = rooms_df[rooms_df['Type'].str.lower() == 'lab']['Rooms'].tolist()
    theory_rooms = rooms_df[rooms_df['Type'].str.lower() == 'theory']['Rooms'].tolist()
    all_rooms = rooms_df['Rooms'].tolist()
    
    # Enhanced prioritization
    def get_priority_score(session):
        score = 0
        if 'CS2' in session['Section'] or 'CS4' in session['Section']:
            score += 100
        if session['Type'] == 'Lab':
            score += 50  # Labs are harder to place
        return score
    
    sessions_df['Priority_Score'] = sessions_df.apply(get_priority_score, axis=1)
    sessions_df = sessions_df.sort_values(by='Priority_Score', ascending=False)
    
    # Track instructor daily hours
    instructor_daily_hours = {}
    
    def get_instructor_hours(instructor, day):
        return instructor_daily_hours.get(f"{instructor}_{day}", 0)
    
    def add_instructor_hours(instructor, day, hours):
        key = f"{instructor}_{day}"
        instructor_daily_hours[key] = instructor_daily_hours.get(key, 0) + hours
    
    def find_consecutive_slots(day, required_slots, available_slots, max_attempts=50):
        """Find consecutive time slots for a given day - FIXED VERSION"""
        day_slots = [(i, slot) for i, slot in enumerate(available_slots) if slot[0] == day]
        day_slots.sort(key=lambda x: x[1][1])  # Sort by start time
        
        # Find ALL possible consecutive slot combinations
        possible_starts = []
        for i in range(len(day_slots) - required_slots + 1):
            consecutive = True
            
            # Check if slots are truly consecutive
            for j in range(required_slots - 1):
                current_end = day_slots[i + j][1][2]  # End time of current slot
                next_start = day_slots[i + j + 1][1][1]  # Start time of next slot
                
                if current_end != next_start:
                    consecutive = False
                    break
            
            if consecutive:
                # Check if end time doesn't exceed daily limit
                last_slot_end = day_slots[i + required_slots - 1][1][2]
                if last_slot_end <= CONFIG["daily_end"]:
                    slot_indices = [day_slots[i + j][0] for j in range(required_slots)]
                    possible_starts.append(slot_indices)
        
        # Return a RANDOM choice from all possible starts
        if possible_starts:
            return random.choice(possible_starts)
        
        return None
    
    def check_conflicts(session, day, start_time, end_time, room):
        """Enhanced conflict checking for variable duration sessions"""
        for scheduled in schedule:
            if scheduled["Weekday"] != day:
                continue
                
            scheduled_start = datetime.strptime(scheduled["Start_Time"], "%H:%M").time()
            scheduled_end = datetime.strptime(scheduled["End_Time"], "%H:%M").time()
            
            # Check time overlap
            if not (end_time <= scheduled_start or start_time >= scheduled_end):
                # Room conflict
                if scheduled["Room"] == room:
                    return "room_conflict"
                # Instructor conflict
                if scheduled["Instructor"] == session["Instructor"]:
                    return "instructor_conflict"
                # Section conflict (students can't be in two places)
                if scheduled["Section"] == session["Section"]:
                    return "section_conflict"
        return None
    
    iterator = tqdm(sessions_df.iterrows(), total=len(sessions_df), 
                   desc="📅 Placing Sessions", unit="session") if show_progress else sessions_df.iterrows()
    
    for _, session in iterator:
        placed = False
        trials = 0
        best_attempt = None
        required_slots = session["Duration_Slots"]
        
        # Calculate session duration in hours
        session_hours = required_slots * 0.5  # 30 minutes = 0.5 hours
        
        # Try preferred placement first - FIXED VERSION
        while not placed and trials < max_trials:
            trials += 1
            
            # Select random day and try to find consecutive slots
            day = random.choice(CONFIG["working_days"])
            
            # Check instructor daily hour limits
            if get_instructor_hours(session["Instructor"], day) + session_hours > CONFIG["max_daily_hours_per_instructor"]:
                continue
            
            # Find consecutive slots for this session - now properly randomized
            slot_indices = find_consecutive_slots(day, required_slots, available_slots)
            if slot_indices is None:
                continue
            
            # Get start and end times from the selected slots
            start_time = available_slots[slot_indices[0]][1]
            end_time = available_slots[slot_indices[-1]][2]
            
            # Select appropriate room
            preferred_rooms = lab_rooms if session["Type"] == 'Lab' else theory_rooms
            if not preferred_rooms:
                preferred_rooms = all_rooms
            room = random.choice(preferred_rooms)
            
            conflict = check_conflicts(session, day, start_time, end_time, room)
            if conflict is None:
                # Successfully placed
                schedule.append({
                    **session,
                    "Weekday": day,
                    "Start_Time": start_time.strftime('%H:%M'),
                    "End_Time": end_time.strftime('%H:%M'),
                    "Room": room
                })
                add_instructor_hours(session["Instructor"], day, session_hours)
                placed = True
                continue
            
            # Store best attempt for fallback
            if best_attempt is None or conflict == "section_conflict":
                best_attempt = {
                    "day": day, "start": start_time, "end": end_time, 
                    "room": room, "conflict": conflict
                }
        
        # Fallback strategies - IMPROVED VERSION  
        if not placed:
            fallback_attempts = [
                ("preferred_room_relax_time", lab_rooms if session["Type"] == 'Lab' else theory_rooms),
                ("any_room_instructor_only", all_rooms),
                ("any_room_relaxed", all_rooms)
            ]
            
            for strategy, room_pool in fallback_attempts:
                if placed: break
                
                # Try multiple random combinations instead of sequential attempts
                for attempt in range(200):
                    day = random.choice(CONFIG["working_days"])
                    
                    # Find consecutive slots with better randomization
                    slot_indices = find_consecutive_slots(day, required_slots, available_slots)
                    if slot_indices is None:
                        continue
                        
                    start_time = available_slots[slot_indices[0]][1]
                    end_time = available_slots[slot_indices[-1]][2]
                    room = random.choice(room_pool)
                    
                    # Apply strategy-specific conflict checking
                    conflict_found = False
                    for scheduled in schedule:
                        if scheduled["Weekday"] != day:
                            continue
                        
                        scheduled_start = datetime.strptime(scheduled["Start_Time"], "%H:%M").time()
                        scheduled_end = datetime.strptime(scheduled["End_Time"], "%H:%M").time()
                        
                        if not (end_time <= scheduled_start or start_time >= scheduled_end):
                            if strategy == "any_room_relaxed":
                                # Only check instructor conflicts
                                if scheduled["Instructor"] == session["Instructor"]:
                                    conflict_found = True
                                    break
                            else:
                                # Check all conflicts except section for "any_room_instructor_only"
                                if (scheduled["Room"] == room or 
                                    scheduled["Instructor"] == session["Instructor"]):
                                    conflict_found = True
                                    break
                    
                    if not conflict_found:
                        schedule.append({
                            **session,
                            "Weekday": day,
                            "Start_Time": start_time.strftime('%H:%M'),
                            "End_Time": end_time.strftime('%H:%M'),
                            "Room": room,
                            "Forced": True,
                            "Strategy": strategy
                        })
                        
                        forced_log.append({
                            "Course": session['Course_Key'],
                            "Day": day,
                            "Start": start_time.strftime('%H:%M'),
                            "Room": room,
                            "Strategy": strategy,
                            "Relaxed": strategy == "any_room_relaxed"
                        })
                        placed = True
                        break
        
        if not placed:
            missed_sessions.append({
                "Course": session["Course_Key"],
                "Instructor": session["Instructor"],
                "Section": session["Section"],
                "Type": session["Type"],
                "Duration_Hours": session_hours,
                "Reason": f"Failed after {max_trials} trials with all fallback strategies"
            })
    
    return pd.DataFrame(schedule), forced_log, missed_sessions

# ==============================
# Function: Generate population (unchanged)
# ==============================
def generate_population(pop_size, sessions_df, available_slots, rooms_df, show_progress=False):
    population = []
    all_forced = []
    all_missed = []

    for i in range(pop_size):
        if show_progress:
            print(f"Generating individual {i+1}/{pop_size}")
        schedule, forced_log, missed_sessions = generate_individual(
            sessions_df, available_slots, rooms_df, show_progress=False
        )
        population.append(schedule)
        all_forced.extend(forced_log)
        all_missed.extend(missed_sessions)

    return population, all_forced, all_missed

# ==============================
# Enhanced Function: Calculate fitness - UPDATED FOR NEW SLOT SYSTEM
# ==============================
def calculate_fitness(individual):
    if individual.empty:
        return 1
    
    penalty = 0
    bonus = 0
    
    # Convert time strings to time objects for comparison
    individual = individual.copy()
    individual['Start_Time_obj'] = pd.to_datetime(individual['Start_Time'], format="%H:%M").dt.time
    individual['End_Time_obj'] = pd.to_datetime(individual['End_Time'], format="%H:%M").dt.time
    
    # Check conflicts and calculate penalties
    for i, row in individual.iterrows():
        overlapping = individual[
            (individual['Weekday'] == row['Weekday']) &
            (individual.index != i) &
            (individual['Start_Time_obj'] < row['End_Time_obj']) &
            (individual['End_Time_obj'] > row['Start_Time_obj'])
        ]
        
        # Conflict penalties
        instructor_conflicts = overlapping[overlapping['Instructor'] == row['Instructor']]
        room_conflicts = overlapping[overlapping['Room'] == row['Room']]
        section_conflicts = overlapping[overlapping['Section'] == row['Section']]
        
        penalty += len(instructor_conflicts) * 50  # Instructor conflicts are critical
        penalty += len(room_conflicts) * 30       # Room conflicts are serious
        penalty += len(section_conflicts) * 40    # Student conflicts are serious
        
        # Penalties for forced placements
        if 'Forced' in individual.columns and pd.notna(row.get('Forced')) and row['Forced']:
            strategy = row.get('Strategy', 'unknown')
            if strategy == "preferred_room_relax_time":
                penalty += 15  # Some compromise on timing
            elif strategy == "any_room_instructor_only":
                penalty += 10  # Room compromise
            elif strategy == "any_room_relaxed":
                penalty += 5   # More relaxation, less penalty
        
        # Evening time penalty (after 4 PM)
        if row['Start_Time_obj'] >= CONFIG["evening_penalty_threshold"]:
            penalty += 3
        
        # Bonus for proper session placement
        session_type = row.get('Type', 'Unknown')
        if session_type == 'Lab' and not row.get('Forced', False):
            bonus += 8  # Good lab placement
        elif session_type == 'Theory' and not row.get('Forced', False):
            bonus += 5  # Good theory placement
    
    # Instructor daily hour distribution bonus
    instructor_hours = {}
    for _, row in individual.iterrows():
        key = f"{row['Instructor']}_{row['Weekday']}"
        duration = row.get('Duration_Slots', 4) * 0.5  # Convert slots to hours
        instructor_hours[key] = instructor_hours.get(key, 0) + duration
    
    # Bonus for balanced instructor schedules
    for hours in instructor_hours.values():
        if 2 <= hours <= 6:  # Good daily hour range
            bonus += 3
        elif hours > 8:      # Overloaded day
            penalty += 12
    
    # Coverage bonus (more sessions scheduled = better)
    coverage_bonus = len(individual) * 3
    
    base_score = 1000
    final_score = max(1, base_score - penalty + bonus + coverage_bonus)
    
    return final_score

# ==============================
# Enhanced Function: Better crossover - UPDATED
# ==============================
def crossover(parent1, parent2):
    if parent1.empty or parent2.empty:
        return parent1.copy(), parent2.copy()
    
    # Use instructor-based crossover for better preservation of good schedules
    instructors1 = set(parent1['Instructor'].unique())
    instructors2 = set(parent2['Instructor'].unique())
    common_instructors = instructors1.intersection(instructors2)
    
    if common_instructors:
        # Split by instructor rather than random position
        split_instructor = random.choice(list(common_instructors))
        
        child1_part1 = parent1[parent1['Instructor'] <= split_instructor]
        child1_part2 = parent2[parent2['Instructor'] > split_instructor]
        
        child2_part1 = parent2[parent2['Instructor'] <= split_instructor]
        child2_part2 = parent1[parent1['Instructor'] > split_instructor]
        
        child1 = pd.concat([child1_part1, child1_part2], ignore_index=True)
        child2 = pd.concat([child2_part1, child2_part2], ignore_index=True)
    else:
        # Fallback to positional crossover
        split = len(parent1) // 2
        child1 = pd.concat([parent1.iloc[:split], parent2.iloc[split:]], ignore_index=True)
        child2 = pd.concat([parent2.iloc[:split], parent1.iloc[split:]], ignore_index=True)
    
    # Remove duplicates while preserving course session requirements
    child1 = child1.drop_duplicates(subset=["Course_Key", "Session_Number"], keep='first')
    child2 = child2.drop_duplicates(subset=["Course_Key", "Session_Number"], keep='first')
    
    return child1.reset_index(drop=True), child2.reset_index(drop=True)

# ==============================
# Enhanced Function: Better mutation - UPDATED FOR 30-MIN SLOTS
# ==============================
def mutate(individual, available_slots, rooms_df, mutation_rate=0.1):
    if individual.empty or random.random() >= mutation_rate:
        return individual
    
    individual = individual.copy()
    lab_rooms = rooms_df[rooms_df['Type'].str.lower() == 'lab']['Rooms'].tolist()
    theory_rooms = rooms_df[rooms_df['Type'].str.lower() == 'theory']['Rooms'].tolist()
    
    # Choose multiple sessions to mutate for better exploration
    num_mutations = max(1, int(len(individual) * mutation_rate))
    mutation_indices = random.sample(range(len(individual)), 
                                   min(num_mutations, len(individual)))
    
    def find_consecutive_slots_for_day(day, required_slots):
        """Helper function to find consecutive slots"""
        day_slots = [(i, slot) for i, slot in enumerate(available_slots) if slot[0] == day]
        day_slots.sort(key=lambda x: x[1][1])
        
        for i in range(len(day_slots) - required_slots + 1):
            consecutive = True
            for j in range(required_slots - 1):
                current_end = day_slots[i + j][1][2]
                next_start = day_slots[i + j + 1][1][1]
                if current_end != next_start:
                    consecutive = False
                    break
            
            if consecutive:
                return day_slots[i:i + required_slots]
        return None
    
    for idx in mutation_indices:
        session = individual.iloc[idx]
        session_type = session.get('Type', 'Theory')
        required_slots = session.get('Duration_Slots', 4)
        preferred_rooms = lab_rooms if session_type == 'Lab' else theory_rooms
        
        for _ in range(50):  # Try to find better placement
            day = random.choice(CONFIG["working_days"])
            consecutive_slots = find_consecutive_slots_for_day(day, required_slots)
            
            if consecutive_slots is None:
                continue
                
            start_time = consecutive_slots[0][1][1]
            end_time = consecutive_slots[-1][1][2]
            room = random.choice(preferred_rooms if preferred_rooms else rooms_df['Rooms'].tolist())
            
            if end_time <= CONFIG["daily_end"]:
                individual.at[idx, 'Weekday'] = day
                individual.at[idx, 'Start_Time'] = start_time.strftime('%H:%M')
                individual.at[idx, 'End_Time'] = end_time.strftime('%H:%M')
                individual.at[idx, 'Room'] = room
                
                # Remove forced flags if mutation improves placement
                if 'Forced' in individual.columns:
                    individual.at[idx, 'Forced'] = False
                if 'Strategy' in individual.columns:
                    individual.at[idx, 'Strategy'] = None
                break
    
    return individual

# ==============================
# Enhanced Function: Optimize with adaptive parameters (unchanged)
# ==============================
def optimize(population, available_slots, rooms_df, generations=100, elite_size=3, 
            mutation_rate=0.15, adaptive=True):
    best_fitness_history = []
    stagnation_counter = 0
    current_mutation_rate = mutation_rate
    
    room_list = rooms_df['Rooms'].tolist()
    
    progress_bar = tqdm(
        range(generations),
        desc="🧬 Optimizing Schedule",
        unit="gen"
    )
    
    for gen in progress_bar:
        # Calculate fitness for all individuals
        fitness_scores = [calculate_fitness(ind) for ind in population]
        best_fitness = max(fitness_scores)
        avg_fitness = np.mean(fitness_scores)
        best_fitness_history.append(best_fitness)
        
        # Update progress bar
        progress_bar.set_postfix({
            'Best': f'{best_fitness:.0f}',
            'Avg': f'{avg_fitness:.0f}',
            'MutRate': f'{current_mutation_rate:.3f}'
        })
        
        # Adaptive mutation rate
        if adaptive and gen > 0:
            if best_fitness <= best_fitness_history[-2]:
                stagnation_counter += 1
                if stagnation_counter > 10:
                    current_mutation_rate = min(0.3, current_mutation_rate * 1.1)
                    stagnation_counter = 0
            else:
                stagnation_counter = 0
                current_mutation_rate = max(0.05, current_mutation_rate * 0.95)
        
        # Selection: Elite + Tournament
        elite_indices = sorted(range(len(fitness_scores)), 
                             key=lambda i: fitness_scores[i], reverse=True)[:elite_size]
        new_population = [population[i].copy() for i in elite_indices]
        
        # Fill rest with crossover and mutation
        while len(new_population) < len(population):
            # Tournament selection
            tournament_size = 3
            parent1_idx = max(random.sample(range(len(population)), tournament_size),
                            key=lambda i: fitness_scores[i])
            parent2_idx = max(random.sample(range(len(population)), tournament_size),
                            key=lambda i: fitness_scores[i])
            
            parent1 = population[parent1_idx]
            parent2 = population[parent2_idx]
            
            child1, child2 = crossover(parent1, parent2)
            
            new_population.append(mutate(child1, available_slots, rooms_df, current_mutation_rate))
            if len(new_population) < len(population):
                new_population.append(mutate(child2, available_slots, rooms_df, current_mutation_rate))
        
        population = new_population
    
    # Return best individual
    final_scores = [calculate_fitness(ind) for ind in population]
    best_index = final_scores.index(max(final_scores))
    
    return population[best_index], final_scores[best_index], best_fitness_history

# ==============================
# Enhanced reporting functions - UPDATED
# ==============================
def format_schedule_by_day(schedule_df):
    """Enhanced schedule formatting with conflict highlighting"""
    if schedule_df.empty:
        print("❌ No schedule to display - empty DataFrame")
        return
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    for day in days:
        day_df = schedule_df[schedule_df['Weekday'] == day]
        if day_df.empty:
            continue
            
        print(f"\n📅 {day.upper()}")
        print("=" * 90)
        
        # Sort by start time
        day_df = day_df.sort_values(by='Start_Time')
        
        for _, row in day_df.iterrows():
            forced_marker = ""
            if row.get('Forced', False):
                strategy = row.get('Strategy', 'unknown')
                forced_marker = f" [FORCED:{strategy}]"
            
            type_marker = f" [{row.get('Type', 'Unknown')}]"
            duration = row.get('Duration_Slots', 4) * 0.5  # Convert to hours
            
            print(f"{row['Start_Time']}-{row['End_Time']} | "
                  f"{row['Course_Key']:<40} | "
                  f"{row['Instructor']:<20} | "
                  f"{row['Room']:<10} | "
                  f"{duration}h"
                  f"{type_marker}{forced_marker}")

def analyze_schedule_quality(schedule_df, sessions_df):
    """Comprehensive schedule analysis - UPDATED FOR HOURS PER WEEK"""
    print("\n📊 SCHEDULE QUALITY ANALYSIS")
    print("=" * 50)
    
    total_expected = len(sessions_df)
    total_scheduled = len(schedule_df)
    coverage = (total_scheduled / total_expected * 100) if total_expected > 0 else 0
    
    print(f"📈 Coverage: {total_scheduled}/{total_expected} sessions ({coverage:.1f}%)")
    
    if not schedule_df.empty:
        # Session type and duration breakdown
        type_breakdown = schedule_df['Type'].value_counts()
        print(f"\n📚 Session Types:")
        for session_type, count in type_breakdown.items():
            total_hours = schedule_df[schedule_df['Type'] == session_type]['Duration_Slots'].sum() * 0.5
            print(f"   - {session_type}: {count} sessions ({total_hours:.1f}h total)")
        
        # Duration distribution
        duration_dist = schedule_df['Duration_Slots'].value_counts().sort_index()
        print(f"\n⏱️ Session Duration Distribution:")
        for slots, count in duration_dist.items():
            hours = slots * 0.5
            if slots == 3:
                print(f"   - {hours}h (90 min): {count} sessions")
            elif slots == 4:
                print(f"   - {hours}h (2 hour): {count} sessions")  
            elif slots == 6:
                print(f"   - {hours}h (3 hour labs): {count} sessions")
            else:
                print(f"   - {hours}h: {count} sessions")
        
        # Forced placements analysis
        forced_count = len(schedule_df[schedule_df.get('Forced', False) == True])
        if forced_count > 0:
            print(f"\n⚠️  Forced placements: {forced_count}")
            
            if 'Strategy' in schedule_df.columns:
                strategies = schedule_df[schedule_df.get('Forced', False) == True]['Strategy'].value_counts()
                for strategy, count in strategies.items():
                    print(f"   - {strategy}: {count}")
        
        # Instructor workload
        instructor_sessions = schedule_df['Instructor'].value_counts()
        print(f"\n👥 Instructor workload (top 5):")
        for instructor, count in instructor_sessions.head().items():
            total_hours = schedule_df[schedule_df['Instructor'] == instructor]['Duration_Slots'].sum() * 0.5
            print(f"   - {instructor}: {count} sessions ({total_hours:.1f}h total)")
        
        # Room utilization
        room_usage = schedule_df['Room'].value_counts()
        print(f"\n🏢 Room utilization (top 5):")
        for room, count in room_usage.head().items():
            total_hours = schedule_df[schedule_df['Room'] == room]['Duration_Slots'].sum() * 0.5
            print(f"   - {room}: {count} sessions ({total_hours:.1f}h total)")
        
        # Time distribution
        print(f"\n⏰ Time slot distribution:")
        time_dist = schedule_df['Start_Time'].value_counts().sort_index()
        for time_slot, count in time_dist.head(10).items():
            print(f"   - {time_slot}: {count} sessions")

def check_long_sessions(df):
    """Check for sessions exceeding expected duration"""
    problematic_sessions = []
    for _, row in df.iterrows():
        start = datetime.strptime(row["Start_Time"], "%H:%M")
        end = datetime.strptime(row["End_Time"], "%H:%M")
        duration = (end - start).seconds / 60
        expected_duration = row.get('Duration_Slots', 4) * 30  # 30 minutes per slot
        
        if abs(duration - expected_duration) > 5:  # Allow 5-minute tolerance
            problematic_sessions.append((
                row["Course_Key"], row["Weekday"], 
                row["Start_Time"], row["End_Time"], 
                duration, expected_duration
            ))
    return problematic_sessions

def export_schedule_by_section(schedule_df, output_dir="exports"):
    """Export schedules grouped by section"""
    
    if schedule_df.empty:
        print("No schedule data to export")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    sections = schedule_df['Section'].unique()
    
    for section in sections:
        section_df = schedule_df[schedule_df['Section'] == section]
        filename = f"{output_dir}/schedule_{section}.csv"
        section_df.to_csv(filename, index=False)
        print(f"📄 Exported {section} schedule to {filename}")
    
    # Also export master schedule
    master_filename = f"{output_dir}/master_schedule.csv"
    schedule_df.to_csv(master_filename, index=False)
    print(f"📄 Exported master schedule to {master_filename}")

def export_schedule_by_teacher(schedule_df, output_dir="exports/teachers"):
    """Export schedules grouped by teacher"""

    if schedule_df.empty:
        print("No schedule data to export")
        return

    os.makedirs(output_dir, exist_ok=True)

    teachers = schedule_df['Instructor'].unique()
    
    for teacher in teachers:
        safe_teacher = str(teacher).replace(" ", "_").replace("/", "_")
        teacher_df = schedule_df[schedule_df['Instructor'] == teacher]
        filename = f"{output_dir}/schedule_{safe_teacher}.csv"
        teacher_df.to_csv(filename, index=False)
        print(f"📄 Exported {teacher} schedule to {filename}")

    # Master schedule (optional)
    master_filename = f"{output_dir}/../master_schedule_teachers.csv"
    schedule_df.to_csv(master_filename, index=False)
    print(f"📄 Exported teacher master schedule to {master_filename}")

def export_schedule_by_room(schedule_df, output_dir="exports/rooms"):
    """Export schedules grouped by room"""

    if schedule_df.empty:
        print("No schedule data to export")
        return

    os.makedirs(output_dir, exist_ok=True)

    rooms = schedule_df['Room'].unique()
    
    for room in rooms:
        safe_room = str(room).replace(" ", "_").replace("/", "_")
        room_df = schedule_df[schedule_df['Room'] == room]
        filename = f"{output_dir}/schedule_{safe_room}.csv"
        room_df.to_csv(filename, index=False)
        print(f"📄 Exported {room} schedule to {filename}")

    # Master schedule (optional)
    master_filename = f"{output_dir}/../master_schedule_rooms.csv"
    schedule_df.to_csv(master_filename, index=False)
    print(f"📄 Exported room master schedule to {master_filename}")