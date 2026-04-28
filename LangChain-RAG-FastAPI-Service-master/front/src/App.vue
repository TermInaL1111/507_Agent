<template>
  <div class="app-container">
    <!-- 侧边导航栏 -->
    <aside class="sidebar" v-if="showSidebar">
      <div class="logo">
        <el-icon size="32" color="#409EFF"><ChatLineRound /></el-icon>
        <span class="logo-text">AI助手</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        class="sidebar-menu"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/aichat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI问答</span>
        </el-menu-item>
        
        <el-menu-item index="/sessions">
          <el-icon><ChatLineSquare /></el-icon>
          <span>会话管理</span>
        </el-menu-item>

        <el-menu-item index="/schedule">
          <el-icon><Calendar /></el-icon>
          <span>课表服务</span>
        </el-menu-item>

        <el-menu-item index="/course-plan">
          <el-icon><Reading /></el-icon>
          <span>课程规划</span>
        </el-menu-item>

        <el-menu-item index="/course-recommend">
          <el-icon><Notebook /></el-icon>
          <span>选课建议</span>
        </el-menu-item>

        <el-menu-item index="/campus-map">
          <el-icon><Location /></el-icon>
          <span>校园导航</span>
        </el-menu-item>

        <el-menu-item index="/document-assistant">
          <el-icon><Document /></el-icon>
          <span>文书辅助</span>
        </el-menu-item>

        <el-menu-item index="/knowledge-manage">
          <el-icon><Collection /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        
        <el-menu-item index="/profile">
          <el-icon><User /></el-icon>
          <span>个人中心</span>
        </el-menu-item>
        
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
      
      <div class="user-info">
        <el-dropdown @command="handleCommand">
          <span class="user-dropdown">
            <el-avatar :size="32" :src="userStore.userInfo?.avatar || ''" />
            <span class="username">{{ userStore.userInfo?.username || '未登录' }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人资料</el-dropdown-item>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="main-content" :class="{ 'no-sidebar': !showSidebar }">
      <router-view v-slot="{ Component }">
        <template v-if="$route.meta.keepAlive">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </template>
        <template v-else>
          <component :is="Component" />
        </template>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from './store/user'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 判断是否显示侧边栏（登录页和注册页不显示）
const showSidebar = computed(() => {
  return !['/login', '/register'].includes(route.path)
})

// 当前激活的菜单
const activeMenu = computed(() => {
  if (route.path.startsWith('/aichat')) {
    return '/aichat'
  }

  return route.path
})

// 处理下拉菜单命令
const handleCommand = (command) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'logout':
      userStore.logout()
      ElMessage.success('退出登录成功')
      router.push('/login')
      break
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 14px;
  height: 100%;
  width: 100%;
}

.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
}

/* 侧边栏 */
.sidebar {
  width: 210px;
  height: 100%;
  background-color: #304156;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-bottom: 1px solid #1f2d3d;
}

.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
}

.sidebar-menu .el-menu-item {
  height: 50px;
  line-height: 50px;
}

.user-info {
  height: 60px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  border-top: 1px solid #1f2d3d;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #bfcbd9;
}

.username {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 主内容区 */
.main-content {
  flex: 1;
  overflow: auto;
  background-color: #f0f2f5;
}

.main-content.no-sidebar {
  background-color: #fff;
}
</style>
