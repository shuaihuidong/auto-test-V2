import { get, post, put, del } from './request'

export interface Variable {
  id: number
  name: string
  value: any
  scope: 'global' | 'project' | 'script'
  type: 'string' | 'number' | 'boolean' | 'json'
  description: string
  is_sensitive: boolean
  project: number | null
  script: number | null
  created_at: string
  updated_at: string
}

export const variableApi = {
  getList: (params?: Record<string, any>): Promise<{ results: Variable[]; count: number }> =>
    get('/variables/', params),

  getByProject: (projectId: number): Promise<Variable[]> =>
    get('/variables/by_project/', { project_id: projectId }),

  getByScript: (scriptId: number): Promise<Variable[]> =>
    get('/variables/by_script/', { script_id: scriptId }),

  create: (data: Partial<Variable>): Promise<Variable> =>
    post('/variables/', data),

  update: (id: number, data: Partial<Variable>): Promise<Variable> =>
    put(`/variables/${id}/`, data),

  delete: (id: number): Promise<void> =>
    del(`/variables/${id}/`),
}
