<template>
  <div class="leave-container">
    <div class="leave-card">
      <h2 class="page-title">📄 请假条生成</h2>

      <!-- 请假类型选择 -->
      <el-radio-group v-model="leaveType" size="large" class="type-switch">
        <el-radio-button value="course_leave">课程请假</el-radio-button>
        <el-radio-button value="long_leave">长假期请假</el-radio-button>
      </el-radio-group>

      <!-- ========== 课程请假表单 ========== -->
      <el-form
        v-if="leaveType === 'course_leave'"
        ref="courseFormRef"
        :model="courseForm"
        :rules="courseRules"
        label-width="100px"
        class="leave-form"
      >
        <el-form-item label="请假条类型" prop="recipient_type">
          <el-radio-group v-model="courseForm.recipient_type">
            <el-radio value="teacher">交给任课老师</el-radio>
            <el-radio value="student_affairs">学工组备案</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="courseForm.recipient_type === 'teacher'" label="老师姓名" prop="teacher_name">
          <el-input v-model="courseForm.teacher_name" placeholder="如：张三" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="班级" prop="class_name" label-width="60px">
              <el-input v-model="courseForm.class_name" placeholder="如：计科2301" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="姓名" prop="student_name" label-width="60px">
              <el-input v-model="courseForm.student_name" placeholder="学生姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学号" prop="student_id" label-width="60px">
              <el-input v-model="courseForm.student_id" placeholder="学号" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="请假原因" prop="reason">
          <el-input v-model="courseForm.reason" type="textarea" :rows="2" placeholder="如：身体不适需就医" />
        </el-form-item>

        <el-form-item label="请假天数" prop="duration_days">
          <el-input v-model="courseForm.duration_days" placeholder="如：1天 / 半天 / 2节课" style="width:200px" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="开始时间" prop="start_date" label-width="80px">
              <el-date-picker
                v-model="startDatePicker"
                type="datetime"
                placeholder="选择开始日期时间"
                format="YYYY年M月D日H时"
                value-format="YYYY年M月D日H时"
                style="width:100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间" prop="end_date" label-width="80px">
              <el-date-picker
                v-model="endDatePicker"
                type="datetime"
                placeholder="选择结束日期时间"
                format="YYYY年M月D日H时"
                value-format="YYYY年M月D日H时"
                style="width:100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="本人电话" label-width="80px">
              <el-input v-model="courseForm.student_phone" placeholder="手机号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="家长电话" label-width="80px">
              <el-input v-model="courseForm.parent_phone" placeholder="家长手机号" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="本人签名" label-width="80px">
              <el-input v-model="courseForm.signature" placeholder="输入姓名作为签名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="日期" label-width="60px">
              <el-date-picker
                v-model="signDateCourse"
                type="date"
                placeholder="签字日期"
                format="YYYY年M月D日"
                value-format="YYYY年M月D日"
                style="width:100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- ========== 长假期请假表单 ========== -->
      <el-form
        v-if="leaveType === 'long_leave'"
        ref="longFormRef"
        :model="longForm"
        :rules="longRules"
        label-width="100px"
        class="leave-form"
      >
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="姓名" prop="student_name" label-width="60px">
              <el-input v-model="longForm.student_name" placeholder="学生姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学号" prop="student_id" label-width="60px">
              <el-input v-model="longForm.student_id" placeholder="学号" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="班号" prop="class_name" label-width="60px">
              <el-input v-model="longForm.class_name" placeholder="如：23G231" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="离校电话" label-width="80px">
              <el-input v-model="longForm.phone" placeholder="本人离校期间电话" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="亲属关系" label-width="80px">
              <el-input v-model="longForm.parent_relation" placeholder="如：父亲" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="亲属电话" label-width="80px">
              <el-input v-model="longForm.parent_phone" placeholder="亲属联系电话" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="离校时间" prop="leave_start" label-width="80px">
              <el-date-picker
                v-model="leaveStartPicker"
                type="datetime"
                placeholder="选择离校日期时间"
                format="YYYY年M月D日H时"
                value-format="YYYY年M月D日H时"
                style="width:100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="返校时间" prop="leave_end" label-width="80px">
              <el-date-picker
                v-model="leaveEndPicker"
                type="datetime"
                placeholder="选择返校日期时间"
                format="YYYY年M月D日H时"
                value-format="YYYY年M月D日H时"
                style="width:100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="共几天" prop="total_days">
          <el-input v-model="longForm.total_days" placeholder="如：5" style="width:150px" />
        </el-form-item>

        <el-form-item label="请假原因" prop="reason">
          <el-input v-model="longForm.reason" type="textarea" :rows="3" placeholder="详细说明请假原因" />
        </el-form-item>

        <el-form-item label="去向地址">
          <el-input v-model="longForm.destination" type="textarea" :rows="2" placeholder="请假期间去向的详细地址" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="本人签名" label-width="80px">
              <el-input v-model="longForm.signature" placeholder="输入姓名作为签名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="日期" label-width="60px">
              <el-date-picker
                v-model="signDateLong"
                type="date"
                placeholder="签字日期"
                format="YYYY年M月D日"
                value-format="YYYY年M月D日"
                style="width:100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- 生成按钮 -->
      <div class="form-actions">
        <el-button type="primary" size="large" @click="handleGenerate" :loading="generating">
          <el-icon v-if="!generating"><Document /></el-icon>
          {{ generating ? '生成中...' : '生成请假条' }}
        </el-button>
      </div>

      <!-- 下载链接 -->
      <div v-if="downloadUrl" class="download-area">
        <el-alert type="success" :closable="false" show-icon>
          <template #title>
            请假条已生成 —
            <el-link type="primary" :href="downloadUrl" target="_blank">
              📥 下载 {{ downloadFilename }}
            </el-link>
          </template>
        </el-alert>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'

