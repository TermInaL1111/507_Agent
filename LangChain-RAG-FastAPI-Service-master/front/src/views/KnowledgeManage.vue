<template>
  <div class="knowledge-manage-page page-container">
    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>单文件上传</span>
              <el-tag type="info" effect="plain">/api/vector/add/single</el-tag>
            </div>
          </template>

          <el-upload
            v-model:file-list="singleFileList"
            drag
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.txt,.md,.pptx,.docx"
            :on-change="handleSingleFileChange"
            :on-remove="handleSingleFileRemove"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">拖拽文件到此，或 <em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 PDF/TXT/MD/PPTX/DOCX，单文件建议不超过 20MB</div>
            </template>
          </el-upload>

          <el-progress v-if="singleUploadProgress > 0" :percentage="singleUploadProgress" :status="singleUploading ? '' : 'success'" />

          <div class="action-row">
            <el-button type="primary" :loading="singleUploading" @click="uploadSingleFile">
              上传单文件
            </el-button>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>多文件上传</span>
              <el-tag type="info" effect="plain">/api/vector/add/multiple</el-tag>
            </div>
          </template>

          <el-upload
            v-model:file-list="multipleFileList"
            drag
            multiple
            :auto-upload="false"
            accept=".pdf,.txt,.md,.pptx,.docx"
            :on-change="handleMultipleFilesChange"
            :on-remove="handleMultipleFileRemove"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">拖拽多个文件到此，或 <em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">文件总大小建议不超过 200MB</div>
            </template>
          </el-upload>

          <el-progress v-if="multipleUploadProgress > 0" :percentage="multipleUploadProgress" :status="multipleUploading ? '' : 'success'" />

          <div class="action-row">
            <el-button type="primary" :loading="multipleUploading" @click="uploadMultipleFiles">
              上传多文件
            </el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>向量库维护</span>
              <el-tag type="danger" effect="plain">/api/vector/clean</el-tag>
            </div>
          </template>

          <el-alert
            title="该操作将删除当前用户上传的全部向量数据，请谨慎操作"
            type="warning"
            :closable="false"
            show-icon
            class="block-alert"
          />

          <el-button type="danger" plain :loading="cleaningVectors" @click="confirmCleanVectors">
            清空我的向量数据
          </el-button>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>文档重排测试</span>
              <el-tag type="success" effect="plain">/api/reorder</el-tag>
            </div>
          </template>

          <el-form label-position="top">
            <el-form-item label="查询问题">
              <el-input
                v-model="reorderForm.query"
                type="textarea"
                :rows="2"
                placeholder="输入用于重排序的查询问题"
              />
            </el-form-item>

            <el-form-item label="候选文档列表">
              <div class="doc-list">
                <div v-for="(_, index) in reorderForm.documents" :key="`doc-${index}`" class="doc-item">
                  <el-input
                    v-model="reorderForm.documents[index]"
                    type="textarea"
                    :rows="2"
                    :placeholder="`文档 ${index + 1}`"
                  />
                  <el-button
                    type="danger"
                    plain
                    :disabled="reorderForm.documents.length === 1"
                    @click="removeDocument(index)"
                  >
                    删除
                  </el-button>
                </div>
              </div>
            </el-form-item>

            <div class="action-row">
              <el-button plain @click="addDocument">新增文档</el-button>
              <el-button type="primary" :loading="reordering" @click="runReorderTest">执行重排</el-button>
            </div>
          </el-form>

          <el-table v-if="reorderResults.length" :data="reorderResults" border class="result-table">
            <el-table-column label="#" width="60">
              <template #default="scope">{{ scope.$index + 1 }}</template>
            </el-table-column>
            <el-table-column label="文档内容" min-width="260" show-overflow-tooltip>
              <template #default="scope">{{ scope.row.document }}</template>
            </el-table-column>
            <el-table-column label="分数" width="120" align="center">
              <template #default="scope">
                {{ scope.row.similarityText }}
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-else description="重排结果将显示在这里" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';
import { ElMessage, ElMessageBox } from 'element-plus';
import { apiConfig } from '../config/api';

const singleFileList = ref([]);
const selectedSingleFile = ref(null);
const singleUploading = ref(false);
const singleUploadProgress = ref(0);

const multipleFileList = ref([]);
const selectedMultipleFiles = ref([]);
const multipleUploading = ref(false);
const multipleUploadProgress = ref(0);

const cleaningVectors = ref(false);

const reorderForm = ref({
  query: '',
  documents: ['', '']
});
const reordering = ref(false);
const reorderResults = ref([]);

