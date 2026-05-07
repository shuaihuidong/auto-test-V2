import { get } from './request'

export interface Role {
  value: string
  label: string
  level: number
  permissions: string[]
  user_count: number
}

export interface RoleDetail extends Role {
  users: any[]
}

// 获取角色列表
export async function getRoleList(): Promise<{ results: Role[] }> {
  return get('/users/roles/')
}

// 获取角色详情
export async function getRoleDetail(role: string): Promise<RoleDetail> {
  return get(`/users/roles/${role}/`)
}

// 获取角色下的用户列表
export async function getRoleUsers(role: string): Promise<{ role: string; role_label: string; users: any[]; count: number }> {
  return get(`/users/roles/${role}/users/`)
}

// 导出 API 对象供组件使用
export const roleApi = {
  getList: getRoleList,
  getDetail: getRoleDetail,
  getUsers: getRoleUsers
}
