import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export interface CommandBarAction {
    id: string
    label: string
    icon?: ReactNode
    onClick?: () => void
    href?: string
    variant?: 'primary' | 'secondary' | 'ghost'
    disabled?: boolean
    dropdown?: CommandBarAction[]
}

export interface PivotTab {
    id: string
    label: string
    icon?: ReactNode
}

export interface BreadcrumbItem {
    label: string
    href?: string
}

interface M365LayoutContextValue {
    // Command Bar
    commandBarActions: CommandBarAction[]
    primaryAction: CommandBarAction | null
    setCommandBarActions: (actions: CommandBarAction[]) => void
    setPrimaryAction: (action: CommandBarAction | null) => void

    // Breadcrumbs
    breadcrumbs: BreadcrumbItem[]
    setBreadcrumbs: (items: BreadcrumbItem[]) => void

    // Pivot Tabs
    pivotTabs: PivotTab[]
    activePivotTab: string | null
    setPivotTabs: (tabs: PivotTab[]) => void
    setActivePivotTab: (tabId: string | null) => void

    // Page Info
    pageTitle: string
    setPageTitle: (title: string) => void
}

const M365LayoutContext = createContext<M365LayoutContextValue | null>(null)

export function M365LayoutProvider({ children }: { children: ReactNode }) {
    const [commandBarActions, setCommandBarActionsState] = useState<CommandBarAction[]>([])
    const [primaryAction, setPrimaryActionState] = useState<CommandBarAction | null>(null)
    const [breadcrumbs, setBreadcrumbsState] = useState<BreadcrumbItem[]>([])
    const [pivotTabs, setPivotTabsState] = useState<PivotTab[]>([])
    const [activePivotTab, setActivePivotTabState] = useState<string | null>(null)
    const [pageTitle, setPageTitleState] = useState('')

    const setCommandBarActions = useCallback((actions: CommandBarAction[]) => {
        setCommandBarActionsState(actions)
    }, [])

    const setPrimaryAction = useCallback((action: CommandBarAction | null) => {
        setPrimaryActionState(action)
    }, [])

    const setBreadcrumbs = useCallback((items: BreadcrumbItem[]) => {
        setBreadcrumbsState(items)
    }, [])

    const setPivotTabs = useCallback((tabs: PivotTab[]) => {
        setPivotTabsState(tabs)
    }, [])

    const setActivePivotTab = useCallback((tabId: string | null) => {
        setActivePivotTabState(tabId)
    }, [])

    const setPageTitle = useCallback((title: string) => {
        setPageTitleState(title)
    }, [])

    return (
        <M365LayoutContext.Provider
            value={{
                commandBarActions,
                primaryAction,
                setCommandBarActions,
                setPrimaryAction,
                breadcrumbs,
                setBreadcrumbs,
                pivotTabs,
                activePivotTab,
                setPivotTabs,
                setActivePivotTab,
                pageTitle,
                setPageTitle,
            }}
        >
            {children}
        </M365LayoutContext.Provider>
    )
}

export function useM365Layout() {
    const context = useContext(M365LayoutContext)
    if (!context) {
        throw new Error('useM365Layout must be used within M365LayoutProvider')
    }
    return context
}

// Hook for pages to configure their layout
export function usePageLayout(config: {
    title: string
    breadcrumbs: BreadcrumbItem[]
    commandBarActions?: CommandBarAction[]
    primaryAction?: CommandBarAction | null
    pivotTabs?: PivotTab[]
    defaultPivotTab?: string
}) {
    const {
        setPageTitle,
        setBreadcrumbs,
        setCommandBarActions,
        setPrimaryAction,
        setPivotTabs,
        setActivePivotTab,
        activePivotTab,
    } = useM365Layout()

    // Set initial values on mount
    useState(() => {
        setPageTitle(config.title)
        setBreadcrumbs(config.breadcrumbs)
        setCommandBarActions(config.commandBarActions || [])
        setPrimaryAction(config.primaryAction || null)
        setPivotTabs(config.pivotTabs || [])
        if (config.defaultPivotTab) {
            setActivePivotTab(config.defaultPivotTab)
        }
    })

    return {
        activePivotTab,
        setActivePivotTab,
        setCommandBarActions,
        setPrimaryAction,
    }
}
