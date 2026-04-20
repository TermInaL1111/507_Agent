<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-box">
        <div class="login-logo">
          <el-avatar :size="80" src="https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg" />
          <h2>用户登录</h2>
          <p class="subtitle">AI智能助手系统</p>
        </div>
        
        <el-form 
          ref="loginForm"
          :model="form"
          :rules="rules"
          @submit.prevent="onSubmit"
          class="login-form"
          label-position="top"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
            />
          </el-form-item>
          
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="onSubmit"
            />
          </el-form-item>
          
          <el-form-item>
            <el-button 
              type="primary" 
              size="large" 
              class="submit-btn"
              :loading="loading"
              @click="onSubmit"
            >
              登录
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="register-link">
          还没有账号？<el-link type="primary" @click="goToRegister">去注册</el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Lock } from '@element-plus/icons-vue';
import { useUserStore } from '../store/user';

const router = useRouter();
const userStore = useUserStore();
const loginForm = ref(null);
const loading = ref(false);

const form = reactive({
  username: '',
  password: ''
});

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
};

const onSubmit = async () => {
  const valid = await loginForm.value.validate().catch(() => false);
  if (!valid) return;
  
  loading.value = true;
  
  try {
    const result = await userStore.login({
      username: form.username,
      password: form.password
    });
    
    if (result.success) {
      ElMessage.success(result.message);
      router.push('/ai-chat');
    } else {
      ElMessage.error(result.message);
    }
  } catch (error) {
    ElMessage.error('登录失败，请稍后再试');
  } finally {
    loading.value = false;
  }
};

const goToRegister = () => {
  router.push('/register');
};
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-container {
  width: 100%;
  max-width: 480px;
  padding: 20px;
}

.login-box {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.login-logo {
  text-align: center;
  margin-bottom: 30px;
}

.login-logo h2 {
  margin-top: 16px;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.subtitle {
  color: #909399;
  font-size: 14px;
  margin-top: 8px;
}

.login-form {
  width: 100%;
}

.submit-btn {
  width: 100%;
  margin-top: 10px;
}

.register-link {
  text-align: center;
  margin-top: 20px;
  color: #606266;
  font-size: 14px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-input__wrapper) {
  padding: 4px 11px;
}
</style>