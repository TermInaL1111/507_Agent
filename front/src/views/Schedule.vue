<template>
  <div class="schedule-page page-container">
    <div class="schedule-header">
      <div>
        <h2>每周时间表</h2>
        <p>统一管理课程、活动、自习、考试和待办安排</p>
      </div>
      <div class="header-actions">
        <el-segmented v-model="viewMode" :options="viewOptions" />
        <el-button :icon="Refresh" @click="loadEvents">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreateDialog()">新增安排</el-button>
      </div>
    </div>

    <div v-if="viewMode === 'gantt'" class="gantt-shell">
      <div class="gantt-header">
        <div>
          <h3>今日甘特图</h3>
          <p>{{ todayDateText }} · {{ getWeekdayLabel(todayWeekday) }} · 按开始时间排序</p>
        </div>
        <span>{{ todayGanttEvents.length }} 项</span>
      </div>

      <el-empty v-if="!todayGanttEvents.length" description="今天暂无活动计划" />
      <div v-else class="gantt-board">
        <div class="gantt-axis">
          <div class="gantt-axis-spacer"></div>
          <div class="gantt-timeline">
            <span
              v-for="tick in ganttTicks"
              :key="tick.time"
              class="gantt-tick"
              :style="{ left: `${tick.left}%` }"
            >
              {{ tick.time }}
            </span>
          </div>
        </div>

        <div v-for="event in todayGanttEvents" :key="`gantt-${event.id}`" class="gantt-row">
          <div class="gantt-info">
            <strong>{{ event.title }}</strong>
            <span>{{ event.startTime }}-{{ event.endTime }}</span>
            <em v-if="event.location">{{ event.location }}</em>
          </div>
          <div class="gantt-track">
            <div
              class="gantt-bar"
              :style="getGanttBarStyle(event)"
              :title="`${event.title} ${event.startTime}-${event.endTime}`"
            >
              <span>{{ event.title }}</span>
              <small>{{ event.startTime }}-{{ event.endTime }}</small>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="schedule-shell">
      <div class="schedule-grid">
        <div class="grid-head time-head">时间段</div>
        <div v-for="day in weekdays" :key="day.key" class="grid-head">
          <span>{{ day.label }}</span>
        </div>

        <template v-for="slot in displayedTimeSlots" :key="slot.key">
          <div class="time-cell">
            <strong>{{ slot.label }}</strong>
            <span>{{ slot.period }}</span>
          </div>
          <div
            v-for="day in weekdays"
            :key="`${slot.key}-${day.key}`"
            class="day-cell"
            @dblclick="openCreateDialog(day.key, slot)"
          >
            <div
              v-for="event in getEventsForCell(day.key, slot)"
              :key="event.id"
              class="event-block"
              :class="`event-${event.type}`"
            >
              <div class="event-main">
                <span class="event-title">{{ event.title }}</span>
                <el-button text :icon="Delete" class="event-delete" @click.stop="removeEvent(event)" />
              </div>
              <div class="event-time">{{ event.startTime }}-{{ event.endTime }}</div>
              <div v-if="event.location" class="event-meta">{{ event.location }}</div>
              <div v-if="event.teacher" class="event-meta">{{ event.teacher }}</div>
              <div v-if="event.remark" class="event-remark">{{ event.remark }}</div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="all-events">
      <div class="all-events-head">
        <h3>全部安排</h3>
        <span>共 {{ sortedEvents.length }} 项</span>
      </div>
      <el-empty v-if="!sortedEvents.length" description="暂无时间安排" />
      <div v-else class="all-events-list">
        <div v-for="event in sortedEvents" :key="`list-${event.id}`" class="all-event-item">
          <div class="all-event-main">
            <strong>{{ event.title }}</strong>
            <el-tag size="small" effect="plain">{{ getWeekdayLabel(event.weekday) }}</el-tag>
            <el-tag v-if="event.source === 'ai_chat'" size="small" type="success" effect="plain">AI添加</el-tag>
          </div>
          <div class="all-event-meta">
            <span>{{ event.date || '每周' }}</span>
            <span>{{ event.startTime }}-{{ event.endTime }}</span>
            <span v-if="event.location">{{ event.location }}</span>
            <span v-if="event.remark">{{ event.remark }}</span>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="新增时间安排" width="520px">
      <el-form :model="form" label-width="86px">
        <el-form-item label="事项名称">
          <el-input v-model="form.title" placeholder="例如：数据结构、项目开发、自习" />
        </el-form-item>
        <el-form-item label="类型">
          <el-segmented v-model="form.type" :options="typeOptions" />
        </el-form-item>
        <el-form-item label="星期">
          <el-select v-model="form.weekday" style="width: 100%">
            <el-option v-for="day in weekdays" :key="day.key" :label="day.label" :value="day.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间">
          <div class="time-inputs">
            <el-time-select v-model="form.startTime" start="06:00" step="00:10" end="23:30" placeholder="开始" />
            <span>至</span>
            <el-time-select v-model="form.endTime" start="06:10" step="00:10" end="23:50" placeholder="结束" />
          </div>
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="form.location" placeholder="教学楼 A301、图书馆、自定义地点" />
        </el-form-item>
        <el-form-item label="教师">
          <el-input v-model="form.teacher" placeholder="可选" />
        </el-form-item>
        <el-form-item label="重复">
          <el-select v-model="form.repeat" style="width: 100%">
            <el-option label="每周重复" value="weekly" />
            <el-option label="单次安排" value="once" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <el-alert
        v-if="conflicts.length"
        type="warning"
        :closable="false"
        show-icon
        class="conflict-alert"
        :title="`检测到 ${conflicts.length} 个时间冲突，确认后仍会保存`"
      />
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEvent">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Delete, Plus, Refresh } from '@element-plus/icons-vue';
import { useUserStore } from '../store/user';

