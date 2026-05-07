import { cn } from '@/lib/utils'

interface PageHeaderProps {
    title: string
    subtitle?: string
    children?: React.ReactNode
    className?: string
}

export function PageHeader({ title, subtitle, children, className }: PageHeaderProps) {
    return (
        <div className={cn(
            "flex items-start justify-between gap-4 mb-6",
            className
        )}>
            <div className="min-w-0 flex-1">
                <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                    {title}
                </h1>
                {subtitle && (
                    <p className="mt-1 text-sm text-muted-foreground">
                        {subtitle}
                    </p>
                )}
            </div>

            {children && (
                <div className="flex items-center gap-2 flex-shrink-0">
                    {children}
                </div>
            )}
        </div>
    )
}
