<template>
  <div class="sessions-page">
    <el-page-header title="会话管理" @back="goToAIChat">
      <template #content>
        <span class="page-title">会话管理</span>
      </template>
      <template #extra>
        <el-button type="primary" @click="createNewSession">
          <el-icon><Plus /></el-icon>
          新会话
        </el-button>
      </template>
    </el-page-header>
    
    <div class="sessions-content">
      <div class="session-toolbar">
        <el-tag effect="plain" type="info">会话总数：{{ sessionStore.sessions.length }}</el-tag>
        <el-button type="primary" link :loading="refreshing" @click="refreshSessions">
          <el-icon><Refresh /></el-icon>
          刷新列表
        </el-button>
      </div>

      <div v-if="sessionStore.isLoading" class="loading">
        <el-loading-spinner />
        <p>加载中...</p>
      </div>
      
      <el-empty
        v-else-if="sessionStore.sessions.length === 0"
        description="暂无会话记录"
      >
        <el-button type="primary" @click="createNewSession">
          创建新会话
        </el-button>
      </el-empty>
      
      <div v-else class="sessions-list">
        <el-card shadow="hover">
          <el-table
            :data="sessionStore.sessions"
            style="width: 100%"
            :row-class-name="getRowClass"
            @row-click="(row) => selectSession(row)"
          >
            <el-table-column label="会话标题" min-width="200">
              <template #default="{ row }">
                <div class="session-title">
                  <el-icon color="#409EFF"><ChatDotRound /></el-icon>
                  <span>{{ row.title || '新会话' }}</span>
                </div>
              </template>
            </el-table-column>
            
            <el-table-column label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatSessionTime(row.created_at) }}
              </template>
            </el-table-column>
            
            <el-table-column label="操作" width="120" align="center">
              <template #default="{ row }">
                <el-button
                  type="danger"
                  size="small"
                  plain
                  @click.stop="deleteSession(row.session_id)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>
    
    <!-- 新会话对话框 -->
    <el-dialog
      v-model="showNewSessionDialog"
      title="创建新会话"
      width="500px"
    >
      <el-form>
        <el-form-item label="请输入您的问题">
          <el-input
            v-model="newSessionQuery"
            type="textarea"
            :rows="4"
            placeholder="请输入您的问题..."
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewSessionDialog = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="confirmNewSession"
          :disabled="!newSessionQuery.trim()"
        >
          开始对话
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, ChatDotRound, Delete, Refresh } from '@element-plus/icons-vue';
import { useSessionStore } from '../store/session';
import { useUserStore } from '../store/user';

const router = useRouter();
const route = useRoute();
const sessionStore = useSessionStore();
const userStore = useUserStore();

const showNewSessionDialog = ref(false);
const newSessionQuery = ref('');
const refreshing = ref(false);

// 监听路由变化，确保每次访问会话管理页面时自动刷新会话列表
watch(() => route.path, async (newPath) => {
  if (newPath === '/sessions') {
    await loadSessions();
  }
});

// 返回AI对话页面
const goToAIChat = () => {
  router.push('/aichat');
};

// 获取行样式
const getRowClass = ({ row }) => {
  if (sessionStore.currentSession?.session_id === row.session_id) {
    return 'active-row';
  }
  return '';
};

// 加载会话列表
const loadSessions = async () => {
  // 检查是否登录
  if (!userStore.getLoginStatus) {
    ElMessage.warning('请先登录');
    router.push('/login');
    return;
  }
  
  // 获取用户ID（假设从用户信息中获取）
  if (!userStore.userInfo) {
    const result = await userStore.getUserInfoDetail();
    if (!result.success) {
      ElMessage.error('获取用户信息失败');
      return;
    }
  }
  
  if (userStore.userInfo) {
    // 尝试获取用户ID，支持不同的字段名
    const userId = userStore.userInfo.uuid || userStore.userInfo.id || userStore.userInfo.user_id;
    
    if (userId) {
      const sessionResult = await sessionStore.getUserSessions(userId);
      if (!sessionResult.success) {
        ElMessage.error(sessionResult.message || '获取会话列表失败');
      }
    } else {
      ElMessage.error('获取用户ID失败，请检查用户信息结构');
      console.error('用户信息中没有找到ID字段:', userStore.userInfo);
    }
  } else {
    ElMessage.error('获取用户信息失败');
  }
};

const refreshSessions = async () => {
  refreshing.value = true;
  try {
    await loadSessions();
    ElMessage.success('会话列表已刷新');
  } finally {
    refreshing.value = false;
  }
};

// 组件挂载时获取会话列表
onMounted(async () => {
  await loadSessions();
});

// 获取会话标题（使用第一条消息作为标题）
const getSessionTitle = (session) => {
  if (session.history && session.history.length > 0) {
    const firstMessage = session.history[0][0]; // 第一条用户消息
    return firstMessage.length > 20 ? firstMessage.substring(0, 20) + '...' : firstMessage;
  }
  return '新会话';
};

// 格式化会话时间
const formatSessionTime = (timeString) => {
  if (!timeString) return '';
  try {
    const date = new Date(timeString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    return timeString;
  }
};

// 选择会话
const selectSession = (session) => {
  // 跳转到带会话ID的路由
  router.push(`/aichat/${session.session_id}`);
};

// 删除会话
const deleteSession = async (sessionId) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个会话吗？删除后无法恢复',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    const result = await sessionStore.deleteSession(sessionId);
    if (result.success) {
      ElMessage.success('会话删除成功');
    } else {
      ElMessage.error(result.message || '删除失败');
    }
  } catch {
    // 用户取消删除
  }
};

// 打开新会话对话框
const createNewSession = () => {
  showNewSessionDialog.value = true;
};

// 确认创建新会话
const confirmNewSession = async () => {
  if (!newSessionQuery.value.trim()) return;
  
  const loadingInstance = ElMessage({
    message: '创建会话中...',
    type: 'info',
    duration: 0
  });
  
  try {
    const result = await sessionStore.createSession(newSessionQuery.value);
    if (result.success && result.data?.session_id) {
      ElMessage.success('会话创建成功');
      showNewSessionDialog.value = false;
      newSessionQuery.value = '';
      router.push(`/aichat/${result.data.session_id}`);
    } else {
      ElMessage.error(result.message || '创建会话失败');
    }
  } catch (error) {
    ElMessage.error('创建会话失败');
    console.error('创建会话失败:', error);
  } finally {
    loadingInstance.close();
  }
};
</script>

<style scoped>
.sessions-page {
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

:deep(.el-page-header) {
  margin-bottom: 20px;
}

.sessions-content {
  flex: 1;
}

.session-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #909399;
}

.loading p {
  margin-top: 16px;
}

.sessions-list {
  margin-top: 10px;
}

.session-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.active-row) {
  background-color: #ecf5ff !important;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>