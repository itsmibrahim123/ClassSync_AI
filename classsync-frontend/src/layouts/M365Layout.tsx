import { Outlet } from 'react-router-dom'
import { TopNav } from '@/components/layout/TopNav'
import { CommandBar } from '@/components/layout/CommandBar'
import { PivotTabs } from '@/components/layout/PivotTabs'
import { M365LayoutProvider } from '@/contexts/M365LayoutContext'

export function M365Layout() {
    return (
        <M365LayoutProvider>
            <div className="min-h-screen bg-background flex flex-col">
                {/* Top Navigation */}
                <TopNav />

                {/* Command Bar */}
                <CommandBar />

                {/* Pivot Tabs (optional, pages set them via context) */}
                <PivotTabs />

                {/* Main Content */}
                <main className="flex-1 overflow-y-auto">
                    <div className="container mx-auto p-6 max-w-7xl">
                        <Outlet />
                    </div>
                </main>
            </div>
        </M365LayoutProvider>
    )
}
