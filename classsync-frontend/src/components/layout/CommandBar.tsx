import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { MoreHorizontal, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useM365Layout, type CommandBarAction } from '@/contexts/M365LayoutContext'

export function CommandBar() {
    const { commandBarActions, primaryAction } = useM365Layout()
    const [overflowItems, setOverflowItems] = useState<CommandBarAction[]>([])
    const [visibleItems, setVisibleItems] = useState<CommandBarAction[]>([])
    const containerRef = useRef<HTMLDivElement>(null)
    const actionsRef = useRef<HTMLDivElement>(null)

    // Handle responsive overflow
    useEffect(() => {
        const handleResize = () => {
            if (!containerRef.current || !actionsRef.current) return

            const containerWidth = containerRef.current.offsetWidth
            const primaryWidth = 150 // Approximate primary button width
            const moreButtonWidth = 48
            const availableWidth = containerWidth - primaryWidth - moreButtonWidth - 32 // 32px padding

            let usedWidth = 0
            const visible: CommandBarAction[] = []
            const overflow: CommandBarAction[] = []

            commandBarActions.forEach((action) => {
                const itemWidth = 44 // Approximate icon button width
                if (usedWidth + itemWidth <= availableWidth) {
                    visible.push(action)
                    usedWidth += itemWidth
                } else {
                    overflow.push(action)
                }
            })

            setVisibleItems(visible)
            setOverflowItems(overflow)
        }

        handleResize()
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [commandBarActions])

    // Don't render if no actions
    if (commandBarActions.length === 0 && !primaryAction) {
        return null
    }

    return (
        <div
            ref={containerRef}
            className="h-commandbar bg-background border-b border-border px-4 flex items-center justify-between"
            role="toolbar"
            aria-label="Page actions"
        >
            {/* Left: Secondary actions */}
            <div ref={actionsRef} className="flex items-center gap-1">
                {visibleItems.map((action) => (
                    <ActionButton key={action.id} action={action} />
                ))}

                {/* Overflow menu */}
                {overflowItems.length > 0 && (
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                                <MoreHorizontal className="h-4 w-4" />
                                <span className="sr-only">More actions</span>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start">
                            {overflowItems.map((action) => (
                                <DropdownMenuItem
                                    key={action.id}
                                    onClick={action.onClick}
                                    disabled={action.disabled}
                                >
                                    {action.icon && <span className="mr-2">{action.icon}</span>}
                                    {action.label}
                                </DropdownMenuItem>
                            ))}
                        </DropdownMenuContent>
                    </DropdownMenu>
                )}
            </div>

            {/* Right: Primary action */}
            {primaryAction && (
                <div className="flex items-center">
                    <PrimaryActionButton action={primaryAction} />
                </div>
            )}
        </div>
    )
}

function ActionButton({ action }: { action: CommandBarAction }) {
    if (action.dropdown) {
        return (
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 gap-1.5"
                        disabled={action.disabled}
                    >
                        {action.icon}
                        <span className="hidden sm:inline">{action.label}</span>
                        <ChevronDown className="h-3 w-3" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                    {action.dropdown.map((item) => (
                        <DropdownMenuItem
                            key={item.id}
                            onClick={item.onClick}
                            disabled={item.disabled}
                        >
                            {item.icon && <span className="mr-2">{item.icon}</span>}
                            {item.label}
                        </DropdownMenuItem>
                    ))}
                </DropdownMenuContent>
            </DropdownMenu>
        )
    }

    if (action.href) {
        return (
            <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1.5"
                disabled={action.disabled}
                asChild
            >
                <Link to={action.href}>
                    {action.icon}
                    <span className="hidden sm:inline">{action.label}</span>
                </Link>
            </Button>
        )
    }

    return (
        <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5"
            onClick={action.onClick}
            disabled={action.disabled}
        >
            {action.icon}
            <span className="hidden sm:inline">{action.label}</span>
        </Button>
    )
}

function PrimaryActionButton({ action }: { action: CommandBarAction }) {
    if (action.dropdown) {
        return (
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button
                        size="sm"
                        className="h-8 gap-1.5"
                        disabled={action.disabled}
                    >
                        {action.icon}
                        {action.label}
                        <ChevronDown className="h-3 w-3 ml-1" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                    {action.dropdown.map((item) => (
                        <DropdownMenuItem
                            key={item.id}
                            onClick={item.onClick}
                            disabled={item.disabled}
                        >
                            {item.icon && <span className="mr-2">{item.icon}</span>}
                            {item.label}
                        </DropdownMenuItem>
                    ))}
                </DropdownMenuContent>
            </DropdownMenu>
        )
    }

    if (action.href) {
        return (
            <Button
                size="sm"
                className="h-8 gap-1.5"
                disabled={action.disabled}
                asChild
            >
                <Link to={action.href}>
                    {action.icon}
                    {action.label}
                </Link>
            </Button>
        )
    }

    return (
        <Button
            size="sm"
            className="h-8 gap-1.5"
            onClick={action.onClick}
            disabled={action.disabled}
        >
            {action.icon}
            {action.label}
        </Button>
    )
}
