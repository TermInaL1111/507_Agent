<template>
  <div class="my-page page-container">
    <el-card class="my-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('my.title') }}</span>
        </div>
      </template>

      <div class="user-section" v-if="isLogin">
        <el-avatar :size="80" :src="avatarUrl" />
        <div class="user-info">
          <div class="username">{{ userInfo?.username }}</div>
          <div class="desc">{{ userBio }}</div>
        </div>
        <el-button type="text" @click="goToProfile">
          个人资料
        </el-button>
      </div>

      <div class="user-section" v-else>
        <el-avatar :size="80" src="https://avatars.githubusercontent.com/u/14048127?s=200&v=4" />
        <div class="user-info">
          <div class="username">{{ $t('my.notLoggedIn') }}</div>
          <div class="desc">
            <el-button type="primary" size="small" @click="goToLogin" style="margin-right: 8px">
              {{ $t('my.goToLogin') }}
            </el-button>
            <el-button size="small" @click="goToRegister">
              {{ $t('my.goToRegister') }}
            </el-button>
          </div>
        </div>
      </div>

      <el-divider />

      <div class="menu-row">
        <el-card class="menu-item" shadow="hover" @click="goToSettings">
          <el-icon><Setting /></el-icon>
          <span>{{ $t('my.settings') }}</span>
        </el-card>
        <el-card v-if="isLogin" class="menu-item danger" shadow="hover" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          <span>{{ $t('my.logout') }}</span>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Setting, SwitchButton } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'

const userStore = useUserStore()
const router = useRouter()
const { t } = useI18n()

const userInfo = computed(() => userStore.userInfo)
const isLogin = computed(() => userStore.getLoginStatus)
const userBio = computed(() => userStore.getUserBio || t('profile.bio'))

const avatarUrl = computed(() => {
  if (userInfo.value?.avatar) {
    return `http://localhost:8001${userInfo.value.avatar}`
  }
  return 'https://avatars.githubusercontent.com/u/14048127?s=200&v=4'
})

const goToLogin = () => {
  router.push('/login')
}

const goToRegister = () => {
  router.push('/register')
}

const goToProfile = () => {
  if (isLogin.value) {
    router.push('/profile')
  }
}

const goToSettings = () => {
  router.push('/settings')
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm(
      t('my.logout') + '?',
      t('common.confirm'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel') || '取消',
        type: 'warning'
      }
    )
    userStore.logout()
    ElMessage.success(t('my.logout') + '成功')
    router.push('/login')
  } catch {
    // 用户取消
  }
}

onMounted(async () => {
  if (isLogin.value) {
    try {
      await userStore.getUserInfoDetail()
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
  }
})
</script>

<style scoped>
.my-page {
  height: 100%;
}

.my-card {
  max-width: 900px;
  margin: 0 auto;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
}

.user-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
}

.user-info {
  flex: 1;
}

.user-info .username {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.user-info .desc {
  color: var(--text-color-secondary);
}

.menu-row {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}

.menu-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  cursor: pointer;
}

.menu-item.danger {
  color: var(--danger-color);
}
</style>