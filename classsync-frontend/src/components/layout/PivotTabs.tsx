import { cn } from '@/lib/utils'
import { useM365Layout } from '@/contexts/M365LayoutContext'

interface PivotTabsProps {
    className?: string
}

export function PivotTabs({ className }: PivotTabsProps) {
    const { pivotTabs, activePivotTab, setActivePivotTab } = useM365Layout()

    if (pivotTabs.length === 0) return null

    return (
        <div
            className={cn(
                "bg-background border-b border-border",
                className
            )}
            role="tablist"
            aria-label="Page sections"
        >
            <div className="flex items-center gap-1 px-4 h-10">
                {pivotTabs.map((tab) => {
                    const isActive = activePivotTab === tab.id

                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActivePivotTab(tab.id)}
                            className={cn(
                                "relative flex items-center gap-2 px-3 py-2 text-sm font-medium transition-colors",
                                "hover:text-foreground",
                                isActive
                                    ? "text-primary"
                                    : "text-muted-foreground"
                            )}
                            role="tab"
                            aria-selected={isActive}
                            aria-controls={`tabpanel-${tab.id}`}
                        >
                            {tab.icon && (
                                <span className="flex-shrink-0">{tab.icon}</span>
                            )}
                            <span>{tab.label}</span>

                            {/* Active indicator */}
                            {isActive && (
                                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
                            )}
                        </button>
                    )
                })}
            </div>
        </div>
    )
}

// Panel component to show content for active tab
interface PivotTabPanelProps {
    tabId: string
    children: React.ReactNode
    className?: string
}

export function PivotTabPanel({ tabId, children, className }: PivotTabPanelProps) {
    const { activePivotTab } = useM365Layout()

    if (activePivotTab !== tabId) return null

    return (
        <div
            role="tabpanel"
            id={`tabpanel-${tabId}`}
            className={className}
        >
            {children}
        </div>
    )
}
