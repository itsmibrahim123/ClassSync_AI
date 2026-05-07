export interface Dataset {
    id: number
    institution_id: number
    dataset_type: string
    file_name: string
    file_path: string
    file_size: number
    row_count: number
    validation_status: string
    validation_errors: string[] | null
    uploaded_by: number
    created_at: string
    updated_at: string
}

export interface Timetable {
    id: number
    institution_id: number
    name: string
    semester: string
    year: number
    status: string
    generation_time_seconds: number
    constraint_score: number
    conflict_count: number
    generated_by: number
    created_at: string
    updated_at: string
}

export interface TimetableEntry {
    id: number
    timetable_id: number
    section_id: number
    course_id: number
    teacher_id: number
    room_id: number
    day_of_week: number
    start_time: string
    end_time: string
    created_at: string
    updated_at: string
}

export interface ConstraintConfig {
    id: number
    institution_id: number
    name: string
    is_active: boolean
    is_default: boolean
    timeslot_duration_minutes: number
    days_per_week: number
    start_time: string
    end_time: string
    hard_constraints: Record<string, any>
    soft_constraints: Record<string, any>
    optional_constraints: Record<string, any>
    created_at: string
    updated_at: string
}

// Teacher types
export interface Teacher {
    id: number
    code: string
    name: string
    email?: string
    department?: string
    time_preferences?: Record<string, any>
    created_at?: string
}

// Constraint types for Generate Timetable
export type ConstraintType = 'blocked_slot' | 'day_off' | 'available_window' | 'preferred_slot'

export interface TeacherConstraint {
    teacher_id: number
    constraint_type: ConstraintType
    is_hard: boolean
    weight: number // 1-10 for soft constraints
    day?: string // For single-day constraints: "Monday", "Tuesday", etc.
    days?: string[] // For multi-day constraints like day_off: ["Friday", "Saturday"]
    start_time?: string // "09:00"
    end_time?: string // "12:00"
}

export interface RoomConstraint {
    room_id: number
    constraint_type: ConstraintType
    is_hard: boolean
    day?: string
    days?: string[]
    start_time?: string
    end_time?: string
    reason?: string
}

export type LockType = 'time_only' | 'full_lock'

export interface LockedAssignment {
    session_key: string
    course_id: number
    section_id: number
    teacher_id: number
    day: string
    start_time: string
    room_id?: number
    lock_type: LockType
}

export interface GenerateRequest {
    constraint_config_id?: number
    teacher_constraints: TeacherConstraint[]
    room_constraints: RoomConstraint[]
    locked_assignments: LockedAssignment[]
    population_size: number
    generations: number
    target_fitness: number
    random_seed?: number
}

export interface GenerateResponse {
    message: string
    timetable_id: number
    generation_time: number
    sessions_scheduled: number
    sessions_total: number
    fitness_score: number
    hard_violations?: Record<string, number>
    soft_scores?: Record<string, number>
    constraints_applied?: {
        teacher_constraints: number
        room_constraints: number
        locked_assignments: number
    }
}

// Room type for room constraints
export interface Room {
    id: number
    code: string
    name?: string
    room_type: string
    capacity?: number
    building?: string
    is_available: boolean
}

// Course and Section for locked assignments
export interface Course {
    id: number
    code: string
    name: string
    course_type: string
    credit_hours?: number
    teacher_id: number
}

export interface Section {
    id: number
    code: string
    name?: string
    course_id: number
    semester: string
    year: number
    student_count?: number
}