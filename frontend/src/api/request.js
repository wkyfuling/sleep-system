import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let isRefreshing = false
let pendingQueue = []

function runQueue(token, err) {
  pendingQueue.forEach(({ resolve, reject, config }) => {
    if (err) return reject(err)
    config.headers.Authorization = `Bearer ${token}`
    resolve(axios(config))
  })
  pendingQueue = []
}

request.interceptors.response.use(
  (resp) => resp.data,
  async (err) => {
    const { response, config } = err
    if (!response) {
      ElMessage.error('网络异常，请检查后端服务')
      return Promise.reject(err)
    }

    // 尝试刷新 token
    if (response.status === 401 && !config._retry) {
      const refresh = localStorage.getItem('refresh_token')
      if (!refresh || config.url?.includes('/auth/')) {
        // 登录/注册接口 401 直接向上抛；无 refresh token 直接抛
        const msg = response.data?.detail || '认证失败'
        return Promise.reject({ ...err, message: msg })
      }
      config._retry = true

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingQueue.push({ resolve, reject, config })
        })
      }
      isRefreshing = true
      try {
        const { data } = await axios.post(
          (import.meta.env.VITE_API_BASE_URL || '/api') + '/auth/refresh/',
          { refresh },
        )
        const newAccess = data.access
        localStorage.setItem('access_token', newAccess)
        runQueue(newAccess, null)
        config.headers.Authorization = `Bearer ${newAccess}`
        return axios(config).then((r) => r.data)
      } catch (e) {
        runQueue(null, e)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(e)
      } finally {
        isRefreshing = false
      }
    }

    const msg = response.data?.detail || Object.values(response.data || {})[0] || '请求失败'
    const text = Array.isArray(msg) ? msg[0] : msg
    ElMessage.error(typeof text === 'string' ? text : '请求失败')
    return Promise.reject(err)
  },
)

export default request
