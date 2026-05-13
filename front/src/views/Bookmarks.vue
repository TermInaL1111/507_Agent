<template>
  <div class="bookmarks-page page-container">
    <div class="page-header">
      <h2>我的收藏</h2>
      <el-button :icon="Refresh" @click="loadBookmarks" :loading="loading">刷新</el-button>
    </div>
    <el-empty v-if="!loading && !bookmarks.length" description="还没有收藏任何内容" />
    <div v-else class="bookmark-list">
      <div v-for="bm in bookmarks" :key="bm.id" class="bookmark-card">
        <div class="bookmark-content">{{ bm.content }}</div>
        <div class="bookmark-footer">
          <span class="bookmark-time">{{ bm.created_at?.slice(0, 16) }}</span>
          <el-button link type="danger" size="small" @click="removeBookmark(bm.id)">取消收藏</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Refresh } from '@element-plus/icons-vue';
import { useUserStore } from '../store/user';

const userStore = useUserStore();
const bookmarks = ref([]);
const loading = ref(false);

const loadBookmarks = async () => {
  loading.value = true;
  try {
    const token = userStore.getToken;
    const resp = await fetch('/api/bookmarks', { headers: { Authorization: `Bearer ${token}` } });
    const data = await resp.json();
    bookmarks.value = data.bookmarks || [];
  } catch { ElMessage.error('加载收藏失败'); }
  loading.value = false;
};

const removeBookmark = async (id) => {
  try {
    const token = userStore.getToken;
    await fetch(`/api/bookmarks/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    bookmarks.value = bookmarks.value.filter(b => b.id !== id);
    ElMessage.success('已取消收藏');
  } catch { ElMessage.error('操作失败'); }
};

onMounted(loadBookmarks);
</script>

<style scoped>
.bookmarks-page { padding: 24px; max-width: 800px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.bookmark-list { display: flex; flex-direction: column; gap: 12px; }
.bookmark-card { background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 14px; }
.bookmark-content { font-size: 14px; color: #303133; line-height: 1.6; white-space: pre-wrap; }
.bookmark-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; }
.bookmark-time { font-size: 12px; color: #c0c4cc; }
</style>
