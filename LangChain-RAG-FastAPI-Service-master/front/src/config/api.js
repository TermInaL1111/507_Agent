/**
 * API配置文件
 * 包含API基础URL和所有API端点配置
 */

// API基础URL配置
export const apiConfig = {
  // 后端API基础URL（使用相对路径，通过Vite代理访问）
  baseURL: import.meta.env.VITE_BASE_URL || '',
  // 用户服务基础URL（使用相对路径，通过Vite代理访问）
  userBaseURL: import.meta.env.VITE_USER_BASE_URL || '',
  
  // API端点配置
  endpoints: {
    // 认证相关
    login: '/user/login/',
    logout: '/user/logout/',
    register: '/user/register/',
    profile: '/user/detail/',
    
    // 文件上传
    uploadFile: '/file/upload/',
    
    // AI对话相关
    agentQuery: '/api/agent/query',
    agentQueryStream: '/api/agent/query/stream',
    
    // RAG相关
    ragQuery: '/api/rag/query',
    
    // 会话管理
    getSession: '/api/session/',
    deleteSession: '/api/session/',
    getAllSessions: '/api/sessions',
    getUserSessions: '/api/sessions',
    
    // 向量数据库
    uploadSingleFile: '/api/vector/add/single',
    uploadMultipleFiles: '/api/vector/add/multiple',
    cleanVectors: '/api/vector/clean',
    
    // 文档重排序
    reorderDocuments: '/api/reorder',

    // 待新增：教师信息
    getTeachers: '/api/teachers',

    // 待新增：课表服务
    getTodaySchedule: '/api/schedule/today',
    getWeeklySchedule: '/api/schedule/week',
    getScheduleConflicts: '/api/schedule/conflicts',

    // 待新增：课程规划
    getPlanOverview: '/api/plan/overview',
    recommendPlan: '/api/plan/recommend',

    // 待新增：选课建议
    recommendCourseSelection: '/api/course/select/recommend',
    checkCoursePrerequisite: '/api/course/select/check-prerequisite',

    // 待新增：校园导航
    getCampusLocations: '/api/campus/locations',
    getCampusRoute: '/api/campus/route',

    // 待新增：帖子辅助
    summarizePosts: '/api/posts/summarize',
    classifyPosts: '/api/posts/classify',
    factCheckPosts: '/api/posts/fact-check',
    moderatePosts: '/api/posts/moderation',

    // 待新增：文书辅助
    generateDocument: '/api/docs/generate',
    checkDocument: '/api/docs/check',
    optimizeDocument: '/api/docs/optimize'
  }
}