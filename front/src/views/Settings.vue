<template>
  <div class="settings-page page-container">
    <el-card class="settings-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('settings.title') }}</span>
        </div>
      </template>

      <!-- 个性化设置 -->
      <el-divider content-position="left">{{ $t('settings.personalization') }}</el-divider>
      <div class="section">
        <div class="section-title">{{ $t('settings.themeCustomization') }}</div>
        <div class="theme-list">
          <div
            v-for="theme in themeList"
            :key="theme.id"
            class="theme-item"
            :class="{ active: currentTheme === theme.id }"
            @click="changeTheme(theme.id)"
          >
            <div class="theme-color" :style="{ backgroundColor: theme.primaryColor }"></div>
            <div class="theme-name">{{ theme.name }}</div>
          </div>
        </div>
      </div>

      <!-- 语言设置 -->
      <el-divider content-position="left">{{ $t('settings.languageSettings') }}</el-divider>
      <div class="section">
        <div class="section-title">{{ $t('settings.selectLanguage') }}</div>
        <el-radio-group v-model="currentLanguage" class="language-group">
          <el-radio-button
            v-for="lang in languageOptions"
            :key="lang.value"
            :label="lang.value"
          >
            {{ lang.label }}
          </el-radio-button>
        </el-radio-group>
        <el-button type="primary" class="language-apply" @click="changeLanguage">
          {{ $t('common.confirm') }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useThemeStore } from '../store/theme'
import { useI18n } from 'vue-i18n'
import { useLanguageStore } from '../store/language'

const themeStore = useThemeStore()
const languageStore = useLanguageStore()
const { t, locale } = useI18n()

// 主题相关
const themeList = computed(() => themeStore.getAllThemes)
const currentTheme = computed(() => themeStore.getCurrentTheme)

const changeTheme = (themeId) => {
  themeStore.setTheme(themeId)
  ElMessage.success(t('settings.themeChanged'))
}

// 语言相关
const currentLanguage = ref(languageStore.getCurrentLanguage)
const languageOptions = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' }
]

const changeLanguage = () => {
  languageStore.setLanguage(currentLanguage.value)
  locale.value = currentLanguage.value
  ElMessage.success(t('settings.languageChanged'))
  // 强制刷新页面以应用语言更改
  window.location.reload()
}
</script>

<style scoped>
.settings-page {
  height: 100%;
}

.settings-card {
  max-width: 900px;
  margin: 0 auto;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
}

.section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  color: var(--text-color-regular);
  margin-bottom: 12px;
}

.theme-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.theme-item {
  width: 120px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color-light);
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-item:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.theme-item.active {
  border-color: var(--primary-color);
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.3);
}

.theme-color {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-bottom: 8px;
}

.theme-name {
  font-size: 13px;
}

.language-group {
  margin-top: 8px;
}

.language-apply {
  margin-top: 16px;
}
</style>