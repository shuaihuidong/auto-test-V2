<template>
  <div class="project-members">
    <div class="list-header">
      <a-space>
        <span>共 {{ members.length }} 名成员</span>
      </a-space>
      <a-button type="primary" @click="showAddModal">
        <PlusOutlined /> 添加成员
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="members"
      :loading="loading"
      :pagination="false"
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'user'">
          <a-space>
            <a-avatar>{{ record.username?.charAt(0).toUpperCase() }}</a-avatar>
            <span>{{ record.username }}</span>
            <a-tag v-if="record.is_owner" color="gold">所有者</a-tag>
          </a-space>
        </template>

        <template v-else-if="column.key === 'role'">
          <a-tag :color="getRoleColor(record.role)">
            {{ getRoleLabel(record.role) }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'joined_at'">
          {{ formatDate(record.joined_at) }}
        </template>

        <template v-else-if="column.key === 'actions'">
          <a-space>
            <a-button
              v-if="!record.is_owner"
              type="link"
              size="small"
              @click="changeRole(record)"
            >
              变更角色
            </a-button>
            <a-popconfirm
              v-if="!record.is_owner"
              title="确定要移除此成员吗？"
              @confirm="removeMember(record)"
            >
              <a-button type="link" size="small" danger>移除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 添加成员对话框 -->
    <a-modal
      v-model:open="addModalVisible"
      title="添加成员"
      width="500px"
      @ok="handleAddOk"
    >
      <a-form layout="vertical">
        <a-form-item label="选择用户" required>
          <a-select
            v-model:value="selectedUserId"
            show-search
            :filter-option="filterOption"
            placeholder="搜索用户名"
            style="width: 100%"
            :options="availableUsers"
            :field-names="{ label: 'label', value: 'value' }"
          >
            <template #option="{ label, email }">
              <div>
                <div>{{ label }}</div>
                <small style="color: #999">{{ email }}</small>
              </div>
            </template>
          </a-select>
        </a-form-item>

        <a-form-item label="角色" required>
          <a-select v-model:value="selectedRole" style="width: 100%">
            <a-select-option value="member">普通成员</a-select-option>
            <a-select-option value="admin">管理员</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 变更角色对话框 -->
    <a-modal
      v-model:open="roleModalVisible"
      title="变更角色"
      width="400px"
      @ok="handleRoleOk"
    >
      <a-form layout="vertical">
        <a-form-item label="角色" required>
          <a-select v-model:value="newRole" style="width: 100%">
            <a-select-option value="member">普通成员</a-select-option>
            <a-select-option value="admin">管理员</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { userApi } from '@/api/user'
import { projectApi, type ProjectMember } from '@/api/project'

interface Props {
  projectId: number
}

const props = defineProps<Props>()

const loading = ref(false)
const members = ref<ProjectMember[]>([])
const availableUsers = ref<any[]>([])

const addModalVisible = ref(false)
const roleModalVisible = ref(false)
const selectedUserId = ref<number>()
const selectedRole = ref('member')
const newRole = ref('member')
const editingMemberId = ref<string | number>()

const columns = [
  { title: '用户', key: 'user', ellipsis: true },
  { title: '角色', key: 'role', width: 120 },
  { title: '加入时间', key: 'joined_at', width: 140 },
  { title: '操作', key: 'actions', width: 140, fixed: 'right' }
]

async function loadMembers() {
  loading.value = true
  try {
    const data = await projectApi.getMembers(props.projectId)
    members.value = data
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function loadAvailableUsers() {
  try {
    const data = await userApi.getList()
    // 转换为下拉框需要的格式
    const memberUserIds = members.value.map(m => m.user_id || m.id)
    availableUsers.value = (data.results || [])
      .filter((u: any) => !memberUserIds.includes(u.id))
      .map((u: any) => ({
        label: u.username,
        value: u.id,
        email: u.email,
        username: u.username
      }))
  } catch (error) {
    availableUsers.value = []
  }
}

function showAddModal() {
  selectedUserId.value = undefined
  selectedRole.value = 'member'
  loadAvailableUsers()
  addModalVisible.value = true
}

async function handleAddOk() {
  if (!selectedUserId.value) {
    message.error('请选择用户')
    return
  }

  loading.value = true
  try {
    await projectApi.addMember(props.projectId, {
      user: selectedUserId.value,
      role: selectedRole.value
    })
    message.success('添加成功')
    addModalVisible.value = false
    loadMembers()
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function changeRole(record: ProjectMember) {
  editingMemberId.value = record.id
  newRole.value = record.role
  roleModalVisible.value = true
}

async function handleRoleOk() {
  if (!editingMemberId.value) {
    message.error('无效的成员ID')
    return
  }

  loading.value = true
  try {
    await projectApi.changeMemberRole(props.projectId, Number(editingMemberId.value), newRole.value)
    message.success('角色变更成功')
    roleModalVisible.value = false
    loadMembers()
  } catch (error) {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

async function removeMember(record: ProjectMember) {
  try {
    await projectApi.removeMember(props.projectId, Number(record.id))
    message.success('移除成功')
    loadMembers()
  } catch (error) {
    // 错误已由拦截器处理
  }
}

function getRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    owner: '所有者',
    admin: '管理员',
    member: '普通成员'
  }
  return labels[role] || role
}

function getRoleColor(role: string): string {
  const colors: Record<string, string> = {
    owner: 'gold',
    admin: 'blue',
    member: 'default'
  }
  return colors[role] || 'default'
}

function formatDate(date: string): string {
  return dayjs(date).format('YYYY-MM-DD')
}

function filterOption(input: string, option: any): boolean {
  const label = option.label || option.username || ''
  return label.toLowerCase().includes(input.toLowerCase())
}

onMounted(() => {
  loadMembers()
})

defineExpose({
  refresh: loadMembers
})
</script>

<style scoped>
.project-members {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}
</style>
