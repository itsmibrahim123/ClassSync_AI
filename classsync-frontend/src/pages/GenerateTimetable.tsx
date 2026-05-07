import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
    Lock,
    Unlock,
    Sliders,
    Clock,
    User,
    Trash2,
    Plus,
    Settings2,
    ChevronUp,
    ChevronDown,
    Database,
    AlertCircle,
    Loader2,
    Sparkles,
    MoreVertical,
    Save,
    Check
} from 'lucide-react'
import { useM365Layout } from '@/contexts/M365LayoutContext'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { 
    DropdownMenu, 
    DropdownMenuContent, 
    DropdownMenuItem, 
    DropdownMenuLabel, 
    DropdownMenuSeparator, 
    DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { timetablesApi, constraintsApi, teachersApi, datasetsApi, teacherConstraintsApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { TeacherConstraint, ConstraintType, Teacher, ConstraintConfig } from '@/types'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
const TIME_SLOTS = [
    '08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
    '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30',
    '16:00', '16:30', '17:00', '17:30', '18:00'
]

const CONSTRAINT_TYPES: { value: ConstraintType; label: string; description: string }[] = [
    { value: 'blocked_slot', label: 'Blocked Slot', description: 'Teacher is unavailable at this time' },
    { value: 'day_off', label: 'Day Off', description: 'Teacher wants this day off' },
    { value: 'available_window', label: 'Available Window', description: 'Teacher is only available during this time' },
    { value: 'preferred_slot', label: 'Preferred Slot', description: 'Teacher prefers this time slot' },
]

// Validation types
interface ValidationError {
    type: 'error' | 'warning'
    message: string
    details?: string
}

// Time helper functions
function timeToMinutes(time: string | undefined | null): number {
    if (!time || typeof time !== 'string') return 0
    try {
        const parts = time.split(':')
        if (parts.length !== 2) return 0
        const [hours, minutes] = parts.map(Number)
        if (isNaN(hours) || isNaN(minutes)) return 0
        return hours * 60 + minutes
    } catch (e) {
        return 0
    }
}

function slotsOverlap(start1: string, end1: string, start2: string, end2: string): boolean {
    const s1 = timeToMinutes(start1)
    const e1 = timeToMinutes(end1)
    const s2 = timeToMinutes(start2)
    const e2 = timeToMinutes(end2)
    // Ensure valid ranges
    if (s1 >= e1 || s2 >= e2) return false
    return s1 < e2 && s2 < e1
}

export function GenerateTimetable() {
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const { setPageTitle, setBreadcrumbs, setPrimaryAction, setCommandBarActions } = useM365Layout()

    // State for constraint configuration
    const [selectedConfigId, setSelectedConfigId] = useState<number | null>(null)
    const [teacherConstraints, setTeacherConstraints] = useState<TeacherConstraint[]>([])
    const [showAddConstraint, setShowAddConstraint] = useState(false)
    const [expandedSections, setExpandedSections] = useState({
        constraints: true,
        settings: false,
    })

    // Form state for adding constraints
    const [newConstraint, setNewConstraint] = useState<Partial<TeacherConstraint>>({
        teacher_id: 0,
        constraint_type: 'blocked_slot',
        is_hard: false,
        weight: 5,
        day: 'Monday',
        start_time: '09:00',
        end_time: '12:00',
    })

    // Profile Management State
    const [selectedProfileId, setSelectedProfileId] = useState<string>("")
    const [profileDialogOpen, setProfileDialogOpen] = useState(false)
    const [profileForm, setProfileForm] = useState({
        name: "",
        description: "",
        is_default: false
    })

    // Fetch profiles
    const { data: teacherProfiles } = useQuery({
        queryKey: ['teacher-profiles'],
        queryFn: () => teacherConstraintsApi.list().then(res => res.data)
    })

    // Fetch full profile details
    const loadProfileMutation = useMutation({
        mutationFn: (id: number) => teacherConstraintsApi.get(id),
        onSuccess: (response) => {
            const profile = response.data
            // Map items back to TeacherConstraint format
            const mappedConstraints: TeacherConstraint[] = profile.items.map((item: any) => ({
                teacher_id: item.teacher_id,
                constraint_type: item.constraint_type === "Blocked Slot" ? "blocked_slot" 
                    : item.constraint_type === "Preferred Slot" ? "preferred_slot" 
                    : "blocked_slot", // Default fallback
                is_hard: item.priority === "hard",
                weight: 5, // Default weight as it's not in profile item schema
                day: DAYS.find(d => d.startsWith(item.day)) || item.day, // Map Mon -> Monday
                start_time: item.start_time,
                end_time: item.end_time
            }))
            setTeacherConstraints(mappedConstraints)
            // Show banner or toast (using simple alert for now or implement banner)
        }
    })

    // Save Profile Mutation
    const saveProfileMutation = useMutation({
        mutationFn: (data: any) => teacherConstraintsApi.create(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['teacher-profiles'] })
            setProfileDialogOpen(false)
            setProfileForm({ name: "", description: "", is_default: false })
            alert("Profile saved successfully!")
        }
    })

    // Delete Profile Mutation
    const deleteProfileMutation = useMutation({
        mutationFn: (id: number) => teacherConstraintsApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['teacher-profiles'] })
            if (selectedProfileId) setSelectedProfileId("")
        }
    })

    // Set Default Mutation
    const setDefaultProfileMutation = useMutation({
        mutationFn: (id: number) => teacherConstraintsApi.setDefault(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['teacher-profiles'] })
        }
    })

    // Handle Profile Selection
    const handleProfileSelect = (value: string) => {
        setSelectedProfileId(value)
        if (value) {
            loadProfileMutation.mutate(parseInt(value))
        }
    }

    const handleSaveProfile = () => {
        if (!profileForm.name) return
        
        // Map current constraints to Profile Item format
        const items = teacherConstraints.map(c => ({
            teacher_id: c.teacher_id,
            day: c.day ? c.day.substring(0, 3) : "Mon", // Map Monday -> Mon
            start_time: c.start_time || "09:00",
            end_time: c.end_time || "10:00",
            constraint_type: c.constraint_type === "blocked_slot" ? "Blocked Slot" : "Preferred Slot",
            priority: c.is_hard ? "hard" : "soft"
        }))

        saveProfileMutation.mutate({
            name: profileForm.name,
            description: profileForm.description,
            is_default: profileForm.is_default,
            items: items
        })
    }

    // Auto-load default profile on mount if no constraints
    useState(() => {
        // This runs once on mount/init logic
        if (teacherConstraints.length === 0 && teacherProfiles) {
            const defaultProfile = teacherProfiles.find((p: any) => p.is_default)
            if (defaultProfile) {
                handleProfileSelect(defaultProfile.id.toString())
            }
        }
    })

    // Optimization settings
    const [settings, setSettings] = useState({
        population_size: 30,
        generations: 100,
        target_fitness: 85,
        random_seed: undefined as number | undefined,
    })

    // Validation function for constraints
    const validateConstraints = (): ValidationError[] => {
        try {
            const errors: ValidationError[] = []
            const config = selectedConfig || defaultConfig

            // Group constraints by teacher
            const constraintsByTeacher = new Map<number, TeacherConstraint[]>()
            teacherConstraints.forEach(c => {
                const existing = constraintsByTeacher.get(c.teacher_id) || []
                constraintsByTeacher.set(c.teacher_id, [...existing, c])
            })

            // Check each teacher's constraints
            constraintsByTeacher.forEach((constraints, teacherId) => {
                const teacherName = getTeacherNameById(teacherId)

                // Get blocked slots for this teacher
                const blockedSlots = constraints.filter(c =>
                    c.constraint_type === 'blocked_slot' && c.day && c.start_time && c.end_time
                )

                // Get day-offs for this teacher
                const dayOffs = constraints.filter(c => c.constraint_type === 'day_off')
                const dayOffDays = new Set<string>()
                dayOffs.forEach(d => {
                    if (d.days) d.days.forEach(day => dayOffDays.add(day))
                    if (d.day) dayOffDays.add(d.day)
                })

                // 1. Check for overlapping blocked slots on the same day
                for (let i = 0; i < blockedSlots.length; i++) {
                    for (let j = i + 1; j < blockedSlots.length; j++) {
                        const slot1 = blockedSlots[i]
                        const slot2 = blockedSlots[j]

                        if (slot1.day === slot2.day &&
                            slotsOverlap(slot1.start_time!, slot1.end_time!, slot2.start_time!, slot2.end_time!)) {
                            errors.push({
                                type: 'warning',
                                message: `Overlapping blocked slots for ${teacherName}`,
                                details: `${slot1.day}: ${slot1.start_time}-${slot1.end_time} overlaps with ${slot2.start_time}-${slot2.end_time}`
                            })
                        }
                    }
                }

                // 2. Check for blocked slot on day-off (redundant)
                blockedSlots.forEach(slot => {
                    if (slot.day && dayOffDays.has(slot.day)) {
                        errors.push({
                            type: 'warning',
                            message: `Redundant blocked slot for ${teacherName}`,
                            details: `${slot.day} is already a day-off, blocked slot is unnecessary`
                        })
                    }
                })

                // 3. Check if time slots are within institution hours
                if (config && config.start_time && config.end_time) {
                    try {
                        const dayStart = timeToMinutes(config.start_time)
                        const dayEnd = timeToMinutes(config.end_time)

                        blockedSlots.forEach(slot => {
                            if (slot.start_time && slot.end_time) {
                                const slotStart = timeToMinutes(slot.start_time)
                                const slotEnd = timeToMinutes(slot.end_time)

                                if (slotStart < dayStart) {
                                    errors.push({
                                        type: 'warning',
                                        message: `Blocked slot starts before institution hours`,
                                        details: `${teacherName}: ${slot.start_time} is before ${config.start_time}`
                                    })
                                }
                                if (slotEnd > dayEnd) {
                                    errors.push({
                                        type: 'warning',
                                        message: `Blocked slot ends after institution hours`,
                                        details: `${teacherName}: ${slot.end_time} is after ${config.end_time}`
                                    })
                                }
                                if (slotStart >= slotEnd) {
                                    errors.push({
                                        type: 'error',
                                        message: `Invalid time range for ${teacherName}`,
                                        details: `Start time ${slot.start_time} must be before end time ${slot.end_time}`
                                    })
                                }
                            }
                        })
                    } catch (e) {
                        // Ignore parsing errors
                    }
                }
            })

            return errors
        } catch (error) {
            console.error("Validation error:", error)
            return []
        }
    }

    // Helper to get teacher name by ID
    const getTeacherNameById = (id: number) => {
        const teacher = teachers?.find((t: Teacher) => t.id === id)
        return teacher?.name || `Teacher ${id}`
    }

    // Calculate validation errors
    const validationErrors = validateConstraints()
    const hasErrors = validationErrors.some(e => e.type === 'error')

    // Fetch data
    const { data: constraintConfigs } = useQuery({
        queryKey: ['constraintConfigs'],
        queryFn: () => constraintsApi.list().then(res => res.data),
    })

    const { data: teachers } = useQuery({
        queryKey: ['teachers'],
        queryFn: () => teachersApi.list().then(res => res.data),
    })

    const { data: datasets } = useQuery({
        queryKey: ['datasets'],
        queryFn: () => datasetsApi.list().then(res => res.data),
    })

    // Check if datasets are available
    const hasDatasets = datasets && datasets.length > 0

    const generateMutation = useMutation({
        mutationFn: () => timetablesApi.generate({
            constraint_config_id: selectedConfigId || undefined,
            teacher_constraints: teacherConstraints,
            room_constraints: [],
            locked_assignments: [],
            population_size: settings.population_size,
            generations: settings.generations,
            target_fitness: settings.target_fitness,
            random_seed: settings.random_seed,
        }),
        onSuccess: (response) => {
            queryClient.invalidateQueries({ queryKey: ['timetables'] })
            navigate(`/timetables/${response.data.timetable_id}`)
        },
    })

    // Configure layout - only run once on mount
    useEffect(() => {
        setPageTitle('Generate Timetable')
        setBreadcrumbs([
            { label: 'Dashboard', href: '/' },
            { label: 'Generate' },
        ])

        return () => {
            setCommandBarActions([])
            setPrimaryAction(null)
        }
    }, [setPageTitle, setBreadcrumbs, setCommandBarActions, setPrimaryAction])

    // Update command bar actions when relevant state changes
    useEffect(() => {
        setCommandBarActions([
            {
                id: 'save-profile',
                label: 'Save Profile',
                icon: <Save className="h-4 w-4" />,
                onClick: () => setProfileDialogOpen(true),
                disabled: teacherConstraints.length === 0,
            },
        ])
    }, [setCommandBarActions, teacherConstraints.length])

    // Update primary action separately to avoid stale closures
    useEffect(() => {
        setPrimaryAction({
            id: 'generate',
            label: generateMutation.isPending ? 'Generating...' : 'Generate Timetable',
            icon: generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />,
            onClick: () => generateMutation.mutate(),
            disabled: !hasDatasets || generateMutation.isPending || hasErrors,
        })
    }, [setPrimaryAction, hasDatasets, generateMutation.isPending, hasErrors])

    // Handlers
    const handleAddConstraint = () => {
        if (!newConstraint.teacher_id) return

        const constraint: TeacherConstraint = {
            teacher_id: newConstraint.teacher_id!,
            constraint_type: newConstraint.constraint_type as ConstraintType,
            is_hard: newConstraint.is_hard || false,
            weight: newConstraint.weight || 5,
            day: newConstraint.constraint_type === 'day_off' ? undefined : newConstraint.day,
            days: newConstraint.constraint_type === 'day_off' ? [newConstraint.day!] : undefined,
            start_time: ['blocked_slot', 'available_window', 'preferred_slot'].includes(newConstraint.constraint_type!)
                ? newConstraint.start_time : undefined,
            end_time: ['blocked_slot', 'available_window', 'preferred_slot'].includes(newConstraint.constraint_type!)
                ? newConstraint.end_time : undefined,
        }

        setTeacherConstraints([...teacherConstraints, constraint])
        setShowAddConstraint(false)
        setNewConstraint({
            teacher_id: 0,
            constraint_type: 'blocked_slot',
            is_hard: false,
            weight: 5,
            day: 'Monday',
            start_time: '09:00',
            end_time: '12:00',
        })
    }

    const handleRemoveConstraint = (index: number) => {
        setTeacherConstraints(teacherConstraints.filter((_, i) => i !== index))
    }

    const getTeacherName = (id: number) => getTeacherNameById(id)

    const selectedConfig = constraintConfigs?.find((c: ConstraintConfig) => c.id === selectedConfigId)
    const defaultConfig = constraintConfigs?.find((c: ConstraintConfig) => c.is_default)

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            {/* Header */}
            <PageHeader
                title="Generate Timetable"
                subtitle="Configure scheduling parameters and run the AI optimizer."
            >
                {!hasDatasets && (
                    <Button variant="outline" size="sm" onClick={() => navigate('/upload')}>
                        Upload Data
                    </Button>
                )}
            </PageHeader>

            {/* Top Grid: Profile & Status */}
            <div className="grid gap-6 md:grid-cols-12">
                {/* Constraint Profile Selection */}
                <div className="md:col-span-8">
                    <Card className="h-full border-border/60 shadow-sm">
                        <CardHeader className="pb-3 border-b border-border/40 bg-muted/5">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-base font-semibold flex items-center gap-2">
                                    <Sliders className="h-4 w-4 text-muted-foreground" />
                                    Constraint Profile
                                </CardTitle>
                                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => navigate('/settings')}>
                                    Manage Profiles
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent className="pt-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {constraintConfigs?.map((config: ConstraintConfig) => (
                                    <div
                                        key={config.id}
                                        className={cn(
                                            "cursor-pointer rounded-lg border p-3 transition-all hover:bg-muted/50 flex flex-col justify-between gap-2",
                                            selectedConfigId === config.id || (!selectedConfigId && config.is_default)
                                                ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                                : "border-border/60"
                                        )}
                                        onClick={() => setSelectedConfigId(config.id)}
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium text-sm">{config.name}</span>
                                            {config.is_default && (
                                                <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full uppercase font-bold tracking-wider">
                                                    Default
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Clock className="h-3 w-3" /> {config.start_time}-{config.end_time}
                                            </span>
                                            <span>{config.days_per_week} Days</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Dataset Status */}
                <div className="md:col-span-4">
                    <Card className={cn(
                        "h-full border-2 shadow-sm flex flex-col justify-center",
                        hasDatasets ? "border-green-500/20 bg-green-50/50 dark:bg-green-900/10" : "border-amber-500/20 bg-amber-50/50 dark:bg-amber-900/10"
                    )}>
                        <CardContent className="flex flex-col items-center text-center p-6 gap-3">
                            <div className={cn(
                                "p-3 rounded-full",
                                hasDatasets ? "bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400" : "bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"
                            )}>
                                {hasDatasets ? <Database className="h-6 w-6" /> : <AlertCircle className="h-6 w-6" />}
                            </div>
                            <div>
                                <p className="font-semibold text-base">
                                    {hasDatasets ? 'Data Ready' : 'Data Missing'}
                                </p>
                                <p className="text-xs text-muted-foreground mt-1 max-w-[200px] mx-auto">
                                    {hasDatasets 
                                        ? `${datasets.length} active datasets available for processing.`
                                        : 'Upload course and room data to begin.'}
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Main Configuration Area */}
            <div className="grid gap-6 md:grid-cols-12 items-start">
                
                {/* Left: Teacher Constraints (Main Focus) */}
                <div className="md:col-span-8 space-y-6">
                    <Card className="border-border/60 shadow-sm overflow-hidden">
                        <CardHeader className="py-4 px-6 border-b bg-muted/5 flex flex-row items-center justify-between">
                            <div className="flex items-center gap-4">
                                <CardTitle className="text-base font-semibold flex items-center gap-2">
                                    <User className="h-4 w-4 text-muted-foreground" />
                                    Teacher Constraints
                                </CardTitle>
                                <span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-1 rounded-full">
                                    {teacherConstraints.length} active
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <select 
                                    className="h-8 w-[160px] rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                    value={selectedProfileId}
                                    onChange={(e) => handleProfileSelect(e.target.value)}
                                >
                                    <option value="">Load Profile...</option>
                                    {teacherProfiles?.map((p: any) => (
                                        <option key={p.id} value={p.id}>
                                            {p.name} {p.is_default ? '(Default)' : ''}
                                        </option>
                                    ))}
                                </select>

                                <Button 
                                    variant="outline" 
                                    size="icon" 
                                    className="h-8 w-8"
                                    title="Save as Profile"
                                    onClick={() => setProfileDialogOpen(true)}
                                    disabled={teacherConstraints.length === 0}
                                >
                                    <Save className="h-4 w-4" />
                                </Button>

                                {selectedProfileId && (
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" size="icon" className="h-8 w-8">
                                                <MoreVertical className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuLabel>Profile Actions</DropdownMenuLabel>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem onClick={() => setDefaultProfileMutation.mutate(parseInt(selectedProfileId))}>
                                                <Check className="mr-2 h-4 w-4" /> Set as Default
                                            </DropdownMenuItem>
                                            <DropdownMenuItem className="text-destructive" onClick={() => {
                                                if(confirm('Delete this profile?')) deleteProfileMutation.mutate(parseInt(selectedProfileId))
                                            }}>
                                                <Trash2 className="mr-2 h-4 w-4" /> Delete Profile
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                )}
                            </div>
                        </CardHeader>
                        
                        <CardContent className="p-6 space-y-6">
                            {/* Constraints List */}
                            {teacherConstraints.length > 0 ? (
                                <div className="space-y-3">
                                    {teacherConstraints.map((constraint, index) => (
                                        <div
                                            key={index}
                                            className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/5 transition-colors group"
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className={cn(
                                                    "p-2 rounded-md",
                                                    constraint.is_hard ? "bg-red-100 text-red-600" : "bg-yellow-100 text-yellow-600"
                                                )}>
                                                    {constraint.is_hard ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />}
                                                </div>
                                                <div>
                                                    <p className="font-medium text-sm text-foreground">
                                                        {getTeacherName(constraint.teacher_id)}
                                                    </p>
                                                    <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                                        <span className="font-semibold text-primary/80">
                                                            {CONSTRAINT_TYPES.find(t => t.value === constraint.constraint_type)?.label}
                                                        </span>
                                                        <span>•</span>
                                                        <span>
                                                            {constraint.day || (constraint.days ? constraint.days.join(', ') : 'All Days')} 
                                                            {constraint.start_time ? ` (${constraint.start_time}-${constraint.end_time})` : ''}
                                                        </span>
                                                    </p>
                                                </div>
                                            </div>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                                                onClick={() => handleRemoveConstraint(index)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-xl bg-muted/5">
                                    <p className="text-sm">No custom constraints added</p>
                                    <p className="text-xs mt-1 opacity-70">Teachers will be scheduled based on standard rules</p>
                                </div>
                            )}

                            {/* Add Constraint Form */}
                            {showAddConstraint ? (
                                <div className="bg-muted/30 p-4 rounded-xl border border-border/60 animate-in fade-in zoom-in-95 duration-200">
                                    <h4 className="text-sm font-semibold mb-4 flex items-center gap-2">
                                        <Plus className="h-4 w-4" /> New Constraint
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-medium text-muted-foreground">Teacher</label>
                                            <select
                                                className="w-full h-9 px-3 rounded-md border bg-background text-sm focus:ring-1 focus:ring-primary"
                                                value={newConstraint.teacher_id}
                                                onChange={(e) => setNewConstraint({
                                                    ...newConstraint,
                                                    teacher_id: parseInt(e.target.value)
                                                })}
                                            >
                                                <option value={0}>Select teacher...</option>
                                                {teachers?.map((teacher: Teacher) => (
                                                    <option key={teacher.id} value={teacher.id}>
                                                        {teacher.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-medium text-muted-foreground">Type</label>
                                            <select
                                                className="w-full h-9 px-3 rounded-md border bg-background text-sm focus:ring-1 focus:ring-primary"
                                                value={newConstraint.constraint_type}
                                                onChange={(e) => setNewConstraint({
                                                    ...newConstraint,
                                                    constraint_type: e.target.value as ConstraintType
                                                })}
                                            >
                                                {CONSTRAINT_TYPES.map((type) => (
                                                    <option key={type.value} value={type.value}>
                                                        {type.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-medium text-muted-foreground">Day</label>
                                            <select
                                                className="w-full h-9 px-3 rounded-md border bg-background text-sm focus:ring-1 focus:ring-primary"
                                                value={newConstraint.day}
                                                onChange={(e) => setNewConstraint({
                                                    ...newConstraint,
                                                    day: e.target.value
                                                })}
                                            >
                                                {DAYS.map((day) => (
                                                    <option key={day} value={day}>{day}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-medium text-muted-foreground">Priority</label>
                                            <div className="flex bg-background rounded-md border p-1 h-9">
                                                <button
                                                    type="button"
                                                    className={cn(
                                                        "flex-1 text-xs font-medium rounded transition-all",
                                                        newConstraint.is_hard
                                                            ? "bg-red-100 text-red-700 shadow-sm"
                                                            : "text-muted-foreground hover:bg-muted"
                                                    )}
                                                    onClick={() => setNewConstraint({ ...newConstraint, is_hard: true })}
                                                >
                                                    Hard
                                                </button>
                                                <button
                                                    type="button"
                                                    className={cn(
                                                        "flex-1 text-xs font-medium rounded transition-all",
                                                        !newConstraint.is_hard
                                                            ? "bg-yellow-100 text-yellow-700 shadow-sm"
                                                            : "text-muted-foreground hover:bg-muted"
                                                    )}
                                                    onClick={() => setNewConstraint({ ...newConstraint, is_hard: false })}
                                                >
                                                    Soft
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Time Slots (Conditional) */}
                                    {['blocked_slot', 'available_window', 'preferred_slot'].includes(newConstraint.constraint_type!) && (
                                        <div className="grid grid-cols-2 gap-4 mb-4 pt-4 border-t border-dashed border-border/60">
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-medium text-muted-foreground">Start Time</label>
                                                <select
                                                    className="w-full h-9 px-3 rounded-md border bg-background text-sm"
                                                    value={newConstraint.start_time}
                                                    onChange={(e) => setNewConstraint({ ...newConstraint, start_time: e.target.value })}
                                                >
                                                    {TIME_SLOTS.map((time) => (
                                                        <option key={time} value={time}>{time}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-medium text-muted-foreground">End Time</label>
                                                <select
                                                    className="w-full h-9 px-3 rounded-md border bg-background text-sm"
                                                    value={newConstraint.end_time}
                                                    onChange={(e) => setNewConstraint({ ...newConstraint, end_time: e.target.value })}
                                                >
                                                    {TIME_SLOTS.map((time) => (
                                                        <option key={time} value={time}>{time}</option>
                                                    ))}
                                                </select>
                                            </div>
                                        </div>
                                    )}

                                    <div className="flex justify-end gap-2">
                                        <Button size="sm" variant="ghost" onClick={() => setShowAddConstraint(false)}>
                                            Cancel
                                        </Button>
                                        <Button size="sm" onClick={handleAddConstraint} disabled={!newConstraint.teacher_id}>
                                            Add
                                        </Button>
                                    </div>
                                </div>
                            ) : (
                                <Button
                                    variant="outline"
                                    className="w-full border-dashed text-muted-foreground hover:text-primary hover:border-primary/50"
                                    onClick={() => setShowAddConstraint(true)}
                                >
                                    <Plus className="h-4 w-4 mr-2" /> Add Constraint
                                </Button>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Right: Optimization Settings (Collapsible/Compact) */}
                <div className="md:col-span-4 space-y-6">
                    <Card className="border-border/60 shadow-sm">
                        <CardHeader 
                            className="py-4 px-6 border-b bg-muted/5 cursor-pointer hover:bg-muted/10 transition-colors"
                            onClick={() => setExpandedSections(s => ({ ...s, settings: !s.settings }))}
                        >
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-base font-semibold flex items-center gap-2">
                                    <Settings2 className="h-4 w-4 text-muted-foreground" />
                                    Optimizer Settings
                                </CardTitle>
                                {expandedSections.settings ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                            </div>
                        </CardHeader>
                        {expandedSections.settings && (
                            <CardContent className="p-6 space-y-5 animate-in slide-in-from-top-2 duration-200">
                                <div className="space-y-3">
                                    <div className="flex justify-between">
                                        <label className="text-sm font-medium">Population Size</label>
                                        <span className="text-xs font-mono bg-muted px-1.5 rounded">{settings.population_size}</span>
                                    </div>
                                    <Input
                                        type="range"
                                        min={10}
                                        max={100}
                                        className="h-2"
                                        value={settings.population_size}
                                        onChange={(e) => setSettings({ ...settings, population_size: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between">
                                        <label className="text-sm font-medium">Generations</label>
                                        <span className="text-xs font-mono bg-muted px-1.5 rounded">{settings.generations}</span>
                                    </div>
                                    <Input
                                        type="range"
                                        min={50}
                                        max={300}
                                        className="h-2"
                                        value={settings.generations}
                                        onChange={(e) => setSettings({ ...settings, generations: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between">
                                        <label className="text-sm font-medium">Target Fitness</label>
                                        <span className="text-xs font-mono bg-muted px-1.5 rounded">{settings.target_fitness}%</span>
                                    </div>
                                    <Input
                                        type="range"
                                        min={50}
                                        max={100}
                                        className="h-2"
                                        value={settings.target_fitness}
                                        onChange={(e) => setSettings({ ...settings, target_fitness: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="pt-2 border-t border-border/40">
                                    <label className="text-xs font-medium text-muted-foreground mb-1.5 block">Random Seed</label>
                                    <Input
                                        type="number"
                                        placeholder="e.g. 42 (Optional)"
                                        className="h-8 text-xs"
                                        value={settings.random_seed || ''}
                                        onChange={(e) => setSettings({ ...settings, random_seed: e.target.value ? parseInt(e.target.value) : undefined })}
                                    />
                                </div>
                            </CardContent>
                        )}
                        {!expandedSections.settings && (
                            <div className="px-6 py-3 bg-muted/5 text-xs text-muted-foreground flex justify-between">
                                <span>{settings.generations} gens</span>
                                <span>Pop: {settings.population_size}</span>
                            </div>
                        )}
                    </Card>

                    {/* Validation Summary (Compact) */}
                    {validationErrors.length > 0 && (
                        <Card className={cn(
                            "border-l-4 shadow-sm",
                            hasErrors ? "border-l-destructive" : "border-l-yellow-500"
                        )}>
                            <CardContent className="p-4">
                                <div className="flex items-start gap-3">
                                    {hasErrors ? <AlertCircle className="h-5 w-5 text-destructive shrink-0" /> : <AlertCircle className="h-5 w-5 text-yellow-500 shrink-0" />}
                                    <div>
                                        <p className="font-semibold text-sm mb-1">
                                            {hasErrors ? 'Configuration Errors' : 'Warnings Detected'}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {validationErrors.length} issue(s) found. 
                                            {hasErrors && " Generation is blocked."}
                                        </p>
                                        <ul className="mt-2 space-y-1">
                                            {validationErrors.slice(0, 3).map((err, i) => (
                                                <li key={i} className="text-xs truncate max-w-[250px] list-disc ml-4">
                                                    {err.message}
                                                </li>
                                            ))}
                                            {validationErrors.length > 3 && <li className="text-xs text-muted-foreground">+ {validationErrors.length - 3} more</li>}
                                        </ul>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>

            {/* Error Toast */}
            {generateMutation.isError && (
                <div className="fixed bottom-6 right-6 w-full max-w-md z-50 animate-in slide-in-from-right duration-300">
                    <div className="bg-destructive text-destructive-foreground shadow-lg rounded-lg p-4 flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                        <div className="text-sm">
                            <p className="font-semibold">Generation Failed</p>
                            <p className="opacity-90 mt-1">
                                {((generateMutation.error as any)?.response?.data?.detail?.message) || 'An unexpected error occurred.'}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Loading Toast */}
            {generateMutation.isPending && (
                <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-right duration-300">
                    <div className="bg-primary text-primary-foreground shadow-lg rounded-lg p-4 flex items-center gap-3">
                        <Loader2 className="h-5 w-5 animate-spin" />
                        <div className="text-sm">
                            <p className="font-semibold">Generating Timetable...</p>
                            <p className="opacity-90 text-xs">AI is optimizing your schedule</p>
                        </div>
                    </div>
                </div>
            )}

            <Dialog open={profileDialogOpen} onOpenChange={setProfileDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Save Constraint Profile</DialogTitle>
                        <DialogDescription>
                            Save current teacher constraints as a reusable profile.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Profile Name</label>
                            <Input 
                                placeholder="e.g. Standard Fall Constraints" 
                                value={profileForm.name}
                                onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Description (Optional)</label>
                            <Input 
                                placeholder="Brief description..." 
                                value={profileForm.description}
                                onChange={(e) => setProfileForm({ ...profileForm, description: e.target.value })}
                            />
                        </div>
                        <div className="flex items-center gap-2">
                            <input 
                                type="checkbox" 
                                id="is_default"
                                className="h-4 w-4 rounded border-gray-300"
                                checked={profileForm.is_default}
                                onChange={(e) => setProfileForm({ ...profileForm, is_default: e.target.checked })}
                            />
                            <label htmlFor="is_default" className="text-sm font-medium">Set as default profile</label>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setProfileDialogOpen(false)}>Cancel</Button>
                        <Button onClick={handleSaveProfile} disabled={!profileForm.name || saveProfileMutation.isPending}>
                            {saveProfileMutation.isPending ? "Saving..." : "Save Profile"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}