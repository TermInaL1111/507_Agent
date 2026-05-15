<template>
  <div class="success-page">
    <header class="page-header">
      <div>
        <h1>学生成功中心</h1>
        <p>汇总课程、日程、校园通知和 AI 建议，帮助你掌握今天和近期需要关注的事项。</p>
      </div>
      <div class="header-actions">
        <el-button :loading="loading" @click="loadOverview">重新加载</el-button>
        <el-button type="primary" :loading="generating" @click="generateSuggestions">生成 AI 建议</el-button>
        <el-button type="success" @click="openCreateDialog">新增任务</el-button>
      </div>
    </header>

    <section class="stat-grid">
      <div class="stat-card">
        <span>今日待办</span>
        <strong>{{ overview.todayTasks.length }}</strong>
      </div>
      <div class="stat-card">
        <span>即将截止</span>
        <strong>{{ overview.upcomingTasks.length }}</strong>
      </div>
      <div class="stat-card warn">
        <span>已逾期</span>
        <strong>{{ overview.overdueTasks.length }}</strong>
      </div>
      <div class="stat-card ai">
        <span>AI 建议</span>
        <strong>{{ overview.stats.aiSuggestions || 0 }}</strong>
      </div>
    </section>

    <section class="content-grid">
      <main class="main-column">
        <div class="section-head">
          <h2>今日任务</h2>
          <el-select v-model="filters.status" clearable placeholder="状态" size="small" @change="loadTasks">
            <el-option label="待处理" value="pending" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已完成" value="completed" />
            <el-option label="已忽略" value="ignored" />
          </el-select>
        </div>
        <el-empty v-if="!overview.todayTasks.length" description="今天暂无待办" />
        <article v-for="task in overview.todayTasks" :key="task.id" class="task-item">
          <div>
            <div class="task-title">{{ task.title }}</div>
            <div class="task-meta">
              <el-tag size="small" :type="priorityTag(task.priority)">{{ priorityText(task.priority) }}</el-tag>
              <span>{{ formatDate(task.due_at) }}</span>
              <span>{{ sourceText(task.source_type) }}</span>
            </div>
            <p v-if="task.description">{{ task.description }}</p>
          </div>
          <div class="task-actions">
            <el-button size="small" type="success" plain @click="updateStatus(task, 'completed')">完成</el-button>
            <el-button size="small" plain @click="updateStatus(task, 'ignored')">忽略</el-button>
          </div>
        </article>

        <div class="section-head with-gap">
          <h2>全部任务</h2>
          <div class="filters">
            <el-select v-model="filters.task_type" clearable placeholder="类型" size="small" @change="loadTasks">
              <el-option label="课程" value="course" />
              <el-option label="日程" value="schedule" />
              <el-option label="校园通知" value="campus_notice" />
              <el-option label="培养方案" value="cultivation_plan" />
              <el-option label="手动" value="manual" />
              <el-option label="AI 建议" value="ai_suggestion" />
            </el-select>
            <el-select v-model="filters.priority" clearable placeholder="优先级" size="small" @change="loadTasks">
              <el-option label="低" value="low" />
              <el-option label="中" value="medium" />
              <el-option label="高" value="high" />
              <el-option label="紧急" value="urgent" />
            </el-select>
          </div>
        </div>
        <el-table :data="tasks" v-loading="taskLoading" size="small" class="task-table">
          <el-table-column prop="title" label="任务" min-width="180" />
          <el-table-column label="截止" width="150">
            <template #default="{ row }">{{ formatDate(row.due_at) }}</template>
          </el-table-column>
          <el-table-column label="来源" width="110">
            <template #default="{ row }">{{ sourceText(row.source_type) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">{{ statusText(row.status) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="success" @click="updateStatus(row, 'completed')">完成</el-button>
              <el-button link @click="updateStatus(row, 'ignored')">忽略</el-button>
              <el-button link type="danger" @click="deleteTask(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </main>

      <aside class="side-column">
        <section class="panel">
          <h2>AI 建议任务</h2>
          <el-empty v-if="!overview.aiSuggestions.length" description="暂无待确认建议" />
          <div v-for="task in overview.aiSuggestions" :key="task.id" class="suggestion">
            <strong>{{ task.title }}</strong>
            <p>{{ task.metadata?.summary || task.description }}</p>
            <div class="suggestion-actions">
              <el-button size="small" type="primary" @click="confirmTask(task)">确认</el-button>
              <el-button size="small" @click="updateStatus(task, 'ignored')">忽略</el-button>
            </div>
          </div>
        </section>

        <section class="panel">
          <h2>未来 7 天时间线</h2>
          <el-empty v-if="!overview.timeline.length" description="暂无近期事项" />
          <div v-for="(item, index) in overview.timeline" :key="index" class="timeline-item">
            <span class="timeline-date">{{ item.date }} {{ item.time }}</span>
            <strong>{{ item.title }}</strong>
            <small>{{ sourceText(item.source) }}</small>
          </div>
        </section>
      </aside>
    </section>

    <el-dialog v-model="dialogVisible" title="新增任务" width="460px">
      <el-form :model="form" label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker v-model="form.due_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createTask">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { apiConfig } from '../config/api'
import { useUserStore } from '../store/user'

const userStore = useUserStore()
const overview = reactive({ todayTasks: [], upcomingTasks: [], overdueTasks: [], aiSuggestions: [], timeline: [], stats: {} })
const tasks = ref([])
const loading = ref(false)
const taskLoading = ref(false)
const generating = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const filters = reactive({ status: '', task_type: '', priority: '' })
const form = reactive({ title: '', description: '', due_at: '', priority: 'medium' })

