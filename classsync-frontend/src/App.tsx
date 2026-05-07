import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { M365Layout } from './layouts/M365Layout'
import { Dashboard } from './pages/Dashboard'
import { Upload } from './pages/Upload'
import { Timetables } from './pages/Timetables'
import { TimetableView } from './pages/TimetableView'
import { GenerateTimetable } from './pages/GenerateTimetable'
import { Settings } from './pages/Settings'
import { ThemeProvider } from './components/theme-provider'

const queryClient = new QueryClient()

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
                <BrowserRouter>
                    <Routes>
                        <Route path="/" element={<M365Layout />}>
                            <Route index element={<Dashboard />} />
                            <Route path="upload" element={<Upload />} />
                            <Route path="generate" element={<GenerateTimetable />} />
                            <Route path="timetables" element={<Timetables />} />
                            <Route path="timetables/:id" element={<TimetableView />} />
                            <Route path="settings" element={<Settings />} />
                        </Route>
                    </Routes>
                </BrowserRouter>
            </ThemeProvider>
        </QueryClientProvider>
    )
}

export default App