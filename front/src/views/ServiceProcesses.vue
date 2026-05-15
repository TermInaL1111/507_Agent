<template>
  <div class="process-page">
    <header class="page-header">
      <div>
        <h1>办事流程</h1>
        <p>按步骤完成请假、报修、证明申请和场地预约等校园事务。没有真实系统接口时，仅生成指引、材料或提醒。</p>
      </div>
      <el-button :loading="loading" @click="loadAll">重新加载</el-button>
    </header>

    <el-tabs v-model="activeCategory" @tab-change="loadProcesses">
      <el-tab-pane label="全部" name="" />
      <el-tab-pane label="请假" name="leave" />
      <el-tab-pane label="报修" name="repair" />
      <el-tab-pane label="证明" name="certificate" />
      <el-tab-pane label="场地" name="venue" />
    </el-tabs>

    <section class="process-grid">
      <article v-for="process in processes" :key="process.id" class="process-card">
        <div class="card-head">
          <h2>{{ process.name }}</h2>
          <el-tag size="small">{{ categoryText(process.category) }}</el-tag>
        </div>
        <p>{{ process.description }}</p>
        <div class="meta">
          <span>办理部门：{{ process.department || '以官方通知为准' }}</span>
          <span>材料：{{ (process.required_materials || []).slice(0, 2).join('、') }}</span>
        </div>
        <div class="actions">
          <el-button @click="selectProcess(process)">查看</el-button>
          <el-button type="primary" @click="startProcess(process)">开始办理</el-button>
        </div>
      </article>
    </section>

    <section class="workspace">
      <div class="panel detail-panel">
        <template v-if="selected">
          <h2>{{ selected.name }}</h2>
          <p>{{ selected.description }}</p>
          <h3>材料清单</h3>
          <ul><li v-for="item in selected.required_materials" :key="item">{{ item }}</li></ul>
          <h3>办理步骤</h3>
          <ol><li v-for="item in selected.steps" :key="item">{{ item }}</li></ol>
          <h3>常见问题</h3>
          <div v-for="item in selected.faq" :key="item.q" class="faq">
            <strong>{{ item.q }}</strong>
            <p>{{ item.a }}</p>
          </div>
          <p class="source">来源：{{ selected.source_type }} / {{ selected.source_id }}。政策类内容请以学校官方最新通知为准。</p>
        </template>
        <el-empty v-else description="请选择一个流程查看详情" />
      </div>

      <div class="panel">
        <h2>我的流程</h2>
        <el-empty v-if="!instances.length" description="暂无流程实例" />
        <div v-for="instance in instances" :key="instance.id" class="instance">
          <strong>{{ instance.process?.name || '流程' }}</strong>
          <span>{{ statusText(instance.status) }} · 第 {{ instance.current_step + 1 }} 步</span>
          <div>
            <el-button size="small" @click="editInstance(instance)">继续办理</el-button>
            <el-button size="small" type="danger" plain @click="cancelInstance(instance)">取消</el-button>
          </div>
        </div>
      </div>
    </section>

    <el-dialog v-model="dialogVisible" title="流程办理" width="560px">
      <template v-if="currentInstance">
        <p class="dialog-subtitle">{{ currentInstance.process?.name }}</p>
        <el-steps :active="currentInstance.current_step" finish-status="success" simple>
          <el-step v-for="(step, index) in currentInstance.process?.steps || []" :key="index" :title="String(index + 1)" />
        </el-steps>
        <el-form :model="form" label-position="top" class="process-form">
          <el-form-item label="办理说明 / 申请内容">
            <el-input v-model="form.summary" type="textarea" :rows="3" placeholder="简要描述本次办理事项" />
          </el-form-item>
          <template v-if="currentInstance.process?.code === 'leave_application'">
            <el-form-item label="请假原因"><el-input v-model="form.reason" /></el-form-item>
            <el-form-item label="开始日期"><el-input v-model="form.start_date" placeholder="YYYY-MM-DD" /></el-form-item>
            <el-form-item label="结束日期"><el-input v-model="form.end_date" placeholder="YYYY-MM-DD" /></el-form-item>
            <el-form-item label="审批人"><el-input v-model="form.approver" /></el-form-item>
          </template>
          <template v-else-if="currentInstance.process?.code === 'repair_request'">
            <el-form-item label="报修地点"><el-input v-model="form.location" /></el-form-item>
            <el-form-item label="设施类型"><el-input v-model="form.facility_type" /></el-form-item>
            <el-form-item label="问题描述"><el-input v-model="form.issue" type="textarea" /></el-form-item>
          </template>
          <template v-else-if="currentInstance.process?.code === 'venue_booking'">
            <el-form-item label="用途"><el-input v-model="form.purpose" /></el-form-item>
            <el-form-item label="预约时间"><el-input v-model="form.booking_time" /></el-form-item>
            <el-form-item label="人数 / 设备需求"><el-input v-model="form.requirements" /></el-form-item>
          </template>
          <template v-else>
            <el-form-item label="申请类型 / 用途"><el-input v-model="form.purpose" /></el-form-item>
          </template>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button @click="saveInstance">保存草稿</el-button>
        <el-button type="primary" @click="nextStep">下一步</el-button>
        <el-button v-if="currentInstance?.process?.code === 'leave_application'" type="success" @click="generateDocument">生成请假条</el-button>
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
const headers = () => ({ Authorization: `Bearer ${userStore.getToken}` })
const processes = ref([])
const instances = ref([])
const selected = ref(null)
const loading = ref(false)
const activeCategory = ref('')
const dialogVisible = ref(false)
const currentInstance = ref(null)
const form = reactive({})