const headers = () => ({ Authorization: `Bearer ${userStore.getToken}` })

const loadOverview = async () => {
  loading.value = true
  try {
    const resp = await axios.get(apiConfig.endpoints.studentSuccessOverview, { headers: headers() })
    Object.assign(overview, resp.data.data || {})
  } catch (error) {
    ElMessage.error('学生成功中心加载失败')
  } finally {
    loading.value = false
  }
}

const loadTasks = async () => {
  taskLoading.value = true
  try {
    const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value))
    const resp = await axios.get(apiConfig.endpoints.studentSuccessTasks, { headers: headers(), params })
    tasks.value = resp.data.data?.items || []
  } catch (error) {
    ElMessage.error('任务列表加载失败')
  } finally {
    taskLoading.value = false
  }
}

const generateSuggestions = async () => {
  generating.value = true
  try {
    const resp = await axios.post(apiConfig.endpoints.studentSuccessGenerate, {
      sources: ['schedule', 'campus_channel', 'cultivation_plan'],
      days: 7,
    }, { headers: headers() })
    ElMessage.success(`已生成 ${resp.data.data?.generated_count || 0} 条建议`)
    await refreshAll()
  } catch (error) {
    ElMessage.error('生成建议失败')
  } finally {
    generating.value = false
  }
}

const updateStatus = async (task, status) => {
  try {
    await axios.patch(`${apiConfig.endpoints.studentSuccessTasks}/${task.id}`, { status }, { headers: headers() })
    await refreshAll()
  } catch (error) {
    ElMessage.error('任务状态更新失败')
  }
}

const confirmTask = async (task) => {
  try {
    await axios.post(`${apiConfig.endpoints.studentSuccessTasks}/${task.id}/confirm`, {}, { headers: headers() })
    ElMessage.success('建议任务已确认')
    await refreshAll()
  } catch (error) {
    ElMessage.error('确认失败')
  }
}

const deleteTask = async (task) => {
  try {
    await axios.delete(`${apiConfig.endpoints.studentSuccessTasks}/${task.id}`, { headers: headers() })
    await refreshAll()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const openCreateDialog = () => {
  Object.assign(form, { title: '', description: '', due_at: '', priority: 'medium' })
  dialogVisible.value = true
}

const createTask = async () => {
  if (!form.title.trim()) {
    ElMessage.warning('请填写任务标题')
    return
  }
  saving.value = true
  try {
    await axios.post(apiConfig.endpoints.studentSuccessTasks, { ...form, task_type: 'manual' }, { headers: headers() })
    dialogVisible.value = false
    ElMessage.success('任务已创建')
    await refreshAll()
  } catch (error) {
    ElMessage.error('任务创建失败')
  } finally {
    saving.value = false
  }
}

const refreshAll = async () => {
  await Promise.all([loadOverview(), loadTasks()])
}

const formatDate = (value) => value ? new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '未设置'
const priorityText = (value) => ({ low: '低', medium: '中', high: '高', urgent: '紧急' }[value] || value)
const statusText = (value) => ({ pending: '待处理', confirmed: '已确认', completed: '已完成', ignored: '已忽略', expired: '已过期' }[value] || value)
const sourceText = (value) => ({ schedule: '课表日程', consultation_log: '咨询日志', campus_channel: '校园频道', cultivation_plan: '培养方案', manual: '手动', ai_chat: 'AI对话', document: '文书', other: '其他' }[value] || value)
const priorityTag = (value) => ({ low: 'info', medium: '', high: 'warning', urgent: 'danger' }[value] || '')

onMounted(refreshAll)
</script>

<style scoped>
.success-page {
  padding: 24px;
  color: #1f2937;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: 24px;
}

.page-header p {
  margin: 0;
  color: #6b7280;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border: 1px solid #ebe7df;
  border-radius: 8px;
  padding: 18px;
}

.stat-card span {
  display: block;
  color: #6b7280;
  margin-bottom: 8px;
}

.stat-card strong {
  font-size: 28px;
}

.stat-card.warn strong {
  color: #dc2626;
}

.stat-card.ai strong {
  color: #2563eb;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
}

.main-column,
.panel {
  background: #fff;
  border: 1px solid #ebe7df;
  border-radius: 8px;
  padding: 18px;
}

.side-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-head h2,
.panel h2 {
  margin: 0;
  font-size: 17px;
}

.with-gap {
  margin-top: 22px;
}

.filters {
  display: flex;
  gap: 8px;
}

.task-item,
.suggestion,
.timeline-item {
  border-top: 1px solid #f0ede7;
  padding: 12px 0;
}

.task-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.task-title {
  font-weight: 700;
  margin-bottom: 8px;
}

.task-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  color: #6b7280;
  font-size: 13px;
}

.task-item p,
.suggestion p {
  color: #6b7280;
  margin: 8px 0 0;
  line-height: 1.6;
}

.task-actions,
.suggestion-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.task-table {
  width: 100%;
}

.timeline-date {
  display: block;
  color: #6b7280;
  font-size: 12px;
  margin-bottom: 4px;
}

.timeline-item strong {
  display: block;
  margin-bottom: 4px;
}

.timeline-item small {
  color: #8b8b8b;
}

@media (max-width: 1080px) {
  .content-grid,
  .stat-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}
</style>
