<template>
  <div class="profile-page page-container">
    <!-- 顶部用户卡片 -->
    <div class="profile-card-wrap">
      <div class="profile-banner">
        <div class="banner-bg"></div>
        <div class="banner-content">
          <el-avatar :size="88" :src="avatarUrl" class="profile-avatar" />
          <div class="profile-names">
            <span class="display-name">{{ userInfo?.username || '未设置' }}</span>
            <span class="display-id">ID: {{ userInfo?.id || userInfo?.uuid || '—' }}</span>
            <span class="display-date">注册于 {{ createTimeText }}</span>
          </div>
          <el-button class="edit-trigger" :icon="Edit" round @click="toggleEdit" v-if="!editing">
            编辑资料
          </el-button>
        </div>
      </div>

      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" class="profile-tabs">
        <el-tab-pane label="个人信息" name="info">
          <el-form
            ref="infoFormRef"
            :model="infoForm"
            :rules="infoRules"
            label-width="80px"
            :disabled="!editing"
            class="info-form"
          >
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="用户名" prop="username">
                  <el-input v-model="infoForm.username" maxlength="30" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="手机号" prop="telephone">
                  <el-input v-model="infoForm.telephone" maxlength="11" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="邮箱">
                  <el-input v-model="infoForm.email" disabled />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="性别">
                  <el-radio-group v-model="infoForm.gender">
                    <el-radio :value="1">男</el-radio>
                    <el-radio :value="2">女</el-radio>
                    <el-radio :value="3">其他</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="个人简介">
              <el-input v-model="infoForm.bio" type="textarea" :rows="3" maxlength="200" show-word-limit />
            </el-form-item>

            <el-form-item label="头像">
              <div class="avatar-row">
                <el-avatar :size="56" :src="avatarPreview || avatarUrl" />
                <el-upload
                  v-if="editing"
                  :show-file-list="false"
                  :before-upload="handleAvatarSelect"
                  accept="image/*"
                  class="avatar-upload-btn"
                >
                  <el-button size="small" :icon="Upload">更换头像</el-button>
                </el-upload>
              </div>
            </el-form-item>

            <div v-if="editing" class="form-actions">
              <el-button @click="cancelEdit">取消</el-button>
              <el-button type="primary" :loading="saving" @click="saveInfo">保存修改</el-button>
            </div>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="修改密码" name="password">
          <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="100px" class="pwd-form">
            <el-form-item label="当前密码" prop="oldPassword">
              <el-input v-model="pwdForm.oldPassword" type="password" show-password maxlength="30" />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input v-model="pwdForm.newPassword" type="password" show-password maxlength="30" />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirmPassword">
              <el-input v-model="pwdForm.confirmPassword" type="password" show-password maxlength="30" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="changingPwd" @click="savePassword">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Upload } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()

const editing = ref(false)
const saving = ref(false)
const changingPwd = ref(false)
const activeTab = ref('info')
const avatarPreview = ref('')

const infoFormRef = ref(null)
const pwdFormRef = ref(null)

// ── 用户信息 ──
onMounted(async () => {
  if (!userStore.getLoginStatus) {
    router.push('/login')
    return
  }
  try {
    await userStore.getUserInfoDetail()
  } catch {
    ElMessage.error('获取用户信息失败')
  }
})

const userInfo = computed(() => userStore.userInfo)

const avatarUrl = computed(() => {
  if (userInfo.value?.avatar) {
    return `http://localhost:8001${userInfo.value.avatar}`
  }
  return ''
})

const createTimeText = computed(() => {
  const t = userInfo.value?.create_time
  if (!t) return '—'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
})

const infoForm = reactive({
  username: '',
  email: '',
  telephone: '',
  gender: 1,
  bio: '',
})

const infoRules = {
  username: [
    { required: true, message: '用户名不能为空', trigger: 'blur' },
    { min: 2, max: 30, message: '用户名长度 2-30 个字符', trigger: 'blur' }
  ],
  telephone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号', trigger: 'blur' }
  ]
}

