import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { message } from 'ant-design-vue'

// API 基础地址 - 从环境变量读取
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const TOKEN_KEY = 'auth_token'

const instance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加 Token 认证
instance.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers.Authorization = `Token ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
instance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    const { response, config } = error
    if (response) {
      const { status, data } = response
      // 优先显示后端返回的具体错误消息
      const errorMsg = data.error || data.message || ''

      switch (status) {
        case 401:
          // 登录页面显示具体错误，其他页面显示通用消息并跳转
          if (window.location.pathname === '/login') {
            message.error(errorMsg || '用户名或密码错误')
          } else {
            message.error('未登录或登录已过期')
            window.location.href = '/login'
          }
          break
        case 403:
          message.error(errorMsg || '没有权限访问')
          break
        case 404:
          message.error(errorMsg || '请求的资源不存在')
          break
        case 500:
          message.error(errorMsg || '服务器错误')
          break
        default:
          message.error(errorMsg || '请求失败')
      }
    } else {
      message.error('网络连接失败')
    }
    return Promise.reject(error)
  }
)

export default instance

// 通用请求方法
export function request<T = any>(config: AxiosRequestConfig): Promise<T> {
  return instance.request(config)
}

export function get<T = any>(url: string, params?: any): Promise<T> {
  return instance.get(url, { params })
}

export function post<T = any>(url: string, data?: any): Promise<T> {
  return instance.post(url, data)
}

export function put<T = any>(url: string, data?: any): Promise<T> {
  return instance.put(url, data)
}

export function del<T = any>(url: string): Promise<T> {
  return instance.delete(url)
}
