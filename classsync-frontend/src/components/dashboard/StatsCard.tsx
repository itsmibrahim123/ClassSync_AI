import { LucideIcon } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatsCardProps {
    title: string
    value: string | number
    icon: LucideIcon
    description?: string
    trend?: {
        value: number
        isPositive: boolean
    }
    color?: 'blue' | 'purple' | 'green' | 'coral'
    className?: string
}

const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/40 dark:text-purple-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/40 dark:text-green-400',
    coral: 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400',
}

const gradientClasses = {
    blue: 'from-blue-50/50 to-transparent dark:from-blue-900/10',
    purple: 'from-purple-50/50 to-transparent dark:from-purple-900/10',
    green: 'from-green-50/50 to-transparent dark:from-green-900/10',
    coral: 'from-red-50/50 to-transparent dark:from-red-900/10',
}

export function StatsCard({
                              title,
                              value,
                              icon: Icon,
                              description,
                              trend,
                              color = 'blue',
                              className
                          }: StatsCardProps) {
    return (
        <Card className={cn(
            "transition-all hover:shadow-md hover:-translate-y-0.5 bg-gradient-to-br shadow-sm",
            gradientClasses[color],
            className
        )}>
            <CardHeader className="flex flex-row items-center justify-between p-3 pb-1">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    {title}
                </CardTitle>
                <div className={cn("rounded-md p-1.5", colorClasses[color])}>
                    <Icon className="h-3.5 w-3.5" />
                </div>
            </CardHeader>
            <CardContent className="p-3 pt-0">
                <div className="text-2xl font-bold tracking-tight">{value}</div>
                {(description || trend) && (
                    <div className="flex items-center gap-2 mt-1 min-h-[20px]">
                        {trend && (
                            <span className={cn(
                                "text-[10px] font-bold flex items-center bg-background/50 px-1 rounded",
                                trend.isPositive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                            )}>
                                {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
                            </span>
                        )}
                        {description && (
                            <p className="text-[10px] text-muted-foreground truncate leading-none">
                                {description}
                            </p>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}