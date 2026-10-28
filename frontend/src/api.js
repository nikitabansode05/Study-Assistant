// Base URL of the FastAPI backend. Override with VITE_API_BASE in frontend/.env.
export const API_BASE = (import.meta.env.VITE_API_BASE || 'http://10.160.0.3:8000').replace(/\/+$/, '')

// Mentor session token. Kept in memory only (never localStorage/sessionStorage/cookies),
// so a page reload always returns to the default student view.
let mentorToken = null
export const setMentorToken = (token) => { mentorToken = token || null }

export class ApiError extends Error {
  constructor(message, status = 0, path = '') {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.path = path
  }
}

function formatDetail(detail) {
  if (!detail) return ''
  if (typeof detail === 'string') return detail
  // FastAPI validation errors (422) return a list of {loc, msg} objects.
  if (Array.isArray(detail)) {
    return detail.map(d => {
      const field = Array.isArray(d?.loc) ? d.loc.filter(p => p !== 'body').join('.') : ''
      return field ? `${field}: ${d?.msg}` : (d?.msg || JSON.stringify(d))
    }).join('; ')
  }
  return typeof detail === 'object' ? JSON.stringify(detail) : String(detail)
}

async function request(path, options = {}, { auth = false } = {}) {
  const headers = { ...(options.headers || {}) }
  if (auth && mentorToken) headers.Authorization = `Bearer ${mentorToken}`

  let response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new ApiError(
      `Cannot reach the backend at ${API_BASE}. Make sure the FastAPI server is running (START_BACKEND_WINDOWS.bat).`,
      0,
      path,
    )
  }

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    let message = formatDetail(data.detail)
    if (response.status === 404 && (!message || message === 'Not Found')) {
      message = `API route not found: ${options.method || 'GET'} ${path} (404). Check that VITE_API_BASE points to this project's backend (${API_BASE}).`
    }
    throw new ApiError(message || `Request failed (${response.status})`, response.status, path)
  }
  return data
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

// ---- public
export const getHealth = () => request('/health')
export const askQuestion = (question, history = [], studentId = '') => request(
  '/chat',
  json('POST', {
    question,
    history,
    ...(studentId.trim() ? { student_id: studentId.trim() } : {}),
  }),
)

// ---- mentor auth
export const loginMentor = (userId, password) => request('/auth/login', json('POST', { user_id: userId, password }))
export const logoutMentor = () => request('/auth/logout', { method: 'POST' }, { auth: true })

// ---- mentor-only document management (backend requires the bearer token)
export const getDocuments = () => request('/documents', {}, { auth: true })

// The multipart field name must be "file" to match FastAPI's `file: UploadFile = File(...)`.
// `filename` lets folder imports send the relative path (e.g. docs/intro.md) for clearer sources.
export const uploadDocument = (file, filename) => {
  const body = new FormData()
  body.append('file', file, filename || file.name)
  return request('/documents/upload', { method: 'POST', body }, { auth: true })
}

export const uploadRepositoryZip = (file) => {
  const body = new FormData()
  body.append('file', file)
  return request('/repositories/upload-zip', { method: 'POST', body }, { auth: true })
}

export const importRepository = (url) => request('/repositories/import', json('POST', { url }), { auth: true })

export const deleteDocument = (id) => request(`/documents/${encodeURIComponent(id)}`, { method: 'DELETE' }, { auth: true })
