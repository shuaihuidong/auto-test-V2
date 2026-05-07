export interface User {
  id: number
  username: string
  email: string
  role: 'super_admin' | 'admin' | 'tester' | 'user' | 'guest'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LoginForm {
  username: string
  password: string
}

export interface LoginResponse {
  message: string
  user: User
  token: string
}
