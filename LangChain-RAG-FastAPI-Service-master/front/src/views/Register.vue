<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-box">
        <div class="register-logo">
          <el-avatar :size="80" src="https://avatars.githubusercontent.com/u/14048127?s=200&v=4" />
          <h2>用户注册</h2>
          <p class="subtitle">AI智能助手系统</p>
        </div>
        
        <el-form
          ref="registerForm"
          :model="form"
          :rules="rules"
          class="register-form"
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
          
          <el-form-item label="邮箱地址" prop="email">
            <el-input
              v-model="form.email"
              placeholder="请输入邮箱地址"
              size="large"
              :prefix-icon="Message"
            />
          </el-form-item>
          
          <el-form-item label="手机号码" prop="telephone">
            <el-input
              v-model="form.telephone"
              placeholder="请输入手机号码"
              size="large"
              :prefix-icon="Phone"
              maxlength="11"
            />
          </el-form-item>
          
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码（6-20位）"
              size="large"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          
          <el-form-item label="确认密码" prop="confirm_password">
            <el-input
              v-model="form.confirm_password"
              type="password"
              placeholder="请确认密码"
              size="large"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="register-btn"
              :loading="loading"
              @click="handleRegister"
            >
              {{ loading ? '注册中...' : '注册' }}
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="login-link">
          已有账号？<el-link type="primary" @click="goToLogin">去登录</el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Message, Phone, Lock } from '@element-plus/icons-vue';
import { useUserStore } from '../store/user';

const router = useRouter();
const userStore = useUserStore();
const registerForm = ref(null);

const loading = ref(false);

const form = reactive({
  username: '',
  email: '',
  telephone: '',
  password: '',
  confirm_password: ''
});

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'));
  } else {
    callback();
  }
};

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  telephone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号码', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度应为6-20位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
};

const handleRegister = async () => {
  const valid = await registerForm.value.validate().catch(() => false);
  if (!valid) return;
  
  loading.value = true;
  
  try {
    const result = await userStore.register(form);
    
    if (result.success) {
      ElMessage.success(result.message);
      setTimeout(() => {
        router.push('/login');
      }, 1500);
    } else {
      ElMessage.error(result.message);
    }
  } catch (error) {
    console.error('注册失败:', error);
    ElMessage.error('注册失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

const goToLogin = () => {
  router.push('/login');
};
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.register-container {
  width: 100%;
  max-width: 520px;
  padding: 20px;
}

.register-box {
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.register-logo {
  text-align: center;
  margin-bottom: 30px;
}

.register-logo h2 {
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

.register-form {
  width: 100%;
}

.register-btn {
  width: 100%;
  margin-top: 10px;
}

.login-link {
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