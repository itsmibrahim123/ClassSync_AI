import axios from 'axios'

const api = axios.create({
    baseURL: '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor for adding auth token (when we add auth later)
api.interceptors.request.use(
    (config) => {
        // const token = localStorage.getItem('token')
        // if (token) {
        //   config.headers.Authorization = `Bearer ${token}`
        // }
        return config
    },
    (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Handle unauthorized
            console.error('Unauthorized access')
        }
        return Promise.reject(error)
    }
)

// API Functions
export const datasetsApi = {
    list: () => api.get('/datasets/'),
    upload: (file: File, datasetType: string) => {
        const formData = new FormData()
        formData.append('file', file)

        // dataset_type goes as query parameter, NOT in formData
        return api.post(`/datasets/upload?dataset_type=${datasetType}`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        })
    },
    delete: (id: number) => api.delete(`/datasets/${id}`),
    preview: (id: number, params?: { offset?: number; limit?: number }) =>
        api.get(`/datasets/${id}/preview`, { params }),
}

export const timetablesApi = {
    list: () => api.get('/scheduler/timetables'),
    get: (id: number) => api.get(`/scheduler/timetables/${id}`),
    generate: (request?: {
        constraint_config_id?: number
        teacher_constraints?: any[]
        room_constraints?: any[]
        locked_assignments?: any[]
        population_size?: number
        generations?: number
        target_fitness?: number
        random_seed?: number
    }) => api.post('/scheduler/generate', request || {}),
    update: (id: number, name: string) => api.patch(`/scheduler/timetables/${id}`, { name }),
    delete: (id: number) => api.delete(`/scheduler/timetables/${id}`),
    export: (id: number, format: string, viewType: string) =>
        api.get(`/scheduler/timetables/${id}/export`, {
            params: { format, view_type: viewType },
            responseType: 'blob',
        }),
    downloadDiagnostics: () => api.get('/scheduler/debug/diagnostics/download', { responseType: 'blob' }),
    hardReset: () => api.delete('/scheduler/debug/hard-reset?confirm=true'),
}

export const constraintsApi = {
    list: () => api.get('/constraints/configs'),
    get: (id: number) => api.get(`/constraints/configs/${id}`),
    create: (data: any) => api.post('/constraints/configs', data),
    update: (id: number, data: any) => api.put(`/constraints/configs/${id}`, data),
    delete: (id: number) => api.delete(`/constraints/configs/${id}`),
    setDefault: (id: number) => api.post(`/constraints/configs/${id}/set-default`),
}

export const teacherConstraintsApi = {
    list: () => api.get('/constraints/teacher-profiles'),
    get: (id: number) => api.get(`/constraints/teacher-profiles/${id}`),
    create: (data: any) => api.post('/constraints/teacher-profiles', data),
    update: (id: number, data: any) => api.put(`/constraints/teacher-profiles/${id}`, data),
    delete: (id: number) => api.delete(`/constraints/teacher-profiles/${id}`),
    setDefault: (id: number) => api.post(`/constraints/teacher-profiles/${id}/set-default`),
}

export const healthApi = {
    check: () => api.get('/health/detailed'),
}

export const teachersApi = {
    list: () => api.get('/teachers/'),
    get: (id: number) => api.get(`/teachers/${id}`),
    updatePreferences: (id: number, preferences: Record<string, any>) =>
        api.patch(`/teachers/${id}/preferences`, preferences),
}

export const roomsApi = {
    list: () => api.get('/datasets/').then(res => {
        // Filter for rooms data - this is a workaround until we have a proper rooms endpoint
        return res
    }),
}

export const dashboardApi = {
    stats: () => api.get('/dashboard/stats'),
}

export default api