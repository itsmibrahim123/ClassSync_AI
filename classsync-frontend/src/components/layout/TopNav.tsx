import { Link, useLocation } from 'react-router-dom'
import { Sun, Moon, LayoutDashboard, Upload, Sparkles, Calendar, Settings } from 'lucide-react'
import { useTheme } from '@/components/theme-provider'
import { Button } from '@/components/ui/button'
import { Breadcrumbs } from './Breadcrumbs'
import { useM365Layout } from '@/contexts/M365LayoutContext'
import { cn } from '@/lib/utils'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const navItems = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Upload', href: '/upload', icon: Upload },
    { name: 'Generate', href: '/generate', icon: Sparkles },
    { name: 'Timetables', href: '/timetables', icon: Calendar },
    { name: 'Settings', href: '/settings', icon: Settings },
]

export function TopNav() {
    const { theme, setTheme } = useTheme()
    const { breadcrumbs } = useM365Layout()
    const location = useLocation()

    return (
        <header className="sticky top-0 z-40 h-nav bg-background border-b border-border">
            <div className="flex items-center justify-between h-full px-4">
                {/* Left section: Logo + Nav Links */}
                <div className="flex items-center gap-1">
                    <Link
                        to="/"
                        className="flex items-center gap-2 px-2 mr-2 hover:opacity-80 transition-opacity"
                    >
                        <div className="flex items-center justify-center w-7 h-7 rounded bg-primary text-primary-foreground text-sm font-bold">
                            C
                        </div>
                        <span className="font-semibold text-sm hidden sm:inline">
                            ClassSync
                        </span>
                    </Link>

                    {/* Navigation Links */}
                    <nav className="hidden md:flex items-center">
                        {navItems.map((item) => {
                            const isActive = location.pathname === item.href ||
                                (item.href !== '/' && location.pathname.startsWith(item.href))

                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    className={cn(
                                        "flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                                        isActive
                                            ? "bg-primary/10 text-primary"
                                            : "text-muted-foreground hover:text-foreground hover:bg-accent"
                                    )}
                                >
                                    <item.icon className="h-4 w-4" />
                                    <span>{item.name}</span>
                                </Link>
                            )
                        })}
                    </nav>
                </div>

                {/* Mobile nav dropdown */}
                <div className="md:hidden">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm">
                                Menu
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                            {navItems.map((item) => (
                                <DropdownMenuItem key={item.name} asChild>
                                    <Link to={item.href} className="flex items-center gap-2">
                                        <item.icon className="h-4 w-4" />
                                        {item.name}
                                    </Link>
                                </DropdownMenuItem>
                            ))}
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>

                {/* Right section: Breadcrumbs + Theme + User */}
                <div className="flex items-center gap-2">
                    {/* Breadcrumbs - hidden on mobile */}
                    <div className="hidden lg:flex items-center mr-2 pr-4 border-r border-border">
                        {breadcrumbs.length > 0 && (
                            <Breadcrumbs items={breadcrumbs} />
                        )}
                    </div>

                    {/* Theme toggle */}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9"
                        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                        aria-label="Toggle theme"
                    >
                        {theme === 'dark' ? (
                            <Sun className="h-4 w-4" />
                        ) : (
                            <Moon className="h-4 w-4" />
                        )}
                    </Button>

                    {/* User menu */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <button
                                className={cn(
                                    "flex items-center justify-center w-8 h-8 rounded-full",
                                    "bg-primary text-primary-foreground text-xs font-semibold",
                                    "hover:ring-2 hover:ring-primary/20 transition-shadow"
                                )}
                                aria-label="User menu"
                            >
                                SM
                            </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                            <DropdownMenuLabel>
                                <div className="flex flex-col">
                                    <span className="font-medium">Saad Mughal</span>
                                    <span className="text-xs text-muted-foreground font-normal">
                                        Admin
                                    </span>
                                </div>
                            </DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem asChild>
                                <Link to="/settings" className="w-full">Settings</Link>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-muted-foreground">
                                Sign out
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>
        </header>
    )
}