const router = useRouter();
const userStore = useUserStore();
const events = ref([]);
const dialogVisible = ref(false);
const saving = ref(false);
const conflicts = ref([]);
const viewMode = ref('gantt');

const viewOptions = [
  { label: '今日甘特图', value: 'gantt' },
  { label: '每周表格', value: 'week' }
];

const weekdays = [
  { key: 'Monday', label: '周一' },
  { key: 'Tuesday', label: '周二' },
  { key: 'Wednesday', label: '周三' },
  { key: 'Thursday', label: '周四' },
  { key: 'Friday', label: '周五' },
  { key: 'Saturday', label: '周六' },
  { key: 'Sunday', label: '周日' }
];

const baseTimeSlots = [
  { key: 'morning1', period: '上午', label: '08:00-09:40', start: '08:00', end: '09:40' },
  { key: 'morning2', period: '上午', label: '10:00-11:40', start: '10:00', end: '11:40' },
  { key: 'afternoon1', period: '下午', label: '14:00-15:40', start: '14:00', end: '15:40' },
  { key: 'afternoon2', period: '下午', label: '16:00-17:40', start: '16:00', end: '17:40' },
  { key: 'evening1', period: '晚上', label: '19:00-21:00', start: '19:00', end: '21:00' }
];

const typeOptions = [
  { label: '课程', value: 'course' },
  { label: '活动', value: 'activity' },
  { label: '自习', value: 'study' },
  { label: '考试', value: 'exam' },
  { label: '待办', value: 'task' }
];

const form = reactive({
  title: '',
  type: 'course',
  weekday: 'Monday',
  startTime: '08:00',
  endTime: '09:40',
  location: '',
  teacher: '',
  repeat: 'weekly',
  source: 'manual',
  remark: ''
});

const token = computed(() => userStore.getToken);
const ganttStart = 6 * 60;
const ganttEnd = 24 * 60;
const ganttRange = ganttEnd - ganttStart;

const typeColors = {
  course: '#007AFF',
  activity: '#34C759',
  exam: '#FF3B30',
  meeting: '#5856D6',
  study: '#FF9500',
  task: '#8E8E93',
  other: '#5AC8FA'
};

const weekdayIndex = {
  Monday: 1,
  Tuesday: 2,
  Wednesday: 3,
  Thursday: 4,
  Friday: 5,
  Saturday: 6,
  Sunday: 7
};

const getWeekdayLabel = (weekday) => weekdays.find((day) => day.key === weekday)?.label || weekday;

const pad2 = (value) => String(value).padStart(2, '0');

const today = new Date();
const todayDateText = `${today.getFullYear()}-${pad2(today.getMonth() + 1)}-${pad2(today.getDate())}`;
const todayWeekday = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][today.getDay()];

const ganttTicks = Array.from({ length: 10 }, (_, index) => {
  const minutes = ganttStart + index * 120;
  return {
    time: `${pad2(Math.floor(minutes / 60))}:00`,
    left: ((minutes - ganttStart) / ganttRange) * 100
  };
});

const periodFromTime = (timeValue) => {
  const hour = Number(String(timeValue || '00:00').split(':')[0]);
  if (hour < 12) return '上午';
  if (hour < 18) return '下午';
  return '晚上';
};

const slotKey = (start, end) => `event-${start}-${end}`.replace(/[^a-zA-Z0-9-]/g, '-');

