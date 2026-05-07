<template>
  <div class="training-page">
    <header class="page-head">
      <div>
        <h2>培养方案</h2>
        <p>按学院查看本地已整理的培养方案文件；具体内容查询请在 AI 问答中提问。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadFiles">刷新</el-button>
    </header>

    <el-alert
      v-if="!loading && !files.length"
      title="暂未扫描到培养方案文件，请确认项目目录下存在 Training Program 或 training program 文件夹。"
      type="warning"
      :closable="false"
      show-icon
      class="empty-alert"
    />

    <section v-else class="content-layout">
      <aside class="college-nav">
        <button
          v-for="college in colleges"
          :key="college"
          type="button"
          class="college-item"
          :class="{ active: activeCollege === college }"
          @click="activeCollege = college"
        >
          <span>{{ college }}</span>
          <strong>{{ groupedFiles[college]?.length || 0 }}</strong>
        </button>
      </aside>

      <main class="file-panel">
        <div class="panel-head">
          <div>
            <h3>{{ activeCollege || '全部学院' }}</h3>
            <p>共 {{ currentFiles.length }} 份培养方案</p>
          </div>
          <el-tag effect="plain">AI 问答支持培养方案检索</el-tag>
        </div>

        <div class="file-list">
          <article v-for="file in currentFiles" :key="file.relativePath" class="file-row">
            <div class="file-main">
              <div class="file-title">
                <span>{{ file.major || '未识别专业' }}</span>
                <el-tag size="small" effect="plain">{{ file.fileType }}</el-tag>
                <el-tag size="small" :type="file.status === 'imported' ? 'success' : 'info'">
                  {{ file.status === 'imported' ? '已入库' : '待入库' }}
                </el-tag>
              </div>
              <div class="file-name">{{ file.fileName }}</div>
              <div class="file-path">{{ file.relativePath }}</div>
            </div>
            <div class="file-meta">
              <span v-if="file.chunkCount">切片 {{ file.chunkCount }}</span>
              <span v-if="file.importedAt">入库 {{ formatDate(file.importedAt) }}</span>
            </div>
          </article>
        </div>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { Refresh } from '@element-plus/icons-vue';

const files = ref([]);
const loading = ref(false);
const activeCollege = ref('');

const groupedFiles = computed(() => {
  return files.value.reduce((groups, file) => {
    const college = file.college || '未分类';
    if (!groups[college]) groups[college] = [];
    groups[college].push(file);
    return groups;
  }, {});
});

const colleges = computed(() => {
  return Object.keys(groupedFiles.value).sort((a, b) => a.localeCompare(b, 'zh-CN'));
});

const currentFiles = computed(() => {
  const college = activeCollege.value || colleges.value[0];
  return [...(groupedFiles.value[college] || [])].sort((a, b) => {
    return String(a.major || a.fileName).localeCompare(String(b.major || b.fileName), 'zh-CN');
  });
});

watch(colleges, (value) => {
  if (!value.length) {
    activeCollege.value = '';
    return;
  }
  if (!activeCollege.value || !value.includes(activeCollege.value)) {
    activeCollege.value = value[0];
  }
});

const formatDate = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const loadFiles = async () => {
  loading.value = true;
  try {
    const response = await fetch('/api/training-program/files');
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `加载失败：${response.status}`);
    files.value = payload.data?.files || [];
  } catch (error) {
    ElMessage.error(error.message || '加载培养方案列表失败');
  } finally {
    loading.value = false;
  }
};

onMounted(loadFiles);
</script>

<style scoped>
.training-page {
  padding: 20px;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.page-head h2,
.panel-head h3 {
  margin: 0;
  color: #1f2937;
}

.page-head h2 {
  font-size: 22px;
}

.page-head p,
.panel-head p,
.file-name,
.file-path,
.file-meta {
  margin: 0;
  color: #667085;
}

.empty-alert {
  margin-top: 14px;
}

.content-layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 16px;
}

.college-nav,
.file-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.college-nav {
  padding: 10px;
  align-self: start;
}

.college-item {
  width: 100%;
  min-height: 42px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #475467;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 10px;
  cursor: pointer;
  text-align: left;
}

.college-item + .college-item {
  margin-top: 4px;
}

.college-item:hover,
.college-item.active {
  background: #eef6ff;
  color: #1677ff;
}

.college-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.college-item strong {
  font-weight: 600;
}

.file-panel {
  min-width: 0;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #eef0f3;
}

.file-list {
  padding: 8px 16px 16px;
}

.file-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid #f0f2f5;
}

.file-row:last-child {
  border-bottom: 0;
}

.file-main {
  min-width: 0;
}

.file-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
  color: #1f2937;
  font-weight: 600;
}

.file-name,
.file-path {
  overflow-wrap: anywhere;
  line-height: 1.6;
}

.file-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  min-width: 150px;
  font-size: 12px;
}

@media (max-width: 900px) {
  .page-head,
  .panel-head,
  .file-row {
    align-items: stretch;
    flex-direction: column;
  }

  .content-layout {
    grid-template-columns: 1fr;
  }

  .file-meta {
    align-items: flex-start;
    min-width: 0;
  }
}
</style>
