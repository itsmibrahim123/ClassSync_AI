from enhanced_timetable_optimizer import *
import matplotlib.pyplot as plt
import os

def main():
    print("🎓 ENHANCED UNIVERSITY TIMETABLE OPTIMIZER")
    print("=" * 50)
    
    # Load data
    print("📂 Loading course and room data...")
    courses_df, rooms_df = load_course_and_room_data("Courses_Processed.csv", "Rooms.csv")
    sessions_df = create_sessions_from_courses(courses_df)
    slots = generate_time_slots(CONFIG)
    
    print(f"✅ Loaded {len(courses_df)} courses, {len(sessions_df)} sessions")
    print(f"✅ Generated {len(slots)} available time slots")
    print(f"✅ Found {len(rooms_df)} rooms: {len(rooms_df[rooms_df['Type'].str.lower() == 'lab'])} labs, "
          f"{len(rooms_df[rooms_df['Type'].str.lower() == 'theory'])} theory rooms")
    
    # Generate population
    print(f"\n🧬 Generating population of 30 individuals...")
    population, all_forced, all_missed = generate_population(
        30, sessions_df, slots, rooms_df, show_progress=True
    )
    
    print(f"📊 Population statistics:")
    print(f"   - Average sessions per individual: {np.mean([len(ind) for ind in population]):.1f}")
    print(f"   - Total forced placements: {len(all_forced)}")
    print(f"   - Total missed sessions: {len(all_missed)}")
    
    # Run optimization
    print(f"\n🚀 Starting genetic algorithm optimization...")
    best_schedule, best_score, history = optimize(
        population, slots, rooms_df, 
        generations=100,        # Increased generations
        elite_size=3,          # Slightly more elites
        mutation_rate=0.15,    # Higher initial mutation rate
        adaptive=True          # Enable adaptive mutation
    )
    
    print(f"\n🎯 OPTIMIZATION COMPLETE!")
    print(f"   - Best fitness score: {best_score}")
    print(f"   - Sessions scheduled: {len(best_schedule)}/{len(sessions_df)}")
    
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    # Analyze schedule quality
    analyze_schedule_quality(best_schedule, sessions_df)
    
    # Check for scheduling issues
    print(f"\n🔍 CHECKING FOR ISSUES...")
    
    # Check for missed sessions
    scheduled_keys = set(best_schedule['Course_Key'] + " - Session " + best_schedule.get('Session_Number', 1).astype(str))
    expected_keys = set(sessions_df['Course_Key'] + " - Session " + sessions_df['Session_Number'].astype(str))
    missing_keys = expected_keys - scheduled_keys
    
    if missing_keys:
        print(f"\n❌ {len(missing_keys)} course sessions were NOT scheduled:")
        missing_by_section = {}
        for key in sorted(missing_keys):
            section = key.split(" - ")[-2] if " - " in key else "Unknown"
            missing_by_section[section] = missing_by_section.get(section, 0) + 1
            print(f"  - {key}")
        
        print(f"\n📊 Missing sessions by section:")
        for section, count in sorted(missing_by_section.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {section}: {count} sessions")
    else:
        print(f"\n✅ All course sessions were successfully scheduled!")
    
    # Check for long sessions
    overlong = check_long_sessions(best_schedule)
    if overlong:
        print(f"\n⚠️  Sessions exceeding 3 hours detected:")
        for course, day, start, end, duration in overlong:
            print(f"   - {course} on {day} from {start} to {end} ({duration:.0f} minutes)")
    else:
        print(f"\n✅ No sessions exceed 3 hours")
    
    # Save detailed logs
    print(f"\n💾 SAVING RESULTS...")
    
    # Save forced placements log
    with open("output/forced_placements_log.txt", "w", encoding="utf-8") as f:
        f.write("FORCED PLACEMENT LOG\n")
        f.write("=" * 50 + "\n\n")
        for log in all_forced:
            label = "[RELAXED]" if log.get("Relaxed") else "[FORCED]"
            strategy = f" ({log.get('Strategy', 'unknown')})" if log.get('Strategy') else ""
            f.write(f"{log['Course']} → {log['Day']} at {log['Start']} in {log['Room']} {label}{strategy}\n")
    
    # Save missed sessions log
    with open("output/missed_sessions_log.txt", "w", encoding="utf-8") as f:
        f.write("MISSED SESSIONS LOG\n")
        f.write("=" * 50 + "\n\n")
        for session in all_missed:
            f.write(f"[!] Could not place: {session['Course']} (Section: {session.get('Section', 'N/A')})\n")
            f.write(f"    Instructor: {session.get('Instructor', 'N/A')}\n")
            f.write(f"    Type: {'Lab' if session.get('Is_Lab') else 'Theory'}\n")
            f.write(f"    Reason: {session['Reason']}\n\n")
    
    # Save unscheduled courses
    with open("output/unscheduled_courses.txt", "w", encoding="utf-8") as f:
        f.write("UNSCHEDULED SESSIONS\n")
        f.write("=" * 50 + "\n\n")
        for key in sorted(missing_keys):
            f.write(f"{key}\n")
    
    # Export schedules by section
    print(f"📤 Exporting section-wise schedules...")
    export_schedule_by_section(best_schedule, "output/sections")

    # Export teacher-wise timetables
    print(f"📤 Exporting teacher-wise schedules...")
    export_schedule_by_teacher(best_schedule, "output/teachers")
    
    # Export schedules by room
    print(f"📤 Exporting room-wise schedules...")
    export_schedule_by_room(best_schedule, "output/rooms")

    
    # Save fitness history plot
    plt.figure(figsize=(12, 6))
    plt.plot(history, linewidth=2, color='blue')
    plt.title('Genetic Algorithm Fitness Evolution', fontsize=14, fontweight='bold')
    plt.xlabel('Generation')
    plt.ylabel('Best Fitness Score')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('output/fitness_evolution.png', dpi=300, bbox_inches='tight')
    print(f"📊 Saved fitness evolution plot to output/fitness_evolution.png")
    
    # Display final schedule
    print(f"\n📅 FINAL OPTIMIZED SCHEDULE:")
    print("=" * 80)
    format_schedule_by_day(best_schedule)
    
    # Generate summary report
    generate_summary_report(best_schedule, sessions_df, history, all_forced, all_missed)
    
    print(f"\n🎉 OPTIMIZATION COMPLETE! Check the 'output' directory for detailed results.")

def generate_summary_report(schedule_df, sessions_df, history, forced_log, missed_sessions):
    """Generate a comprehensive summary report"""
    
    with open("output/summary_report.txt", "w", encoding="utf-8") as f:
        f.write("UNIVERSITY TIMETABLE OPTIMIZATION REPORT\n")
        f.write("=" * 60 + "\n\n")
        
        # Overall Statistics
        f.write("OVERALL STATISTICS\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total Expected Sessions: {len(sessions_df)}\n")
        f.write(f"Successfully Scheduled: {len(schedule_df)}\n")
        f.write(f"Coverage Rate: {(len(schedule_df)/len(sessions_df)*100):.1f}%\n")
        f.write(f"Final Fitness Score: {history[-1] if history else 'N/A'}\n")
        f.write(f"Generations Run: {len(history) if history else 'N/A'}\n\n")
        
        # Forced Placements Summary
        f.write("FORCED PLACEMENTS SUMMARY\n")
        f.write("-" * 30 + "\n")
        if forced_log:
            strategies = {}
            for log in forced_log:
                strategy = log.get('Strategy', 'unknown')
                strategies[strategy] = strategies.get(strategy, 0) + 1
            
            f.write(f"Total Forced Placements: {len(forced_log)}\n")
            for strategy, count in strategies.items():
                f.write(f"  - {strategy}: {count}\n")
        else:
            f.write("No forced placements required!\n")
        f.write("\n")
        
        # Missed Sessions Summary
        f.write("MISSED SESSIONS SUMMARY\n")
        f.write("-" * 30 + "\n")
        if missed_sessions:
            f.write(f"Total Missed Sessions: {len(missed_sessions)}\n")
            
            # Group by section
            section_misses = {}
            lab_misses = 0
            theory_misses = 0
            
            for session in missed_sessions:
                section = session.get('Section', 'Unknown')
                section_misses[section] = section_misses.get(section, 0) + 1
                if session.get('Is_Lab'):
                    lab_misses += 1
                else:
                    theory_misses += 1
            
            f.write(f"  - Lab sessions missed: {lab_misses}\n")
            f.write(f"  - Theory sessions missed: {theory_misses}\n\n")
            f.write("By Section:\n")
            for section, count in sorted(section_misses.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  - {section}: {count} sessions\n")
        else:
            f.write("All sessions successfully scheduled!\n")
        f.write("\n")
        
        # Resource Utilization
        if not schedule_df.empty:
            f.write("RESOURCE UTILIZATION\n")
            f.write("-" * 30 + "\n")
            
            # Room utilization
            room_usage = schedule_df['Room'].value_counts()
            f.write(f"Room Utilization (Total rooms used: {len(room_usage)}):\n")
            for room, count in room_usage.head(10).items():
                f.write(f"  - {room}: {count} sessions\n")
            f.write("\n")
            
            # Instructor workload
            instructor_load = schedule_df['Instructor'].value_counts()
            f.write(f"Instructor Workload (Total instructors: {len(instructor_load)}):\n")
            for instructor, count in instructor_load.head(10).items():
                f.write(f"  - {instructor}: {count} sessions\n")
            f.write("\n")
            
            # Daily distribution
            daily_dist = schedule_df['Weekday'].value_counts()
            f.write("Daily Session Distribution:\n")
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                count = daily_dist.get(day, 0)
                f.write(f"  - {day}: {count} sessions\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("Report generated by Enhanced Timetable Optimizer\n")
    
    print("📋 Summary report saved to output/summary_report.txt")

if __name__ == "__main__":
    main()