const displayedTimeSlots = computed(() => {
  const slotMap = new Map(baseTimeSlots.map((slot) => [`${slot.start}-${slot.end}`, slot]));
  events.value.forEach((event) => {
    if (!event.startTime || !event.endTime) return;
    const key = `${event.startTime}-${event.endTime}`;
    if (!slotMap.has(key)) {
      slotMap.set(key, {
        key: slotKey(event.startTime, event.endTime),
        period: periodFromTime(event.startTime),
        label: key,
        start: event.startTime,
        end: event.endTime
      });
    }
  });
  return Array.from(slotMap.values()).sort((a, b) => toMinutes(a.start) - toMinutes(b.start));
});

const sortedEvents = computed(() => [...events.value].sort((a, b) => {
  const dayDiff = (weekdayIndex[a.weekday] || 99) - (weekdayIndex[b.weekday] || 99);
  if (dayDiff !== 0) return dayDiff;
  return toMinutes(a.startTime) - toMinutes(b.startTime);
}));

const todayGanttEvents = computed(() => events.value
  .filter((event) => {
    if (event.date) return event.date === todayDateText;
    return event.weekday === todayWeekday;
  })
  .sort((a, b) => toMinutes(a.startTime) - toMinutes(b.startTime)));

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const getGanttBarStyle = (event) => {
  const start = clamp(toMinutes(event.startTime), ganttStart, ganttEnd);
  const end = clamp(toMinutes(event.endTime), ganttStart, ganttEnd);
  const color = typeColors[event.type] || typeColors.other;
  const left = ((start - ganttStart) / ganttRange) * 100;
  const width = Math.max(((end - start) / ganttRange) * 100, 1.2);

  return {
    left: `${left}%`,
    width: `${width}%`,
    background: color,
    boxShadow: `0 8px 18px ${color}33`
  };
};

const ensureLogin = () => {
  userStore.initAuthState();
  if (!userStore.getLoginStatus || !token.value) {
    ElMessage.warning('请先登录后再使用时间表');
    router.push({ path: '/login', query: { redirect: '/schedule' } });
    return false;
  }
  return true;
};

const authHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${token.value}`
});

const loadEvents = async () => {
  if (!ensureLogin()) return;
  const response = await fetch('/api/schedule/week', { headers: authHeaders() });
  if (!response.ok) {
    ElMessage.error('加载时间表失败');
    return;
  }
  const payload = await response.json();
  events.value = payload.data?.events || [];
};

const openCreateDialog = (weekday = 'Monday', slot = baseTimeSlots[0]) => {
  Object.assign(form, {
    title: '',
    type: 'course',
    weekday,
    startTime: slot.start,
    endTime: slot.end,
    location: '',
    teacher: '',
    repeat: 'weekly',
    source: 'manual',
    remark: ''
  });
  conflicts.value = [];
  dialogVisible.value = true;
};

const toMinutes = (value) => {
  const [hour, minute] = value.split(':').map(Number);
  return hour * 60 + minute;
};

const getEventsForCell = (weekday, slot) => {
  const start = toMinutes(slot.start);
  const end = toMinutes(slot.end);
  return events.value
    .filter((event) => event.weekday === weekday && toMinutes(event.startTime) < end && toMinutes(event.endTime) > start)
    .sort((a, b) => toMinutes(a.startTime) - toMinutes(b.startTime));
};

const validateForm = () => {
  if (!form.title.trim()) {
    ElMessage.warning('请输入事项名称');
    return false;
  }
  if (toMinutes(form.startTime) >= toMinutes(form.endTime)) {
    ElMessage.warning('结束时间必须晚于开始时间');
    return false;
  }
  return true;
};

const submitEvent = async () => {
  if (!validateForm() || !ensureLogin()) return;
  saving.value = true;
  try {
    const conflictResponse = await fetch('/api/schedule/conflicts', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(form)
    });
    const conflictPayload = await conflictResponse.json();
    conflicts.value = conflictPayload.conflicts || [];

    if (conflicts.value.length) {
      await ElMessageBox.confirm('该时间段已有安排，是否仍然保存？', '时间冲突', {
        type: 'warning',
        confirmButtonText: '仍然保存',
        cancelButtonText: '返回修改'
      });
    }

    const response = await fetch('/api/schedule/events', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(form)
    });
    if (!response.ok) throw new Error('save failed');
    ElMessage.success('已加入时间表');
    dialogVisible.value = false;
    await loadEvents();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('保存失败，请检查时间安排');
    }
  } finally {
    saving.value = false;
  }
};

const removeEvent = async (event) => {
  if (!ensureLogin()) return;
  await ElMessageBox.confirm(`确认删除“${event.title}”？`, '删除安排', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消'
  });
  const response = await fetch(`/api/schedule/events/${event.id}`, {
    method: 'DELETE',
    headers: authHeaders()
  });
  if (!response.ok) {
    ElMessage.error('删除失败');
    return;
  }
  ElMessage.success('已删除');
  await loadEvents();
};

onMounted(loadEvents);
</script>

<style scoped>
.schedule-page {
  padding: 20px;
}

.schedule-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.schedule-header h2 {
  margin: 0 0 6px;
  font-size: 22px;
  color: #1f2937;
}

.schedule-header p {
  margin: 0;
  color: #667085;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.schedule-shell {
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.gantt-shell {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
  overflow-x: auto;
}

.gantt-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.gantt-header h3 {
  margin: 0 0 4px;
  font-size: 17px;
  color: #1f2937;
}

.gantt-header p,
.gantt-header span {
  margin: 0;
  color: #667085;
  font-size: 13px;
}

.gantt-board {
  min-width: 980px;
}

.gantt-axis,
.gantt-row {
  display: grid;
  grid-template-columns: 180px minmax(760px, 1fr);
  gap: 16px;
}

.gantt-axis {
  height: 34px;
  align-items: end;
}

.gantt-timeline,
.gantt-track {
  position: relative;
}

.gantt-timeline {
  height: 28px;
  border-bottom: 1px solid #d0d5dd;
}

.gantt-tick {
  position: absolute;
  bottom: 7px;
  transform: translateX(-50%);
  color: #667085;
  font-size: 12px;
  white-space: nowrap;
}

.gantt-tick::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -8px;
  width: 1px;
  height: 8px;
  background: #d0d5dd;
}

.gantt-row {
  min-height: 62px;
  align-items: center;
  border-bottom: 1px solid #eef2f7;
}

.gantt-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.gantt-info strong {
  color: #1f2937;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gantt-info span,
.gantt-info em {
  color: #667085;
  font-size: 12px;
  font-style: normal;
}

.gantt-track {
  height: 34px;
  border-radius: 8px;
  background:
    repeating-linear-gradient(
      to right,
      #f2f4f7 0,
      #f2f4f7 1px,
      transparent 1px,
      transparent calc(100% / 9)
    ),
    #fbfdff;
}

.gantt-bar {
  position: absolute;
  top: 4px;
  bottom: 4px;
  min-width: 42px;
  border-radius: 7px;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  box-sizing: border-box;
  overflow: hidden;
}

.gantt-bar span,
.gantt-bar small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gantt-bar span {
  font-weight: 600;
  font-size: 13px;
}

.gantt-bar small {
  font-size: 11px;
  opacity: 0.9;
}

.all-events {
  margin-top: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 14px;
}

.all-events-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.all-events-head h3 {
  margin: 0;
  font-size: 16px;
  color: #1f2937;
}

.all-events-head span {
  color: #667085;
  font-size: 13px;
}

.all-events-list {
  display: grid;
  gap: 10px;
}

.all-event-item {
  border: 1px solid #eef2f7;
  border-radius: 6px;
  padding: 10px 12px;
  background: #fbfdff;
}

.all-event-main,
.all-event-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.all-event-main {
  margin-bottom: 6px;
}

.all-event-meta {
  color: #667085;
  font-size: 13px;
}

.schedule-grid {
  min-width: 1080px;
  display: grid;
  grid-template-columns: 132px repeat(7, minmax(128px, 1fr));
}

.grid-head,
.time-cell,
.day-cell {
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}

.grid-head {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  color: #344054;
  font-weight: 600;
}

.time-cell {
  min-height: 128px;
  padding: 14px 12px;
  background: #fbfdff;
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #344054;
}

.time-cell span {
  color: #667085;
  font-size: 12px;
}

.day-cell {
  min-height: 128px;
  padding: 8px;
  background: #fff;
}

.day-cell:hover {
  background: #f9fbff;
}

.event-block {
  border-left: 4px solid #409eff;
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 8px;
  background: #ecf5ff;
  color: #1f2937;
}

.event-activity {
  border-left-color: #67c23a;
  background: #f0f9eb;
}

.event-study {
  border-left-color: #e6a23c;
  background: #fdf6ec;
}

.event-exam {
  border-left-color: #f56c6c;
  background: #fef0f0;
}

.event-task {
  border-left-color: #909399;
  background: #f4f4f5;
}

.event-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.event-title {
  font-weight: 600;
  line-height: 1.35;
}

.event-delete {
  width: 24px;
  height: 24px;
}

.event-time,
.event-meta,
.event-remark {
  margin-top: 4px;
  color: #667085;
  font-size: 12px;
  line-height: 1.35;
}

.time-inputs {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.time-inputs :deep(.el-select) {
  flex: 1;
}

.conflict-alert {
  margin-top: 8px;
}

@media (max-width: 720px) {
  .schedule-header {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
  }
}
</style>
