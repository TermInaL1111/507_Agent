import { defineStore } from 'pinia';

const THEME_CONFIGS = {
  light: {
    name: '浅色模式',
    primaryColor: '#409EFF',
    description: '清爽明亮，适合日间使用',
  },
  dark: {
    name: '深色模式',
    primaryColor: '#409EFF',
    description: '护眼舒适，适合夜间使用',
  },
  blue: {
    name: '海洋蓝',
    primaryColor: '#1890ff',
    description: '宁静专业，科技感十足',
  },
  green: {
    name: '翡翠绿',
    primaryColor: '#52c41a',
    description: '清新自然，缓解视觉疲劳',
  }
};

export const useThemeStore = defineStore('theme', {
  state: () => ({
    currentTheme: localStorage.getItem('theme') || 'light',
  }),

  getters: {
    getCurrentTheme: (state) => state.currentTheme,
    getThemeConfig: (state) => THEME_CONFIGS[state.currentTheme] || THEME_CONFIGS.light,
    getAllThemes: () => Object.keys(THEME_CONFIGS).map(key => ({
      id: key,
      name: THEME_CONFIGS[key].name,
      primaryColor: THEME_CONFIGS[key].primaryColor,
      description: THEME_CONFIGS[key].description,
    }))
  },

  actions: {
    setTheme(themeName) {
      if (!THEME_CONFIGS[themeName]) return;
      this.currentTheme = themeName;
      localStorage.setItem('theme', themeName);
      this.applyTheme();
    },

    applyTheme() {
      const config = THEME_CONFIGS[this.currentTheme];
      const root = document.documentElement;

      // Element Plus 深色模式
      if (this.currentTheme === 'dark') {
        root.classList.add('dark');
        // 动态加载 Element Plus 深色主题 CSS
        import('element-plus/theme-chalk/dark/css-vars.css').catch(() => {});
      } else {
        root.classList.remove('dark');
      }

      // 设置主题色 CSS 变量
      root.style.setProperty('--el-color-primary', config.primaryColor);
      root.style.setProperty('--primary-color', config.primaryColor);
    },

    initTheme() {
      this.applyTheme();
    }
  }
});
