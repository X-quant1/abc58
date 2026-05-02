import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// ─── 请求拦截：自动携带 JWT token ───
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ─── 响应拦截 ───
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    // 401 → 未登录/token过期 → 跳转登录页
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 避免在登录页重复跳转
      if (!window.location.pathname.includes('/login')) {
        window.location.hash = '#/login'
      }
    }
    return Promise.reject(err)
  }
)

export default api
