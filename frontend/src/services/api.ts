import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Inyectar token en cada request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Refrescar token si expira (401)
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    // Las llamadas de autenticación quedan fuera de esta lógica: un 401 en el login
    // o el refresh es "credenciales incorrectas", no "sesión expirada". Sin esto, un
    // login fallido recargaba la página y borraba el formulario (correo incluido).
    const esAuth = typeof original?.url === 'string' &&
      (original.url.includes('/auth/login') || original.url.includes('/auth/refresh'))
    if (error.response?.status === 401 && !original._retry && !esAuth) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
