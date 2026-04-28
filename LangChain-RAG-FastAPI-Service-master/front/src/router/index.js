import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/aichat'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: {
      title: '登录',
      keepAlive: false
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: {
      title: '注册',
      keepAlive: false
    }
  },
  {
    path: '/aichat',
    name: 'AIChat',
    component: () => import('../views/AIChat.vue'),
    meta: {
      title: 'AI问答',
      keepAlive: true
    }
  },
  {
    path: '/schedule',
    name: 'Schedule',
    component: () => import('../views/Schedule.vue'),
    meta: {
      title: '课表服务',
      keepAlive: false
    }
  },
  {
    path: '/course-plan',
    name: 'CoursePlan',
    component: () => import('../views/CoursePlan.vue'),
    meta: {
      title: '课程规划',
      keepAlive: false
    }
  },
  {
    path: '/course-recommend',
    name: 'CourseRecommend',
    component: () => import('../views/CourseRecommend.vue'),
    meta: {
      title: '选课建议',
      keepAlive: false
    }
  },
  {
    path: '/campus-map',
    name: 'CampusMap',
    component: () => import('../views/CampusMap.vue'),
    meta: {
      title: '校园导航',
      keepAlive: false
    }
  },
  {
    path: '/document-assistant',
    name: 'DocumentAssistant',
    component: () => import('../views/DocumentAssistant.vue'),
    meta: {
      title: '文书辅助',
      keepAlive: false
    }
  },
  {
    path: '/knowledge-manage',
    name: 'KnowledgeManage',
    component: () => import('../views/KnowledgeManage.vue'),
    meta: {
      title: '知识库管理',
      keepAlive: false
    }
  },
  {
    path: '/aichat/:sessionId',
    name: 'AIChatWithSession',
    component: () => import('../views/AIChat.vue'),
    meta: {
      title: 'AI问答',
      keepAlive: true
    }
  },
  {
    path: '/my',
    name: 'My',
    component: () => import('../views/My.vue'),
    meta: {
      title: '我的',
      keepAlive: true
    }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: {
      title: '个人信息',
      keepAlive: false
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: {
      title: '设置',
      keepAlive: false
    }
  },
  {
    path: '/sessions',
    name: 'Sessions',
    component: () => import('../views/Sessions.vue'),
    meta: {
      title: '会话管理',
      keepAlive: true
    }
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title || '新闻资讯'
  
  // 直接允许访问所有页面
  next()
})

export default router