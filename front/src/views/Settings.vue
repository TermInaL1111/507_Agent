<template>
  <div class="settings-page page-container">
    <div class="settings-wrap">
      <!-- 主题设置 -->
      <div class="setting-card">
        <h3 class="card-title">主题外观</h3>
        <p class="card-desc">选择适合你的界面配色方案</p>

        <div class="theme-grid">
          <div
            v-for="theme in themeList"
            :key="theme.id"
            class="theme-card"
            :class="{ active: currentTheme === theme.id }"
            @click="changeTheme(theme.id)"
          >
            <div class="theme-preview" :class="'preview-' + theme.id">
              <span class="preview-bar"></span>
              <span class="preview-content">
                <span class="preview-row long"></span>
                <span class="preview-row mid"></span>
                <span class="preview-row short"></span>
              </span>
            </div>
            <div class="theme-label">
              <strong>{{ theme.name }}</strong>
              <small>{{ theme.description }}</small>
            </div>
            <span v-if="currentTheme === theme.id" class="theme-badge">当前</span>
          </div>
        </div>
      </div>

      <!-- 语言设置 -->
      <div class="setting-card">
        <h3 class="card-title">语言偏好</h3>
        <p class="card-desc">界面显示语言</p>

        <el-radio-group v-model="currentLanguage" size="large">
          <el-radio-button
            v-for="lang in languageOptions"
            :key="lang.value"
            :value="lang.value"
          >
            {{ lang.label }}
          </el-radio-button>
        </el-radio-group>

        <div class="lang-actions">
          <el-button type="primary" @click="changeLanguage">应用语言</el-button>
        </div>
      </div>

      <div class="setting-card">
        <div class="setting-row">
          <div>
            <h3 class="card-title">根据咨询日志自动生成时间节点</h3>
            <p class="card-desc">
              开启后，系统可以根据你的咨询记录识别可能的重要时间节点，并生成日程推荐。关闭后，系统不会再根据咨询日志自动推荐或写入新的时间节点。
            </p>
          </div>
          <el-switch
            v-model="autoTimelineEnabled"
            :loading="settingsSaving"
            :disabled="settingsLoading"
            size="large"
            @change="saveAutoTimelineSetting"
          />
        </div>
        <div class="setting-status" :class="{ off: !autoTimelineEnabled }">
          {{ autoTimelineStatusText }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useThemeStore } from '../store/theme'
import { useLanguageStore } from '../store/language'
import { useUserStore } from '../store/user'
import { useI18n } from 'vue-i18n'
import { apiConfig } from '../config/api'

const themeStore = useThemeStore()
const languageStore = useLanguageStore()
const userStore = useUserStore()
const { t, locale } = useI18n()

const themeList = computed(() => themeStore.getAllThemes)
const currentTheme = computed(() => themeStore.getCurrentTheme)

onMounted(() => {
  themeStore.initTheme()
  loadUserSettings()
})

const changeTheme = (themeId) => {
  themeStore.setTheme(themeId)
  ElMessage.success(`已切换为 ${themeStore.getThemeConfig.name}`)
}

const currentLanguage = ref(languageStore.getCurrentLanguage)
const languageOptions = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' },
]

const autoTimelineEnabled = ref(true)
const settingsLoading = ref(false)
const settingsSaving = ref(false)

const autoTimelineStatusText = computed(() => {
  return autoTimelineEnabled.value
    ? '已开启。系统可以根据咨询日志识别时间节点并生成日程推荐。'
    : '已关闭。系统不会根据咨询日志自动推荐时间节点，也不会自动写入新的事项。'
})

const authHeaders = () => ({ Authorization: `Bearer ${userStore.getToken}` })

const loadUserSettings = async () => {
  if (!userStore.getLoginStatus || !userStore.getToken) return
  settingsLoading.value = true
  try {
    const resp = await axios.get(apiConfig.endpoints.userSettings, {
      headers: authHeaders(),
    })
    const data = resp.data?.data || resp.data || {}
    autoTimelineEnabled.value = Boolean(data.autoGenerateTimelineEnabled)
  } catch (error) {
    ElMessage.error('读取设置失败，请稍后重试')
  } finally {
    settingsLoading.value = false
  }
}

