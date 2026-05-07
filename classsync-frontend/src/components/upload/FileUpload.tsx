import { useState, useCallback } from 'react'
import { Upload, X, FileText, LibraryBig, School, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface FileUploadProps {
    onUpload: (file: File, type: string) => void
    isUploading?: boolean
    className?: string
}

export function FileUpload({ onUpload, isUploading, className }: FileUploadProps) {
    const [dragActive, setDragActive] = useState(false)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const [datasetType, setDatasetType] = useState<'courses' | 'rooms'>('courses')

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true)
        } else if (e.type === "dragleave") {
            setDragActive(false)
        }
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setSelectedFile(e.dataTransfer.files[0])
        }
    }, [])

    const handleFileSelect = () => {
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = '.csv'
        input.onchange = (e) => {
            const target = e.target as HTMLInputElement
            if (target.files && target.files[0]) {
                setSelectedFile(target.files[0])
            }
        }
        input.click()
    }

    const handleUpload = () => {
        if (selectedFile) {
            onUpload(selectedFile, datasetType)
        }
    }

    const handleClear = () => {
        setSelectedFile(null)
    }

    return (
        <Card
            className={cn(
                "relative overflow-hidden border-2 border-dashed transition-all duration-300 h-full flex flex-col",
                dragActive ? "border-primary bg-primary/5 scale-[1.01]" : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/20",
                selectedFile ? "border-solid border-primary/20 bg-background" : "",
                className
            )}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
        >
            <CardContent className="flex flex-col items-center justify-center p-6 text-center flex-1">
                {!selectedFile ? (
                    <div className="space-y-4 flex flex-col items-center justify-center h-full">
                        <div className={cn(
                            "mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 transition-transform duration-500",
                            dragActive && "scale-110"
                        )}>
                            <Upload className="h-8 w-8 text-primary" />
                        </div>
                        <div className="space-y-1">
                            <h3 className="text-lg font-semibold tracking-tight">
                                Upload dataset
                            </h3>
                            <p className="text-sm text-muted-foreground max-w-xs mx-auto">
                                Drag and drop CSV file
                            </p>
                        </div>
                        <Button
                            size="sm"
                            onClick={handleFileSelect}
                            disabled={isUploading}
                            className="mt-2 shadow-sm"
                        >
                            Select File
                        </Button>
                    </div>
                ) : (
                    <div className="w-full max-w-md space-y-5 animate-in fade-in zoom-in-95 duration-300 m-auto">
                        {/* File Info Card */}
                        <div className="flex items-center justify-between p-3 bg-muted/30 rounded-xl border border-border/50">
                            <div className="flex items-center gap-3 overflow-hidden">
                                <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-primary/10 text-primary">
                                    <FileText className="h-5 w-5" />
                                </div>
                                <div className="min-w-0 text-left">
                                    <p className="font-medium text-sm truncate">{selectedFile.name}</p>
                                    <p className="text-[10px] text-muted-foreground">
                                        {(selectedFile.size / 1024).toFixed(2)} KB
                                    </p>
                                </div>
                            </div>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={handleClear}
                                disabled={isUploading}
                                className="h-8 w-8 text-muted-foreground hover:text-destructive transition-colors"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>

                        {/* Dataset Type Selection Cards */}
                        <div className="space-y-2 text-left">
                            <label className="text-xs font-medium text-muted-foreground ml-1">
                                Dataset Type
                            </label>
                            <div className="grid grid-cols-2 gap-3">
                                <div
                                    className={cn(
                                        "cursor-pointer rounded-lg border p-3 transition-all hover:bg-muted/50",
                                        datasetType === 'courses'
                                            ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                            : "border-transparent bg-muted/30 hover:border-border"
                                    )}
                                    onClick={() => setDatasetType('courses')}
                                >
                                    <LibraryBig className={cn("h-5 w-5 mb-2", datasetType === 'courses' ? "text-primary" : "text-muted-foreground")} />
                                    <p className="font-medium text-sm">Courses</p>
                                </div>
                                <div
                                    className={cn(
                                        "cursor-pointer rounded-lg border p-3 transition-all hover:bg-muted/50",
                                        datasetType === 'rooms'
                                            ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                            : "border-transparent bg-muted/30 hover:border-border"
                                    )}
                                    onClick={() => setDatasetType('rooms')}
                                >
                                    <School className={cn("h-5 w-5 mb-2", datasetType === 'rooms' ? "text-primary" : "text-muted-foreground")} />
                                    <p className="font-medium text-sm">Rooms</p>
                                </div>
                            </div>
                        </div>

                        <Button
                            className="w-full h-10 text-sm shadow-md transition-all"
                            onClick={handleUpload}
                            disabled={isUploading}
                        >
                            {isUploading ? (
                                <div className="flex items-center gap-2">
                                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                                    Processing...
                                </div>
                            ) : (
                                <span className="flex items-center gap-2">
                                    Upload Dataset <ArrowRight className="h-4 w-4" />
                                </span>
                            )}
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}