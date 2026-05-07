import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { BreadcrumbItem } from '@/contexts/M365LayoutContext'

interface BreadcrumbsProps {
    items: BreadcrumbItem[]
    className?: string
}

export function Breadcrumbs({ items, className }: BreadcrumbsProps) {
    if (items.length === 0) return null

    return (
        <nav
            aria-label="Breadcrumb"
            className={cn("flex items-center text-sm", className)}
        >
            <ol className="flex items-center gap-1">
                {items.map((item, index) => {
                    const isLast = index === items.length - 1

                    return (
                        <li key={index} className="flex items-center gap-1">
                            {index > 0 && (
                                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60 flex-shrink-0" />
                            )}
                            {isLast || !item.href ? (
                                <span
                                    className={cn(
                                        "font-medium",
                                        isLast ? "text-foreground" : "text-muted-foreground"
                                    )}
                                    aria-current={isLast ? "page" : undefined}
                                >
                                    {item.label}
                                </span>
                            ) : (
                                <Link
                                    to={item.href}
                                    className="text-muted-foreground hover:text-foreground transition-colors"
                                >
                                    {item.label}
                                </Link>
                            )}
                        </li>
                    )
                })}
            </ol>
        </nav>
    )
}
