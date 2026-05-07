<template>
  <div class="profile-page page-container">
    <el-card class="profile-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>个人信息</span>
        </div>
      </template>

      <div class="profile-header">
        <el-avatar :size="80" :src="avatarUrl" />
        <div class="profile-basic">
          <div class="username">{{ userInfo?.username || '未设置' }}</div>
          <div class="email">{{ userInfo?.email || '未设置' }}</div>
        </div>
      </div>

      <el-descriptions column="2" border class="profile-desc">
        <el-descriptions-item label="用户ID">
          {{ userInfo?.id || userInfo?.uuid || '未设置' }}
        </el-descriptions-item>
        <el-descriptions-item label="手机号">
          {{ userInfo?.telephone || '未设置' }}
        </el-descriptions-item>
        <el-descriptions-item label="性别">
          {{ genderText }}
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ createTimeText }}
        </el-descriptions-item>
        <el-descriptions-item label="最后登录时间">
          {{ lastLoginText }}
        </el-descriptions-item>
        <el-descriptions-item label="个人简介" :span="2">
          {{ userBio }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()

// 初始化用户状态
onMounted(async () => {
  if (!userStore.getLoginStatus) {
    router.push('/login')
    return
  }

  try {
    const result = await userStore.getUserInfoDetail()
    if (!result?.success) {
      ElMessage.error(result?.message || '获取用户信息失败')
    }
  } catch (error) {
    console.error('获取用户信息失败:', error)
    ElMessage.error('获取用户信息失败')
  }
})

const userInfo = computed(() => userStore.userInfo)
const userBio = computed(() => userStore.userInfo?.bio || '暂无简介')

const avatarUrl = computed(() => {
  if (userInfo.value?.avatar) {
    return `http://localhost:8001${userInfo.value.avatar}`
  }
  return 'https://avatars.githubusercontent.com/u/14048127?s=200&v=4'
})

const genderText = computed(() => {
  const gender = userInfo.value?.gender
  switch (gender) {
    case 1:
      return '男'
    case 2:
      return '女'
    case 3:
      return '其他'
    default:
      return '未设置'
  }
})

const createTimeText = computed(() => {
  if (!userInfo.value?.create_time) return '未设置'
  const date = new Date(userInfo.value.create_time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
})

const lastLoginText = computed(() => {
  if (!userInfo.value?.last_login) return '未设置'
  const date = new Date(userInfo.value.last_login)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
})
</script>

<style scoped>
.profile-page {
  height: 100%;
}

.profile-card {
  max-width: 900px;
  margin: 0 auto;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.profile-basic .username {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.profile-basic .email {
  color: var(--text-color-secondary);
  font-size: 14px;
}

.profile-desc {
  margin-top: 8px;
}
</style>