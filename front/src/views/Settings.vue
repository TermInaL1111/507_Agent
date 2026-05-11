<template>
  <div class="settings-page page-container">
    <div class="settings-wrap">
      <!-- 主题设置 -->
      <div class="setting-card">
        <div class="card-title">主题外观</div>
        <div class="card-desc">选择适合你的界面配色方案</div>

        <div class="theme-grid">
          <div
            v-for="theme in themeList"
            :key="theme.id"
            class="theme-card"
            :class="{ active: currentTheme === theme.id }"
            @click="changeTheme(theme.id)"
          >
            <div class="theme-preview" :class="'preview-' + theme.id">
              <div class="preview-sidebar"></div>
              <div class="preview-main">
                <div class="preview-header"></div>
                <div class="preview-body">
                  <div class="preview-line w-80"></div>
                  <div class="preview-line w-60"></div>
                  <div class="preview-line w-90"></div>
                  <div class="preview-line w-40"></div>
                </div>
              </div>
            </div>
            <div class="theme-info">
              <span class="theme-name">{{ theme.name }}</span>
              <span class="theme-desc">{{ theme.description }}</span>
            </div>
            <el-icon v-if="currentTheme === theme.id" class="theme-check" color="#409EFF"><Check /></el-icon>
          </div>
        </div>
      </div>

      <!-- 语言设置 -->
      <div class="setting-card">
        <div class="card-title">语言偏好</div>
        <div class="card-desc">界面显示语言</div>

        <el-radio-group v-model="currentLanguage" class="lang-group">
          <el-radio-button v-for="lang in languageOptions" :key="lang.value" :value="lang.value">
            {{ lang.label }}
          </el-radio-button>
        </el-radio-group>

        <div class="card-actions">
          <el-button type="primary" @click="changeLanguage">应用语言</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { useThemeStore } from '../store/theme'
import { useLanguageStore } from '../store/language'
import { useI18n } from 'vue-i18n'

const themeStore = useThemeStore()
const languageStore = useLanguageStore()
const { t, locale } = useI18n()

const themeList = computed(() => themeStore.getAllThemes)
const currentTheme = computed(() => themeStore.getCurrentTheme)

onMounted(() => {
  themeStore.initTheme()
})

const changeTheme = (themeId) => {
  themeStore.setTheme(themeId)
  ElMessage.success(`已切换为 ${themeStore.getThemeConfig.name}`)
}

const currentLanguage = ref(languageStore.getCurrentLanguage)
const languageOptions = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' }
]

const changeLanguage = () => {
  languageStore.setLanguage(currentLanguage.value)
  locale.value = currentLanguage.value
  ElMessage.success(t('settings.languageChanged'))
  window.location.reload()
}
</script>

<style scoped>
.settings-page { height: 100%; }
.settings-wrap { max-width: 860px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; }

.setting-card {
  background: #fff; border-radius: 12px; padding: 28px 32px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}

.card-title { font-size: 18px; font-weight: 600; color: #303133; margin-bottom: 4px; }
.card-desc { font-size: 13px; color: #909399; margin-bottom: 20px; }

/* 主题卡片 */
.theme-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; }

.theme-card {
  position: relative; padding: 12px; border: 2px solid #EBEEF5; border-radius: 10px;
  cursor: pointer; transition: all 0.25s;
}
.theme-card:hover { border-color: #b3d8ff; transform: translateY(-2px); box-shadow: 0 4px 16px rgba(64,158,255,0.1); }
.theme-card.active { border-color: #409EFF; box-shadow: 0 4px 16px rgba(64,158,255,0.15); }

.theme-check { position: absolute; top: 8px; right: 10px; font-size: 20px; }

/* 预览小窗 */
.theme-preview { display: flex; height: 80px; border-radius: 6px; overflow: hidden; margin-bottom: 10px; }
.preview-sidebar { width: 28%; background: #e0e0e0; }
.preview-main { flex: 1; padding: 8px; background: #fff; display: flex; flex-direction: column; gap: 4px; }
.preview-header { height: 12px; background: #ddd; border-radius: 3px; margin-bottom: 4px; }
.preview-line { height: 6px; background: #e8e8e8; border-radius: 2px; }
.w-80 { width: 80%; } .w-60 { width: 60%; } .w-90 { width: 90%; } .w-40 { width: 40%; }

/* dark */
.preview-dark .preview-sidebar { background: #1e1e1e; }
.preview-dark .preview-main { background: #141414; }
.preview-dark .preview-header { background: #333; }
.preview-dark .preview-line { background: #2a2a2a; }

/* blue */
.preview-blue .preview-sidebar { background: #1677cc; }
.preview-blue .preview-main { background: #e6f4ff; }
.preview-blue .preview-header { background: #a8d4ff; }
.preview-blue .preview-line { background: #cce6ff; }

/* green */
.preview-green .preview-sidebar { background: #389e0d; }
.preview-green .preview-main { background: #f6ffed; }
.preview-green .preview-header { background: #b7eb8f; }
.preview-green .preview-line { background: #d9f7be; }

.theme-info { display: flex; flex-direction: column; gap: 2px; }
.theme-name { font-size: 14px; font-weight: 600; color: #303133; }
.theme-desc { font-size: 12px; color: #909399; }

/* 语言 */
.lang-group { display: block; margin-bottom: 12px; }
.card-actions { padding-top: 8px; }
</style>