function syncFormFromUser() {
  infoForm.username = userInfo.value?.username || ''
  infoForm.email = userInfo.value?.email || ''
  infoForm.telephone = userInfo.value?.telephone || ''
  infoForm.gender = userInfo.value?.gender || 1
  infoForm.bio = userInfo.value?.bio || ''
}

// 初始化表单（延迟到 userInfo 加载后）
const initWatcher = setInterval(() => {
  if (userInfo.value) {
    clearInterval(initWatcher)
    syncFormFromUser()
  }
}, 100)

// ── 编辑模式 ──
function toggleEdit() {
  syncFormFromUser()
  editing.value = true
  activeTab.value = 'info'
}

function cancelEdit() {
  syncFormFromUser()
  editing.value = false
  avatarPreview.value = ''
}

async function saveInfo() {
  if (!infoFormRef.value) return
  try {
    await infoFormRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const res = await userStore.updateUserInfo({
      username: infoForm.username,
      telephone: infoForm.telephone,
      gender: infoForm.gender,
      bio: infoForm.bio,
    })
    if (res.success) {
      ElMessage.success('个人信息已更新')
      editing.value = false
      avatarPreview.value = ''
    } else {
      ElMessage.error(res.message || '更新失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + (e.message || '网络错误'))
  } finally {
    saving.value = false
  }
}

function handleAvatarSelect(file) {
  const reader = new FileReader()
  reader.onload = (e) => { avatarPreview.value = e.target.result }
  reader.readAsDataURL(file)
  return false // 阻止默认上传
}

// ── 修改密码 ──
const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const validateConfirm = (_rule, value, callback) => {
  if (value !== pwdForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const pwdRules = {
  oldPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 30, message: '密码长度 6-30 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

async function savePassword() {
  if (!pwdFormRef.value) return
  try {
    await pwdFormRef.value.validate()
  } catch {
    return
  }
  changingPwd.value = true
  try {
    const res = await userStore.updatePassword(pwdForm.oldPassword, pwdForm.newPassword, pwdForm.confirmPassword)
    if (res.success) {
      ElMessage.success('密码修改成功，请重新登录')
      pwdForm.oldPassword = ''
      pwdForm.newPassword = ''
      pwdForm.confirmPassword = ''
      setTimeout(() => {
        userStore.clearAuthState()
        router.push('/login')
      }, 1500)
    } else {
      ElMessage.error(res.message || '密码修改失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + (e.message || '网络错误'))
  } finally {
    changingPwd.value = false
  }
}
</script>

<style scoped>
.profile-page {
  height: 100%;
}

.profile-card-wrap {
  max-width: 860px;
  margin: 0 auto;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 16px rgba(0,0,0,0.06);
}

/* Banner */
.profile-banner {
  position: relative;
  padding: 36px 32px 28px;
}

.banner-bg {
  position: absolute;
  inset: 0;
  height: 120px;
  background: linear-gradient(135deg, #409EFF 0%, #66b1ff 50%, #a0cfff 100%);
  border-radius: 12px 12px 0 0;
}

.banner-content {
  position: relative;
  display: flex;
  align-items: center;
  gap: 20px;
  color: #fff;
}

.profile-avatar {
  border: 4px solid rgba(255,255,255,0.5);
  flex-shrink: 0;
}

.profile-names {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.display-name {
  font-size: 22px;
  font-weight: 700;
}

.display-id,
.display-date {
  font-size: 13px;
  opacity: 0.85;
}

.edit-trigger {
  flex-shrink: 0;
  background: rgba(255,255,255,0.2);
  border: 1px solid rgba(255,255,255,0.4);
  color: #fff;
}

.edit-trigger:hover {
  background: rgba(255,255,255,0.35);
  color: #fff;
}

/* Tabs */
.profile-tabs {
  padding: 0 32px 24px;
}

.info-form,
.pwd-form {
  max-width: 640px;
  padding-top: 8px;
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-upload-btn {
  display: inline-block;
}

.form-actions {
  display: flex;
  gap: 12px;
  padding-top: 8px;
  margin-left: 80px;
}
</style>