const loadProcesses = async () => {
  const params = activeCategory.value ? { category: activeCategory.value } : {}
  const resp = await axios.get(apiConfig.endpoints.serviceProcesses, { headers: headers(), params })
  processes.value = resp.data.data || []
  if (!selected.value && processes.value.length) selected.value = processes.value[0]
}

const loadInstances = async () => {
  const resp = await axios.get(apiConfig.endpoints.serviceProcessInstances, { headers: headers() })
  instances.value = resp.data.data || []
}

const loadAll = async () => {
  loading.value = true
  try {
    await Promise.all([loadProcesses(), loadInstances()])
  } catch (error) {
    ElMessage.error('办事流程加载失败')
  } finally {
    loading.value = false
  }
}

const selectProcess = (process) => { selected.value = process }

const startProcess = async (process) => {
  const resp = await axios.post(`${apiConfig.endpoints.serviceProcesses}/${process.id}/start`, {}, { headers: headers() })
  currentInstance.value = resp.data.data
  Object.keys(form).forEach(key => delete form[key])
  Object.assign(form, currentInstance.value.collected_data || {})
  dialogVisible.value = true
  await loadInstances()
}

const editInstance = (instance) => {
  currentInstance.value = instance
  Object.keys(form).forEach(key => delete form[key])
  Object.assign(form, instance.collected_data || {})
  dialogVisible.value = true
}

const saveInstance = async () => {
  await axios.patch(`${apiConfig.endpoints.serviceProcessInstances}${currentInstance.value.id}`, {
    status: 'collecting',
    current_step: currentInstance.value.current_step,
    collected_data: { ...form },
  }, { headers: headers() })
  ElMessage.success('草稿已保存')
  await loadInstances()
}

const nextStep = async () => {
  const next = Math.min((currentInstance.value.current_step || 0) + 1, (currentInstance.value.process?.steps?.length || 1) - 1)
  await axios.patch(`${apiConfig.endpoints.serviceProcessInstances}${currentInstance.value.id}`, {
    status: 'collecting',
    current_step: next,
    collected_data: { ...form },
  }, { headers: headers() })
  ElMessage.success('已进入下一步')
  await loadAll()
  dialogVisible.value = false
}

const cancelInstance = async (instance) => {
  await axios.patch(`${apiConfig.endpoints.serviceProcessInstances}${instance.id}`, { status: 'cancelled' }, { headers: headers() })
  ElMessage.success('流程已取消')
  await loadInstances()
}

const generateDocument = async () => {
  await saveInstance()
  const resp = await axios.post(`${apiConfig.endpoints.serviceProcessInstances}${currentInstance.value.id}/generate-document`, {}, { headers: headers() })
  ElMessage.success('请假条已生成')
  window.open(resp.data.data.download_url, '_blank')
}

const categoryText = (value) => ({ leave: '请假', repair: '报修', certificate: '证明', venue: '场地', other: '其他' }[value] || value)
const statusText = (value) => ({ draft: '草稿', collecting: '信息收集中', ready_to_submit: '可提交', submitted: '已提交记录', completed: '已完成', cancelled: '已取消' }[value] || value)

onMounted(loadAll)
</script>

<style scoped>
.process-page {
  padding: 24px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}
.page-header h1 {
  margin: 0 0 8px;
  font-size: 24px;
}
.page-header p,
.meta,
.source,
.dialog-subtitle {
  color: #6b7280;
}
.process-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}
.process-card,
.panel {
  background: #fff;
  border: 1px solid #ebe7df;
  border-radius: 8px;
  padding: 18px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}
.card-head h2,
.panel h2 {
  margin: 0;
  font-size: 18px;
}
.meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  margin: 12px 0;
}
.actions {
  display: flex;
  gap: 8px;
}
.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
}
.detail-panel h3 {
  margin-top: 18px;
}
.faq,
.instance {
  border-top: 1px solid #f0ede7;
  padding: 12px 0;
}
.instance {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.process-form {
  margin-top: 18px;
}
@media (max-width: 1080px) {
  .workspace,
  .page-header {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
