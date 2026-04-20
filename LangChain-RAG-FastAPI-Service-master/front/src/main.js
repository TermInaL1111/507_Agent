import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from './store'

// 导入 Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// 导入全局样式
import './style.css'

// 引入国际化
import { setupI18n } from './i18n'

const app = createApp(App)

// 注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 设置i18n
const i18n = setupI18n()
app.use(i18n)

// 使用 Element Plus
app.use(ElementPlus)

// 使用路由和状态管理
app.use(router)
app.use(pinia)

app.mount('#app')

// 初始化主题
import { useThemeStore } from './store/theme'
const themeStore = useThemeStore()
themeStore.initTheme()
