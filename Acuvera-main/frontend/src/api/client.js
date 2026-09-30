import axios from 'axios'

// Ensure baseURL always ends with /api
const rawBaseURL = import.meta.env.VITE_API_URL || '/api'
const baseURL = rawBaseURL.endsWith('/api') ? rawBaseURL : rawBaseURL.replace(/\/$/, '') + '/api'

const api = axios.create({
    baseURL,
    headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('acuvera_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    const bypassId = localStorage.getItem('acuvera_bypass_user_id')
    if (bypassId) config.headers['X-Bypass-User-Id'] = bypassId
    return config
})

api.interceptors.response.use(
    (res) => res,
    (err) => {
        if (err.response?.status === 401) {
            localStorage.removeItem('acuvera_token')
            window.location.href = '/login'
        }
        return Promise.reject(err)
    }
)

export default api

export const AuthAPI = {
    whoami: () => api.get('/auth/whoami/').then(r => r.data.data),
    register: (data) => api.post('/auth/register/', data).then(r => r.data.data),
    login: (data) => api.post('/auth/login/', data).then(r => r.data.data),
}

export const PatientAPI = {
    list: (params) => api.get('/patients/', { params }).then(r => r.data.data),
    get: (id) => api.get(`/patients/${id}/`).then(r => r.data.data),
    create: (data) => api.post('/patients/', data).then(r => r.data.data),
}

export const EncounterAPI = {
    list: (params) => api.get('/encounters/', { params }).then(r => r.data.data),
    get: (id) => api.get(`/encounters/${id}/`).then(r => r.data.data),
    create: (data) => api.post('/encounters/', data).then(r => r.data.data),
    patch: (id, data) => api.patch(`/encounters/${id}/`, data).then(r => r.data.data),
    assign: (id, doctorId) => api.patch(`/encounters/${id}/assign/`, { doctor_id: doctorId }).then(r => r.data.data),
    updateLocation: (id, data) => api.patch(`/encounters/${id}/location/`, data).then(r => r.data.data),
}

export const TriageAPI = {
    analyze: (encounterId, data) => api.post(`/triage/${encounterId}/analyze/`, data).then(r => r.data.data),
}

export const AllocationAPI = {
    suggest: (encounterId) => api.post(`/allocation/suggest/${encounterId}/`).then(r => r.data.data),
    candidates: (encounterId) => api.get(`/allocation/candidates/${encounterId}/`).then(r => r.data.data),
    confirm: (data) => api.post('/allocation/confirm/', data).then(r => r.data.data),
    respond: (data) => api.post('/allocation/respond/', data).then(r => r.data.data),
    refer: (data) => api.post('/allocation/refer/', data).then(r => r.data.data),
}

export const EscalationAPI = {
    trigger: (data) => api.post('/escalation/trigger/', data).then(r => r.data.data),
    acknowledge: (data) => api.post('/escalation/acknowledge/', typeof data === 'string' || typeof data === 'number' ? { event_id: data } : data).then(r => r.data.data),
    events: (params) => api.get('/escalation/events/', { params }).then(r => r.data.data),
}

export const AdminAPI = {
    overview: (params) => api.get('/admin/overview/', { params }).then(r => r.data.data),
    forecast: (params) => api.get('/admin/forecast/', { params }).then(r => r.data.data),
    financialImpact: (params) => api.get('/admin/financial-impact/', { params }).then(r => r.data.data),
    starvationAlerts: (params) => api.get('/admin/starvation-alerts/', { params }).then(r => r.data.data),
    config: () => api.get('/admin/config/').then(r => r.data.data),
    updateConfig: (data) => api.post('/admin/config/', data).then(r => r.data.data),
    doctorUtilization: (id) => api.get(`/admin/doctor/${id}/utilization/`).then(r => r.data.data),
    departments: () => api.get('/departments/').then(r => r.data.data),
    doctors: (deptId) => api.get('/doctors/', { params: deptId ? { department: deptId } : {} }).then(r => r.data.data),
    snapshots: (params) => api.get('/admin/snapshots/', { params }).then(r => r.data.data),
    staffList: (params) => api.get('/admin/staff/', { params }).then(r => r.data.data),
    updateStaff: (id, data) => api.patch(`/admin/staff/${id}/`, data).then(r => r.data.data),
    deleteStaff: (id) => api.delete(`/admin/staff/${id}/`).then(r => r.data.data),
    // Department Management
    createDepartment: (data) => api.post('/departments/', data).then(r => r.data.data),
    updateDepartment: (id, data) => api.patch(`/departments/${id}/`, data).then(r => r.data.data),
    deleteDepartment: (id) => api.delete(`/departments/${id}/`).then(r => r.data.data),
    // Clear all encounters (admin reset)
    clearEncounters: (mode = 'encounters') => api.post('/admin/clear-encounters/', { mode }).then(r => r.data.data),
    // Assistant chat
    insightChat: (data) => api.post('/admin/insight-chat/', data).then(r => r.data.data),
}

export const AssessmentAPI = {
    get: (encounterId) => api.get(`/encounters/${encounterId}/assessment/`).then(r => r.data.data),
    save: (encounterId, data) => api.post(`/encounters/${encounterId}/assessment/`, data).then(r => r.data.data),
    complete: (encounterId, data) => api.post(`/encounters/${encounterId}/assessment/complete/`, data).then(r => r.data.data),
}

export const InsightAPI = {
    generate: (encounterId) => api.post(`/encounters/${encounterId}/insight/`).then(r => r.data.data),
}

export const AmbulanceAPI = {
    preRegister: (data) => api.post('/encounters/ambulance/', data, {
        headers: { 'X-Ambulance-Key': 'acuvera-demo-ambulance' }
    }).then(r => r.data.data),
    listIncoming: () => api.get('/encounters/incoming/').then(r => r.data.data),
}

// Add simulate to AdminAPI — exported separately above for clarity
export const SimulateAPI = {
    run: (data) => api.post('/admin/simulate/', data).then(r => r.data.data),
}
