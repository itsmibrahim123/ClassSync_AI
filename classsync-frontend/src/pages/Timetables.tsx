import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
    Calendar,
    Download,
    Trash2,
    Eye,
    Clock,
    CheckCircle,
    AlertCircle,
    Loader2,
    Edit2,
    Save,
    FileText,
    FileSpreadsheet,
    Sparkles,
    Plus
} from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { timetablesApi } from '@/lib/api'
import { formatDateTime } from '@/lib/utils'
import { useM365Layout } from '@/contexts/M365LayoutContext'
import { PageHeader } from '@/components/layout/PageHeader'

export function Timetables() {
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const { setPageTitle, setBreadcrumbs, setPrimaryAction, setCommandBarActions } = useM365Layout()
    const [editingId, setEditingId] = useState<number | null>(null)
    const [editingName, setEditingName] = useState('')
    const [activeMenu, setActiveMenu] = useState<number | null>(null)

    // Configure layout
    useEffect(() => {
        setPageTitle('Timetables')
        setBreadcrumbs([
            { label: 'Dashboard', href: '/' },
            { label: 'Timetables' },
        ])
        setPrimaryAction({
            id: 'generate-new',
            label: 'Generate New',
            icon: <Plus className="h-4 w-4" />,
            onClick: () => navigate('/generate'),
        })
        setCommandBarActions([])

        return () => {
            setCommandBarActions([])
            setPrimaryAction(null)
        }
    }, [setPageTitle, setBreadcrumbs, setPrimaryAction, setCommandBarActions, navigate])

    // Fetch timetables
    const { data: timetables, isLoading } = useQuery({
        queryKey: ['timetables'],
        queryFn: () => timetablesApi.list().then(res => res.data),
    })

    // Delete mutation
    const deleteMutation = useMutation({
        mutationFn: (id: number) => timetablesApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['timetables'] })
        },
    })

    // Rename mutation
    const renameMutation = useMutation({
        mutationFn: ({ id, name }: { id: number; name: string }) => 
            timetablesApi.update(id, name),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['timetables'] })
            setEditingId(null)
            setEditingName('')
        },
    })

    // Export mutation
    const exportMutation = useMutation({
        mutationFn: ({ id, format }: { id: number; format: string }) =>
            timetablesApi.export(id, format, 'master'),
        onSuccess: (response, variables) => {
            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]))
            const link = document.createElement('a')
            link.href = url
            link.setAttribute('download', `timetable_${variables.id}.${variables.format}`)
            document.body.appendChild(link)
            link.click()
            link.remove()
            setActiveMenu(null)
        },
    })

    const handleGenerate = () => {
        navigate('/generate')
    }

    const handleDelete = (id: number) => {
        if (confirm('Delete this timetable? This action cannot be undone.')) {
            deleteMutation.mutate(id)
        }
    }

    const startEditing = (timetable: any) => {
        setEditingId(timetable.id)
        setEditingName(timetable.name)
    }

    const saveRename = (id: number) => {
        if (editingName.trim()) {
            renameMutation.mutate({ id, name: editingName })
        }
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-300">
            {/* Page Header */}
            <PageHeader
                title="Timetables"
                subtitle="View and manage your generated schedules."
            />

            {/* Timetables Grid */}
            {isLoading ? (
                <div className="flex items-center justify-center py-24">
                    <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" />
                </div>
            ) : timetables && timetables.length > 0 ? (
                <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                    {timetables.map((timetable: any) => (
                        <Card key={timetable.id} className="group relative overflow-hidden transition-all hover:shadow-xl hover:-translate-y-1 border-border/60">
                            <CardHeader className="pb-3">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            {editingId === timetable.id ? (
                                                <div className="flex items-center gap-1 flex-1">
                                                    <Input
                                                        value={editingName}
                                                        onChange={(e) => setEditingName(e.target.value)}
                                                        className="h-8 text-sm"
                                                        autoFocus
                                                        onKeyDown={(e) => {
                                                            if (e.key === 'Enter') saveRename(timetable.id)
                                                            if (e.key === 'Escape') setEditingId(null)
                                                        }}
                                                    />
                                                    <Button size="icon" variant="ghost" className="h-8 w-8 text-green-600" onClick={() => saveRename(timetable.id)}>
                                                        <Save className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-2 group/title">
                                                    <h3 className="font-semibold text-lg truncate cursor-pointer hover:text-primary transition-colors" onClick={() => navigate(`/timetables/${timetable.id}`)}>
                                                        {timetable.name}
                                                    </h3>
                                                    <Button 
                                                        size="icon" 
                                                        variant="ghost" 
                                                        className="h-6 w-6 opacity-0 group-hover/title:opacity-100 transition-opacity"
                                                        onClick={() => startEditing(timetable)}
                                                    >
                                                        <Edit2 className="h-3 w-3 text-muted-foreground" />
                                                    </Button>
                                                </div>
                                            )}
                                        </div>
                                        <p className="text-sm text-muted-foreground mt-1">
                                            {timetable.semester} {timetable.year}
                                        </p>
                                    </div>
                                    <div className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                                        timetable.status === 'COMPLETED' ? 'bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-900' :
                                        timetable.status === 'FAILED' ? 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-900' :
                                        'bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-900'
                                    }`}>
                                        {timetable.status}
                                    </div>
                                </div>
                            </CardHeader>
                            
                            <CardContent>
                                <div className="grid grid-cols-2 gap-y-4 gap-x-2 mb-6">
                                    <div className="flex items-center gap-2.5">
                                        <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                                            <CheckCircle className="h-4 w-4" />
                                        </div>
                                        <div>
                                            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Score</p>
                                            <p className="font-medium text-sm">{timetable.constraint_score}%</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2.5">
                                        <div className="p-1.5 rounded-md bg-destructive/10 text-destructive">
                                            <AlertCircle className="h-4 w-4" />
                                        </div>
                                        <div>
                                            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Conflicts</p>
                                            <p className="font-medium text-sm">{timetable.conflict_count}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2.5">
                                        <div className="p-1.5 rounded-md bg-secondary/10 text-secondary">
                                            <Clock className="h-4 w-4" />
                                        </div>
                                        <div>
                                            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Duration</p>
                                            <p className="font-medium text-sm">{timetable.generation_time_seconds.toFixed(1)}s</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2.5">
                                        <div className="p-1.5 rounded-md bg-muted text-muted-foreground">
                                            <Calendar className="h-4 w-4" />
                                        </div>
                                        <div>
                                            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Created</p>
                                            <p className="font-medium text-sm truncate">{formatDateTime(timetable.created_at).split(',')[0]}</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 pt-4 border-t border-border/50">
                                    <Button
                                        className="flex-1"
                                        variant="default"
                                        size="sm"
                                        onClick={() => navigate(`/timetables/${timetable.id}`)}
                                    >
                                        <Eye className="mr-2 h-4 w-4" />
                                        View
                                    </Button>
                                    
                                    <div className="relative">
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            className="h-9 w-9"
                                            onClick={() => setActiveMenu(activeMenu === timetable.id ? null : timetable.id)}
                                        >
                                            <Download className="h-4 w-4" />
                                        </Button>
                                        
                                        {activeMenu === timetable.id && (
                                            <>
                                                <div className="fixed inset-0 z-10" onClick={() => setActiveMenu(null)} />
                                                <div className="absolute right-0 bottom-10 w-40 bg-popover border border-border shadow-lg rounded-lg p-1 z-20 flex flex-col gap-1 animate-in zoom-in-95 duration-200">
                                                    <button 
                                                        className="flex items-center gap-2 w-full px-3 py-2 text-sm text-left hover:bg-muted rounded-md transition-colors"
                                                        onClick={() => exportMutation.mutate({ id: timetable.id, format: 'xlsx' })}
                                                    >
                                                        <FileSpreadsheet className="h-4 w-4 text-green-600" />
                                                        Export XLSX
                                                    </button>
                                                    <button 
                                                        className="flex items-center gap-2 w-full px-3 py-2 text-sm text-left hover:bg-muted rounded-md transition-colors"
                                                        onClick={() => exportMutation.mutate({ id: timetable.id, format: 'csv' })}
                                                    >
                                                        <FileText className="h-4 w-4 text-blue-600" />
                                                        Export CSV
                                                    </button>
                                                </div>
                                            </>
                                        )}
                                    </div>

                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-9 w-9 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                                        onClick={() => handleDelete(timetable.id)}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-20 text-center bg-muted/20 border-2 border-dashed border-muted-foreground/20 rounded-3xl">
                    <div className="bg-background p-6 rounded-full shadow-sm mb-6">
                        <Calendar className="h-12 w-12 text-primary/60" />
                    </div>
                    <h3 className="text-xl font-semibold">No timetables generated yet</h3>
                    <p className="text-muted-foreground text-base max-w-sm mt-2 mb-8">
                        Upload your data and start the optimization engine to create your first conflict-free schedule.
                    </p>
                    <Button onClick={handleGenerate} size="lg" className="shadow-lg">
                        <Sparkles className="mr-2 h-4 w-4" />
                        Generate First Timetable
                    </Button>
                </div>
            )}
            
        </div>
    )
}