const getAuthHeaders = () => {
  const token = localStorage.getItem('jwt_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const getErrorMessage = (error, fallback = '请求失败，请稍后重试') => {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback;
};

const handleSingleFileChange = (file, fileList) => {
  singleFileList.value = fileList.slice(-1);
  selectedSingleFile.value = singleFileList.value[0]?.raw || null;
};

const handleSingleFileRemove = () => {
  selectedSingleFile.value = null;
};

const handleMultipleFilesChange = (file, fileList) => {
  multipleFileList.value = fileList;
  selectedMultipleFiles.value = fileList.map(item => item.raw).filter(Boolean);
};

const handleMultipleFileRemove = () => {
  selectedMultipleFiles.value = multipleFileList.value.map(item => item.raw).filter(Boolean);
};

const uploadSingleFile = async () => {
  if (!selectedSingleFile.value) {
    ElMessage.warning('请先选择要上传的文件');
    return;
  }

  singleUploading.value = true;
  singleUploadProgress.value = 0;

  try {
    const formData = new FormData();
    formData.append('file', selectedSingleFile.value);

    const response = await axios.post(apiConfig.endpoints.uploadSingleFile, formData, {
      headers: {
        ...getAuthHeaders()
      },
      onUploadProgress: (progressEvent) => {
        if (!progressEvent.total) return;
        singleUploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100);
      }
    });

    ElMessage.success(response.data?.message || '单文件上传成功');
    singleFileList.value = [];
    selectedSingleFile.value = null;
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '单文件上传失败'));
  } finally {
    singleUploading.value = false;
    if (singleUploadProgress.value < 100) {
      singleUploadProgress.value = 0;
    }
  }
};

const uploadMultipleFiles = async () => {
  if (!selectedMultipleFiles.value.length) {
    ElMessage.warning('请先选择要上传的文件');
    return;
  }

  multipleUploading.value = true;
  multipleUploadProgress.value = 0;

  try {
    const formData = new FormData();
    selectedMultipleFiles.value.forEach((file) => {
      formData.append('files', file);
    });

    const response = await axios.post(apiConfig.endpoints.uploadMultipleFiles, formData, {
      headers: {
        ...getAuthHeaders()
      },
      onUploadProgress: (progressEvent) => {
        if (!progressEvent.total) return;
        multipleUploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100);
      }
    });

    ElMessage.success(response.data?.message || '多文件上传成功');
    multipleFileList.value = [];
    selectedMultipleFiles.value = [];
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '多文件上传失败'));
  } finally {
    multipleUploading.value = false;
    if (multipleUploadProgress.value < 100) {
      multipleUploadProgress.value = 0;
    }
  }
};

const confirmCleanVectors = async () => {
  try {
    await ElMessageBox.confirm(
      '该操作会清空你上传的所有向量数据，且不可恢复。确认继续吗？',
      '确认清空向量库',
      {
        confirmButtonText: '确认清空',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
  } catch {
    return;
  }

  cleaningVectors.value = true;

  try {
    const response = await axios.delete(apiConfig.endpoints.cleanVectors, {
      headers: {
        ...getAuthHeaders()
      }
    });
    ElMessage.success(response.data?.message || '向量数据清理成功');
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '向量数据清理失败'));
  } finally {
    cleaningVectors.value = false;
  }
};

const addDocument = () => {
  reorderForm.value.documents.push('');
};

const removeDocument = (index) => {
  if (reorderForm.value.documents.length <= 1) return;
  reorderForm.value.documents.splice(index, 1);
};

const runReorderTest = async () => {
  const query = reorderForm.value.query.trim();
  const documents = reorderForm.value.documents.map(item => item.trim()).filter(Boolean);

  if (!query) {
    ElMessage.warning('请先输入查询问题');
    return;
  }

  if (!documents.length) {
    ElMessage.warning('请至少输入一条候选文档');
    return;
  }

  reordering.value = true;

  try {
    const response = await axios.post(
      apiConfig.endpoints.reorderDocuments,
      { query, documents },
      {
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        }
      }
    );

    const rawResults = response.data?.data?.documents || response.data?.documents || [];
    reorderResults.value = rawResults.map((item, index) => {
      if (typeof item === 'string') {
        return {
          rank: index + 1,
          document: item,
          similarity: null,
          similarityText: '-'
        };
      }

      const score = Number(item?.similarity ?? item?.score ?? item?.rerank_score);
      return {
        rank: index + 1,
        document: item?.document || item?.content || item?.text || JSON.stringify(item),
        similarity: Number.isNaN(score) ? null : score,
        similarityText: Number.isNaN(score) ? '-' : score.toFixed(4)
      };
    });

    ElMessage.success(response.data?.message || '文档重排完成');
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '文档重排失败'));
    reorderResults.value = [];
  } finally {
    reordering.value = false;
  }
};
</script>

<style scoped>
.knowledge-manage-page {
  padding: 20px;
}

.panel-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.action-row {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.block-alert {
  margin-bottom: 12px;
}

.doc-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.doc-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.doc-item :deep(.el-textarea) {
  flex: 1;
}

.result-table {
  margin-top: 12px;
}

@media (max-width: 992px) {
  .knowledge-manage-page {
    padding: 12px;
  }

  .doc-item {
    flex-direction: column;
  }
}
</style>
