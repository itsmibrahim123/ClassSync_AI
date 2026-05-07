import { useState, useEffect, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileUpload } from '@/components/upload/FileUpload'
import { DataPreviewModal } from '@/components/datasets/DataPreviewModal'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from '@/components/ui/button'
import { datasetsApi } from '@/lib/api'
import { formatDateTime } from '@/lib/utils'
import { Trash2, CheckCircle, XCircle, LibraryBig, School, Database, FileSpreadsheet, Download, Info } from 'lucide-react'
import { useM365Layout } from '@/contexts/M365LayoutContext'
import { PageHeader } from '@/components/layout/PageHeader'

export function Upload() {
    const queryClient = useQueryClient()
    const { setPageTitle, setBreadcrumbs, setPrimaryAction, setCommandBarActions } = useM365Layout()

    const [uploadStatus, setUploadStatus] = useState<{
        success: boolean
        message: string
    } | null>(null)
    const [previewOpen, setPreviewOpen] = useState(false)
    const [previewDataset, setPreviewDataset] = useState<{ id: number, file_name: string } | null>(null)
    const [datasetToDelete, setDatasetToDelete] = useState<{ id: number, file_name: string } | null>(null)

    // Template download function
    const downloadTemplate = useCallback((type: 'courses' | 'rooms') => {
        let content = ''
        let filename = ''

        if (type === 'courses') {
            content = 'course_name,instructor,section,program,type,hours_per_week\nCalculus I,Dr. Smith,A,CS,Theory,3\nPhysics Lab,Prof. Doe,A,CS,Lab,3'
            filename = 'courses_template.csv'
        } else {
            content = 'room_name,type,capacity\nRoom 101,Theory,50\nLab 1,Lab,30'
            filename = 'rooms_template.csv'
        }

        const blob = new Blob([content], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
    }, [])

    // Configure layout
    useEffect(() => {
        setPageTitle('Data Management')
        setBreadcrumbs([
            { label: 'Dashboard', href: '/' },
            { label: 'Upload Datasets' },
        ])
        setPrimaryAction({
            id: 'download-templates',
            label: 'Download Templates',
            icon: <Download className="h-4 w-4" />,
            dropdown: [
                {
                    id: 'courses-template',
                    label: 'Courses Template',
                    icon: <LibraryBig className="h-4 w-4 text-blue-500" />,
                    onClick: () => downloadTemplate('courses'),
                },
                {
                    id: 'rooms-template',
                    label: 'Rooms Template',
                    icon: <School className="h-4 w-4 text-orange-500" />,
                    onClick: () => downloadTemplate('rooms'),
                },
            ],
        })
        setCommandBarActions([])

        return () => {
            setCommandBarActions([])
            setPrimaryAction(null)
        }
    }, [setPageTitle, setBreadcrumbs, setPrimaryAction, setCommandBarActions, downloadTemplate])

    // Fetch existing datasets
    const { data: datasets } = useQuery({
        queryKey: ['datasets'],
        queryFn: () => datasetsApi.list().then(res => res.data),
    })

    // Upload mutation
    const uploadMutation = useMutation({
        mutationFn: ({ file, type }: { file: File; type: string }) =>
            datasetsApi.upload(file, type),
        onSuccess: (response) => {
            queryClient.invalidateQueries({ queryKey: ['datasets'] })
            setUploadStatus({
                success: true,
                message: `Successfully uploaded ${response.data.file_name}`,
            })
            setTimeout(() => setUploadStatus(null), 5000)
        },
        onError: (error: any) => {
            setUploadStatus({
                success: false,
                message: error.response?.data?.detail || 'Upload failed',
            })
            setTimeout(() => setUploadStatus(null), 5000)
        },
    })

    // Delete mutation
    const deleteMutation = useMutation({
        mutationFn: (id: number) => datasetsApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['datasets'] })
            setDatasetToDelete(null)
        },
    })

    const handleUpload = (file: File, type: string) => {
        uploadMutation.mutate({ file, type })
    }

    return (
        <div className="flex flex-col space-y-6 animate-in fade-in duration-300 pb-2">
            {/* Header */}
            <PageHeader
                title="Data Management"
                subtitle="Upload your institutional data for scheduling."
            />

            {/* Upload Status Toast */}
            {uploadStatus && (
                <div className={`fixed bottom-6 right-6 z-50 p-4 rounded-xl shadow-lg border flex items-center gap-3 animate-in slide-in-from-right duration-300 ${
                    uploadStatus.success 
                        ? 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/30 dark:border-green-900/50 dark:text-green-300' 
                        : 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-900/50 dark:text-red-300'
                }`}>
                    {uploadStatus.success ? (
                        <CheckCircle className="h-5 w-5" />
                    ) : (
                        <XCircle className="h-5 w-5" />
                    )}
                    <p className="font-medium text-sm">{uploadStatus.message}</p>
                </div>
            )}

            {/* Main Content Grid */}
            <div className="flex-1 min-h-0 flex flex-col gap-6">
                
                {/* Top Row: Upload & Guidelines (Equal Height) */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[420px] shrink-0 relative z-10">
                    {/* Left: Upload Component */}
                    <div className="lg:col-span-7 h-full">
                        <FileUpload
                            onUpload={handleUpload}
                            isUploading={uploadMutation.isPending}
                            className="h-full shadow-sm"
                        />
                    </div>

                    {/* Right: Guidelines */}
                    <Card className="lg:col-span-5 h-full shadow-sm flex flex-col bg-muted/10 border-muted-foreground/20">
                        <CardHeader className="pb-2 border-b bg-background/50">
                            <CardTitle className="text-lg font-semibold flex items-center gap-2">
                                <Info className="h-5 w-5 text-primary" />
                                Dataset Requirements
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 overflow-y-auto p-6 space-y-8">
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
                                        <LibraryBig className="h-5 w-5" />
                                    </div>
                                    <h3 className="font-semibold">Courses Format</h3>
                                </div>
                                <div className="pl-2 border-l-2 border-blue-200 dark:border-blue-800 space-y-3">
                                    <div className="text-sm">
                                        <p className="font-medium mb-1">Required Columns:</p>
                                        <code className="bg-background px-2 py-1 rounded border text-xs block w-full overflow-x-auto text-muted-foreground">
                                            course_name, instructor, section, program, type, hours_per_week
                                        </code>
                                    </div>
                                    <ul className="space-y-2 text-sm text-muted-foreground">
                                        <li className="flex items-center gap-2">
                                            <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                                            <span>Type must be "Lab" or "Theory"</span>
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                                            <span>Multiple sections need separate rows</span>
                                        </li>
                                    </ul>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <div className="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400">
                                        <School className="h-5 w-5" />
                                    </div>
                                    <h3 className="font-semibold">Rooms Format</h3>
                                </div>
                                <div className="pl-2 border-l-2 border-orange-200 dark:border-orange-800 space-y-3">
                                    <div className="text-sm">
                                        <p className="font-medium mb-1">Required Columns:</p>
                                        <code className="bg-background px-2 py-1 rounded border text-xs block w-full overflow-x-auto text-muted-foreground">
                                            room_name, type, capacity
                                        </code>
                                    </div>
                                    <ul className="space-y-2 text-sm text-muted-foreground">
                                        <li className="flex items-center gap-2">
                                            <div className="h-1.5 w-1.5 rounded-full bg-orange-500" />
                                            <span>Type must be "Lab" or "Theory"</span>
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <div className="h-1.5 w-1.5 rounded-full bg-orange-500" />
                                            <span>Capacity defaults to 50 if missing</span>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Bottom Row: Uploaded Files List */}
                <div className="flex flex-col min-h-0 flex-1 mt-10 relative z-10">
                    <div className="flex items-center justify-between mb-3 shrink-0">
                        <h2 className="text-lg font-semibold tracking-tight flex items-center gap-2">
                            <Database className="h-5 w-5 text-muted-foreground" />
                            Active Datasets
                        </h2>
                        <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-full">
                            {datasets?.length || 0} files
                        </span>
                    </div>

                    <Card className="max-h-full overflow-hidden border-border/60 shadow-sm bg-card/50 flex flex-col">
                        <CardContent className="p-0 overflow-y-auto">
                            {datasets && datasets.length > 0 ? (
                                <div className="divide-y divide-border/50">
                                    {datasets.map((dataset: any) => (
                                        <div
                                            key={dataset.id}
                                            className="group flex items-center justify-between p-4 hover:bg-muted/30 transition-all duration-200"
                                        >
                                            <div className="flex items-center gap-4">
                                                <div className={`p-2.5 rounded-xl shrink-0 ${
                                                    dataset.dataset_type === 'courses' 
                                                        ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400' 
                                                        : 'bg-orange-100 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400'
                                                }`}>
                                                    {dataset.dataset_type === 'courses' ? (
                                                        <LibraryBig className="h-5 w-5" />
                                                    ) : (
                                                        <School className="h-5 w-5" />
                                                    )}
                                                </div>
                                                <div className="min-w-0">
                                                    <div className="flex items-center gap-2 mb-0.5">
                                                        <h3 className="font-semibold text-sm truncate">{dataset.file_name}</h3>
                                                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                                            dataset.validation_status === 'valid'
                                                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                                                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                                        }`}>
                                                            {dataset.validation_status}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                                        <span className="flex items-center gap-1">
                                                            <FileSpreadsheet className="h-3 w-3" />
                                                            {dataset.row_count} rows
                                                        </span>
                                                        <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
                                                        <span>{formatDateTime(dataset.created_at)}</span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    className="h-8 text-xs font-medium"
                                                    onClick={() => {
                                                        setPreviewDataset({ 
                                                            id: dataset.id, 
                                                            file_name: dataset.filename || dataset.file_name 
                                                        })
                                                        setPreviewOpen(true)
                                                    }}
                                                >
                                                    View Data
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                                                    onClick={() => setDatasetToDelete({ 
                                                        id: dataset.id, 
                                                        file_name: dataset.filename || dataset.file_name 
                                                    })}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-full py-12 text-center">
                                    <div className="bg-muted/30 p-4 rounded-full mb-3">
                                        <Database className="h-8 w-8 text-muted-foreground/50" />
                                    </div>
                                    <h3 className="font-medium text-base">No datasets</h3>
                                    <p className="text-muted-foreground text-xs mt-1">
                                        Upload files to see them here
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>

            <DataPreviewModal 
                open={previewOpen} 
                onOpenChange={setPreviewOpen} 
                datasetId={previewDataset?.id ?? null} 
                fileName={previewDataset?.file_name} 
            />

            <AlertDialog open={!!datasetToDelete} onOpenChange={(open) => !open && setDatasetToDelete(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will permanently delete the dataset <span className="font-medium text-foreground">{datasetToDelete?.file_name}</span> and remove all associated records from the database.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction 
                            onClick={() => datasetToDelete && deleteMutation.mutate(datasetToDelete.id)}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {deleteMutation.isPending ? "Deleting..." : "Delete"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}