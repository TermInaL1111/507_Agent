<template>
  <div class="knowledge-page page-container">
    <div class="knowledge-header">
      <div>
        <h2>知识库管理</h2>
        <p>查看已有知识库文件，上传新文件后会自动写入 RAG 向量库。</p>
      </div>
      <div class="header-actions">
        <el-select v-model="kbTypeFilter" placeholder="知识库类型" clearable style="width: 150px" @change="loadFiles">
          <el-option label="个人知识库" value="personal" />
          <el-option label="学校政策" value="school_policy" />
          <el-option label="课程资料" value="course" />
        </el-select>
        <el-button :icon="Refresh" @click="loadFiles">刷新</el-button>
      </div>
    </div>

    <div class="upload-panel">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :limit="1"
        :on-change="onFileChange"
        :on-remove="onFileRemove"
        :file-list="selectedFiles"
        accept=".pdf,.txt,.md,.pptx,.docx"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到这里，或点击选择文件</div>
        <template #tip>
          <div class="upload-tip">支持 PDF、TXT、Markdown、PPTX、DOCX，单文件不超过 20MB。</div>
        </template>
      </el-upload>
      <div class="upload-actions">
        <el-button type="primary" :loading="uploading" :disabled="!selectedFiles.length" @click="uploadFile">
          上传并加入 RAG
        </el-button>
        <el-button :disabled="uploading || !selectedFiles.length" @click="clearUpload">清空</el-button>
      </div>
    </div>

    <div class="file-panel">
      <div class="file-panel-head">
        <h3>已有文件</h3>
        <span>共 {{ files.length }} 个</span>
      </div>

      <el-table v-loading="loading" :data="files" border stripe empty-text="暂无知识库文件">
        <el-table-column prop="original_filename" label="文件名" min-width="240" show-overflow-tooltip />
        <el-table-column label="知识库类型" width="130">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ getKbTypeLabel(row.kb_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="140">
          <template #default="{ row }">{{ row.category || '暂无分类' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="previewFile(row)">预览</el-button>
            <el-button size="small" @click="downloadFile(row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="previewVisible" :title="previewFileName" width="78vw" class="preview-dialog">
      <div v-if="previewSupported" class="preview-frame-wrap">
        <iframe :src="previewUrl" class="preview-frame" title="知识库文件预览"></iframe>
      </div>
      <el-empty v-else description="该文件类型暂不支持在线预览，请下载后查看" />
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" @click="downloadFile(selectedPreviewFile)">下载文件</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Refresh, UploadFilled } from '@element-plus/icons-vue';
import { useUserStore } from '../store/user';

const router = useRouter();
const userStore = useUserStore();
const files = ref([]);
const loading = ref(false);
const uploading = ref(false);
const kbTypeFilter = ref('');
const selectedFiles = ref([]);
const uploadRef = ref(null);
const previewVisible = ref(false);
const selectedPreviewFile = ref(null);

const token = computed(() => userStore.getToken);

const authHeaders = () => ({
  Authorization: `Bearer ${token.value}`
});

const ensureLogin = () => {
  userStore.initAuthState();
  if (!userStore.getLoginStatus || !token.value) {
    ElMessage.warning('请先登录后再管理知识库');
    router.push({ path: '/login', query: { redirect: '/knowledge-manage' } });
    return false;
  }
  return true;
};

const getKbTypeLabel = (type) => {
  const map = {
    personal: '个人知识库',
    school_policy: '学校政策',
    course: '课程资料'
  };
  return map[type] || type || '未知类型';
};

const formatDate = (value) => {
  if (!value) return '未知时间';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const loadFiles = async () => {
  if (!ensureLogin()) return;
  loading.value = true;
  try {
    const query = kbTypeFilter.value ? `?kb_type=${encodeURIComponent(kbTypeFilter.value)}` : '';
    const response = await fetch(`/api/source-file/list${query}`, {
      headers: authHeaders()
    });
    if (!response.ok) throw new Error(`load failed: ${response.status}`);
    const payload = await response.json();
    files.value = payload.data?.files || [];
  } catch (error) {
    console.error('加载知识库文件失败:', error);
    ElMessage.error('加载知识库文件失败');
  } finally {
    loading.value = false;
  }
};

const onFileChange = (_file, fileList) => {
  selectedFiles.value = fileList.slice(-1);
};

const onFileRemove = (_file, fileList) => {
  selectedFiles.value = fileList;
};

const clearUpload = () => {
  selectedFiles.value = [];
  uploadRef.value?.clearFiles();
};

const uploadFile = async () => {
  if (!ensureLogin() || !selectedFiles.value.length) return;
  const rawFile = selectedFiles.value[0]?.raw;
  if (!rawFile) {
    ElMessage.warning('请选择要上传的文件');
    return;
  }

  const formData = new FormData();
  formData.append('file', rawFile);
  uploading.value = true;
  try {
    const response = await fetch('/api/vector/add/single', {
      method: 'POST',
      headers: authHeaders(),
      body: formData
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `upload failed: ${response.status}`);
    ElMessage.success('文件已上传并加入 RAG 知识库');
    clearUpload();
    await loadFiles();
  } catch (error) {
    console.error('上传失败:', error);
    ElMessage.error(error.message || '上传失败');
  } finally {
    uploading.value = false;
  }
};

const previewFileName = computed(() => selectedPreviewFile.value?.original_filename || '文件预览');

const previewUrl = computed(() => {
  if (!selectedPreviewFile.value) return '';
  return `/api/source-file/preview/${selectedPreviewFile.value.file_id}`;
});

const previewSupported = computed(() => {
  const name = String(selectedPreviewFile.value?.original_filename || '').toLowerCase();
  return ['.pdf', '.txt', '.md'].some((ext) => name.endsWith(ext));
});

const previewFile = (file) => {
  selectedPreviewFile.value = file;
  previewVisible.value = true;
};

const downloadFile = (file) => {
  if (!file?.file_id) return;
  window.open(`/api/source-file/download/${file.file_id}`, '_blank');
};

onMounted(loadFiles);
</script>

<style scoped>
.knowledge-page {
  padding: 20px;
}

.knowledge-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.knowledge-header h2 {
  margin: 0 0 6px;
  color: #1f2937;
  font-size: 22px;
}

.knowledge-header p {
  margin: 0;
  color: #667085;
}

.header-actions,
.upload-actions,
.file-panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-panel,
.file-panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
}

.file-panel {
  margin-top: 16px;
}

.upload-icon {
  font-size: 42px;
  color: #007aff;
}

.upload-tip {
  color: #667085;
  font-size: 13px;
}

.upload-actions {
  justify-content: flex-end;
  margin-top: 12px;
}

.file-panel-head {
  justify-content: space-between;
  margin-bottom: 12px;
}

.file-panel-head h3 {
  margin: 0;
  font-size: 16px;
  color: #1f2937;
}

.file-panel-head span {
  color: #667085;
  font-size: 13px;
}

.preview-frame-wrap {
  height: 68vh;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.preview-frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff;
}

@media (max-width: 720px) {
  .knowledge-header {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