const userStore = useUserStore()
const token = computed(() => userStore.token || localStorage.getItem('access_token') || '')

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${token.value}`
})

// ── 请假类型 ──
const leaveType = ref('course_leave')
const generating = ref(false)
const downloadUrl = ref('')
const downloadFilename = ref('')

// ── 日期选择器绑定 ──
const startDatePicker = ref('')
const endDatePicker = ref('')
const signDateCourse = ref('')
const leaveStartPicker = ref('')
const leaveEndPicker = ref('')
const signDateLong = ref('')

// ── 课程请假表单 ──
const courseForm = reactive({
  recipient_type: 'teacher',
  teacher_name: '',
  class_name: '',
  student_name: '',
  student_id: '',
  reason: '',
  duration_days: '',
  start_date: '',
  start_time: '',
  end_date: '',
  end_time: '',
  student_phone: '',
  parent_phone: '',
  signature: '',
  sign_date: '',
})

const courseRules = {
  student_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  student_id: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  class_name: [{ required: true, message: '请输入班级', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入请假原因', trigger: 'blur' }],
}

// ── 长假期请假表单 ──
const longForm = reactive({
  student_name: '',
  student_id: '',
  class_name: '',
  phone: '',
  parent_relation: '',
  parent_phone: '',
  leave_start: '',
  leave_end: '',
  total_days: '',
  reason: '',
  destination: '',
  signature: '',
  sign_date: '',
})

const longRules = {
  student_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  student_id: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  class_name: [{ required: true, message: '请输入班号', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入请假原因', trigger: 'blur' }],
  leave_start: [{ required: true, message: '请选择离校时间', trigger: 'change' }],
  leave_end: [{ required: true, message: '请选择返校时间', trigger: 'change' }],
}

// ── 日期选择器→表单字段同步 ──
const parseDateParts = (val) => {
  if (!val) return { date: '', time: '' }
  const m = val.match(/^(\d{4}年\d{1,2}月\d{1,2}日)(\d{1,2}时)?$/)
  if (m) return { date: m[1], time: m[2] || '' }
  return { date: val, time: '' }
}

const syncCourseDates = () => {
  const s = parseDateParts(startDatePicker.value)
  courseForm.start_date = s.date
  courseForm.start_time = s.time
  const e = parseDateParts(endDatePicker.value)
  courseForm.end_date = e.date
  courseForm.end_time = e.time
  courseForm.sign_date = signDateCourse.value
}

const syncLongDates = () => {
  longForm.leave_start = leaveStartPicker.value
  longForm.leave_end = leaveEndPicker.value
  longForm.sign_date = signDateLong.value
}

// ── 生成请假条 ──
const courseFormRef = ref(null)
const longFormRef = ref(null)

const handleGenerate = async () => {
  // 同步日期
  syncCourseDates()
  syncLongDates()

  // 校验
  let valid = false
  if (leaveType.value === 'course_leave') {
    if (!courseFormRef.value) return
    try { await courseFormRef.value.validate(); valid = true } catch { valid = false }
  } else {
    if (!longFormRef.value) return
    try { await longFormRef.value.validate(); valid = true } catch { valid = false }
  }
  if (!valid) return

  generating.value = true
  downloadUrl.value = ''
  downloadFilename.value = ''

  try {
    const body = leaveType.value === 'course_leave'
      ? { leave_type: 'course_leave', course_leave: { ...courseForm } }
      : { leave_type: 'long_leave', long_leave: { ...longForm } }

    const res = await fetch('/api/leave/generate', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(body),
    })
    const json = await res.json()
    if (json.code === 200 && json.data) {
      downloadUrl.value = json.data.download_url
      downloadFilename.value = json.data.filename
      ElMessage.success('请假条生成成功')
    } else {
      ElMessage.error(json.message || '生成失败')
    }
  } catch (e) {
    ElMessage.error('请求失败：' + e.message)
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.leave-container {
  max-width: 860px;
  margin: 24px auto;
  padding: 0 16px;
}

.leave-card {
  background: #fff;
  border-radius: 8px;
  padding: 32px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.page-title {
  margin: 0 0 24px 0;
  font-size: 22px;
  color: #303133;
}

.type-switch {
  margin-bottom: 28px;
}

.leave-form {
  margin-top: 8px;
}

.form-actions {
  margin-top: 28px;
  display: flex;
  justify-content: center;
}

.download-area {
  margin-top: 20px;
}
</style>
