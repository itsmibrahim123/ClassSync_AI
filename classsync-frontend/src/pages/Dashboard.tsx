import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Calendar, Upload, Clock, CheckCircle, PieChart, ArrowRight, Plus, Activity, RefreshCw } from 'lucide-react'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { timetablesApi, dashboardApi, healthApi } from '@/lib/api'
import { formatDateTime, formatDate } from '@/lib/utils'
import { useM365Layout } from '@/contexts/M365LayoutContext'

export function Dashboard() {
    const navigate = useNavigate()
    const { setPageTitle, setBreadcrumbs, setPrimaryAction, setCommandBarActions } = useM365Layout()

    // Configure layout
    useEffect(() => {
        setPageTitle('Dashboard')
        setBreadcrumbs([{ label: 'Dashboard' }])
        setPrimaryAction({
            id: 'new-schedule',
            label: 'New Schedule',
            icon: <Plus className="h-4 w-4" />,
            onClick: () => navigate('/generate'),
        })
        setCommandBarActions([
            {
                id: 'refresh',
                label: 'Refresh',
                icon: <RefreshCw className="h-4 w-4" />,
                onClick: () => window.location.reload(),
            },
        ])

        return () => {
            setCommandBarActions([])
            setPrimaryAction(null)
        }
    }, [setPageTitle, setBreadcrumbs, setPrimaryAction, setCommandBarActions, navigate])

    // Fetch dashboard stats
    const { data: stats } = useQuery({
        queryKey: ['dashboard-stats'],
        queryFn: () => dashboardApi.stats().then(res => res.data),
    })

    // Fetch recent timetables
    const { data: timetables } = useQuery({
        queryKey: ['timetables'],
        queryFn: () => timetablesApi.list().then(res => res.data),
    })

    // Fetch System Health
    const { data: health, isLoading: isHealthLoading } = useQuery({
        queryKey: ['health'],
        queryFn: () => healthApi.check().then(res => res.data),
        refetchInterval: 30000,
    })

    const isApiOperational = health?.components?.api === 'operational'
    const isDbOperational = health?.components?.database === 'operational'

    const getGreeting = () => {
        const hour = new Date().getHours()
        if (hour < 12) return 'Good morning'
        if (hour < 18) return 'Good afternoon'
        return 'Good evening'
    }

    const totalStatus = stats?.total_timetables || 1

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500 pb-8">
            {/* 1. Compact Banner */}
            <div className="relative overflow-hidden rounded-lg bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border border-border px-6 py-5">
                <div className="relative z-10">
                    <h1 className="text-xl font-semibold tracking-tight text-foreground">
                        {getGreeting()}, Admin
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1">
                        {formatDate(new Date())} • System Optimized
                    </p>
                </div>
            </div>

            {/* 2. Compact Stats Grid (Restored Details) */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatsCard
                    title="Total Timetables"
                    value={stats?.total_timetables || 0}
                    icon={Calendar}
                    color="blue"
                    description="Generated Schedules"
                    trend={{ value: 12, isPositive: true }}
                />
                <StatsCard
                    title="Data Sources"
                    value={stats?.total_datasets || 0}
                    icon={Upload}
                    color="purple"
                    description="Courses & Rooms"
                    trend={{ value: 5, isPositive: true }}
                />
                <StatsCard
                    title="Active Schedules"
                    value={stats?.active_schedules || 0}
                    icon={CheckCircle}
                    color="green"
                    description="Deployed & Ready"
                    trend={{ value: 100, isPositive: true }}
                />
                <StatsCard
                    title="Avg. Runtime"
                    value={`${stats?.avg_generation_time || 0}s`}
                    icon={Clock}
                    color="coral"
                    description="Optimization Cycle"
                    trend={{ value: 8, isPositive: false }}
                />
            </div>

            {/* 3. Main Content Area */}
            <div className="grid gap-6 md:grid-cols-12 items-start">
                
                {/* Recent Activity - Takes 8 columns */}
                <Card className="md:col-span-8 border-border/60 shadow-sm">
                    <CardHeader className="flex flex-row items-center justify-between py-4 px-6 border-b bg-muted/10">
                        <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-muted-foreground" />
                            <CardTitle className="text-base font-semibold">Recent Activity</CardTitle>
                        </div>
                        <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-primary" onClick={() => navigate('/timetables')}>
                            View All <ArrowRight className="ml-1 h-3 w-3" />
                        </Button>
                    </CardHeader>
                    <CardContent className="p-0">
                        {timetables && timetables.length > 0 ? (
                            <div className="divide-y divide-border/40">
                                {timetables.slice(0, 5).map((timetable: any) => (
                                    <div
                                        key={timetable.id}
                                        className="group flex items-center justify-between p-4 hover:bg-muted/30 transition-colors cursor-pointer"
                                        onClick={() => navigate(`/timetables/${timetable.id}`)}
                                    >
                                        <div className="flex items-center gap-3 min-w-0">
                                            <div className={`shrink-0 w-2 h-2 rounded-full ${
                                                timetable.status === 'COMPLETED' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' :
                                                timetable.status === 'FAILED' ? 'bg-red-500' : 'bg-yellow-500'
                                            }`} />
                                            <div className="min-w-0 truncate">
                                                <p className="font-medium text-sm truncate">{timetable.name}</p>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <span>{timetable.semester} {timetable.year}</span>
                                                    <span>•</span>
                                                    <span>{formatDateTime(timetable.created_at)}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3 shrink-0">
                                            <div className="text-right">
                                                <span className="text-xs font-medium bg-secondary/20 text-secondary-foreground px-2 py-0.5 rounded-full">
                                                    {timetable.conflict_count} conflicts
                                                </span>
                                            </div>
                                            <ArrowRight className="h-3 w-3 text-muted-foreground/50 opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-center p-6 text-muted-foreground">
                                <Calendar className="h-8 w-8 mb-2 opacity-20" />
                                <p className="text-sm">No timetables generated yet</p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Right Sidebar - Takes 4 columns */}
                <div className="md:col-span-4 flex flex-col gap-6">
                    
                    {/* Status Overview */}
                    <Card className="border-border/60 shadow-sm">
                        <CardHeader className="py-4 px-6 border-b bg-muted/10">
                            <CardTitle className="text-sm font-semibold flex items-center gap-2">
                                <PieChart className="h-4 w-4 text-muted-foreground" />
                                Status Overview
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-6 flex flex-col gap-4">
                            {stats ? (
                                <>
                                    {['completed', 'pending', 'failed'].map((status) => {
                                        const count = stats.status_distribution[status as keyof typeof stats.status_distribution];
                                        const color = status === 'completed' ? 'bg-green-500' : status === 'pending' ? 'bg-yellow-500' : 'bg-red-500';
                                        return (
                                            <div key={status} className="space-y-1.5">
                                                <div className="flex justify-between text-xs font-medium">
                                                    <span className="capitalize text-muted-foreground">{status}</span>
                                                    <span>{count}</span>
                                                </div>
                                                <div className="h-2 w-full bg-muted/60 rounded-full overflow-hidden">
                                                    <div 
                                                        className={`h-full rounded-full ${color}`} 
                                                        style={{ width: `${(count / totalStatus) * 100}%` }}
                                                    />
                                                </div>
                                            </div>
                                        )
                                    })}
                                </>
                            ) : (
                                <div className="text-center text-xs text-muted-foreground">Loading...</div>
                            )}
                        </CardContent>
                    </Card>

                    {/* System Health */}
                    <Card className="border-border/60 shadow-sm">
                        <CardHeader className="py-4 px-6 border-b bg-muted/10">
                            <CardTitle className="text-sm font-semibold flex items-center gap-2">
                                <Activity className="h-4 w-4 text-muted-foreground" />
                                System Health
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-6 flex flex-col gap-4">
                            {/* Optimizer */}
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className={`h-2.5 w-2.5 rounded-full ${isApiOperational ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]' : 'bg-red-500'}`} />
                                    <span className="text-xs font-medium">Optimizer Engine</span>
                                </div>
                                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${isApiOperational ? 'bg-green-500/10 text-green-600 border-green-500/20' : 'bg-red-500/10 text-red-600 border-red-500/20'}`}>
                                    {isHealthLoading ? '...' : (isApiOperational ? 'Operational' : 'Offline')}
                                </span>
                            </div>

                            {/* Database */}
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className={`h-2.5 w-2.5 rounded-full ${isDbOperational ? 'bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]' : 'bg-red-500'}`} />
                                    <span className="text-xs font-medium">Database</span>
                                </div>
                                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${isDbOperational ? 'bg-green-500/10 text-green-600 border-green-500/20' : 'bg-red-500/10 text-red-600 border-red-500/20'}`}>
                                    {isHealthLoading ? '...' : (isDbOperational ? 'Connected' : 'Error')}
                                </span>
                            </div>

                            {/* Data Readiness */}
                            <div className="flex items-center justify-between pt-2 border-t border-border/40 mt-1">
                                <span className="text-xs font-medium text-muted-foreground">Data Readiness</span>
                                <span className={`text-[10px] font-semibold ${stats && stats.total_datasets > 0 ? 'text-green-600' : 'text-amber-500'}`}>
                                    {stats && stats.total_datasets > 0 ? 'Ready' : 'Pending Upload'}
                                </span>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}