const saveAutoTimelineSetting = async (value) => {
  const previous = !value
  settingsSaving.value = true
  try {
    const resp = await axios.patch(
      apiConfig.endpoints.userSettings,
      { autoGenerateTimelineEnabled: value },
      { headers: authHeaders() },
    )
    const data = resp.data?.data || resp.data || {}
    autoTimelineEnabled.value = Boolean(data.autoGenerateTimelineEnabled)
    ElMessage.success('设置已保存')
  } catch (error) {
    autoTimelineEnabled.value = previous
    ElMessage.error('保存设置失败，已恢复原状态')
  } finally {
    settingsSaving.value = false
  }
}

const changeLanguage = () => {
  languageStore.setLanguage(currentLanguage.value)
  locale.value = currentLanguage.value
  ElMessage.success(t('settings.languageChanged'))
  window.location.reload()
}
</script>

<style scoped>
.settings-page {
  height: 100%;
  padding: 16px 0;
}

.settings-wrap {
  max-width: 780px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ---- 卡片 ---- */
.setting-card {
  background: #fff;
  border-radius: 12px;
  padding: 32px 36px;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.06);
}

.card-title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.card-desc {
  margin: 0 0 24px;
  font-size: 14px;
  color: #9ca3af;
}

.setting-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}

.setting-row .card-desc {
  max-width: 560px;
  margin-bottom: 16px;
  line-height: 1.7;
}

.setting-status {
  padding: 12px 14px;
  border-radius: 8px;
  color: #1f6b3f;
  background: #f0f9eb;
  border: 1px solid #d9f7be;
  font-size: 14px;
}

.setting-status.off {
  color: #92400e;
  background: #fff7ed;
  border-color: #fed7aa;
}

/* ---- 主题 ---- */
.theme-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.theme-card {
  position: relative;
  padding: 16px 14px 14px;
  border: 2px solid #ebeef5;
  border-radius: 12px;
  cursor: pointer;
  text-align: center;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.theme-card:hover {
  border-color: #a0cfff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.08);
}

.theme-card.active {
  border-color: #409eff;
  box-shadow: 0 2px 14px rgba(64, 158, 255, 0.15);
}

/* 模拟预览窗 */
.theme-preview {
  display: flex;
  height: 72px;
  border-radius: 8px;
  overflow: hidden;
  margin: 0 auto 12px;
  max-width: 200px;
}

.preview-bar {
  display: block;
  width: 30%;
  flex-shrink: 0;
  background: #e5e7eb;
}

.preview-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  padding: 12px 10px;
  background: #f9fafb;
}

.preview-row {
  display: block;
  height: 6px;
  border-radius: 3px;
  background: #e5e7eb;
}

.preview-row.long  { width: 90%; }
.preview-row.mid   { width: 60%; }
.preview-row.short { width: 35%; }

/* 各主题预览色 */
.preview-dark .preview-bar     { background: #1e1e1e; }
.preview-dark .preview-content { background: #141414; }
.preview-dark .preview-row     { background: #2a2a2a; }

.preview-blue .preview-bar     { background: #1677cc; }
.preview-blue .preview-content { background: #e6f4ff; }
.preview-blue .preview-row     { background: #bae0ff; }

.preview-green .preview-bar     { background: #389e0d; }
.preview-green .preview-content { background: #f6ffed; }
.preview-green .preview-row     { background: #d9f7be; }

.preview-light .preview-bar     { background: #d1d5db; }
.preview-light .preview-content { background: #fff; }
.preview-light .preview-row     { background: #e8e8e8; }

/* 标签 */
.theme-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.theme-label strong {
  font-size: 14px;
  color: #1f2937;
}

.theme-label small {
  font-size: 12px;
  color: #9ca3af;
}

.theme-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: 11px;
  color: #fff;
  background: #409eff;
  padding: 1px 8px;
  border-radius: 20px;
}

/* ---- 语言 ---- */
.lang-actions {
  margin-top: 16px;
}

/* 响应式：窄屏两列 */
@media (max-width: 640px) {
  .theme-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .setting-row {
    flex-direction: column;
  }
}
</style>
