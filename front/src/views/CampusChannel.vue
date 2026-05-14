<template>
  <div class="campus-channel-page">
    <section class="channel-hero">
      <div>
        <h1>校园频道</h1>
        <p>聚合校园公开频道内容，帮助学生快速了解通知、学习交流、赛事组队、失物招领和资料共享等信息。</p>
        <div class="hero-meta">
          <el-tag effect="plain">中国地质大学（武汉）频道</el-tag>
          <span>{{ stats.latest_scraped_at ? `最近采集 ${formatDate(stats.latest_scraped_at)}` : '公开频道' }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button :icon="Refresh" :loading="scraping" @click="scrapeChannel">刷新采集</el-button>
        <el-button type="primary" :icon="Connection" :loading="syncing" @click="syncRag">同步到知识库</el-button>
      </div>
    </section>

    <section class="filters">
      <el-input v-model="filters.keyword" placeholder="搜索关键词" clearable @keyup.enter="reload" />
      <el-select v-model="filters.section" placeholder="版块" clearable @change="reload">
        <el-option v-for="section in sections" :key="section" :label="section" :value="section" />
      </el-select>
      <el-select v-model="filters.sort_by" placeholder="排序" @change="reload">
        <el-option label="最新" value="latest" />
        <el-option label="热门" value="hot" />
      </el-select>
      <el-select v-model="filters.indexed" placeholder="入库状态" @change="reload">
        <el-option label="全部" value="all" />
        <el-option label="已入库" value="true" />
        <el-option label="未入库" value="false" />
      </el-select>
      <el-button @click="reload">重新加载</el-button>
    </section>

    <div class="channel-layout">
      <aside class="section-nav">
        <button
          v-for="section in navSections"
          :key="section"
          :class="{ active: (filters.section || '全部') === section }"
          @click="selectSection(section)"
        >
          {{ section }}
        </button>
      </aside>

      <main class="post-feed" v-loading="loading">
        <el-empty
          v-if="!loading && !posts.length"
          description="当前暂无校园频道内容，请点击“刷新采集”获取最新公开信息。"
        />
        <article v-for="post in posts" :key="post.id" class="post-card">
          <header>
            <div>
              <strong>{{ post.author_name || '频道用户' }}</strong>
              <span>{{ post.publish_time_text || formatDate(post.publish_time || post.scraped_at) }}</span>
            </div>
            <div class="tags">
              <el-tag size="small" effect="plain">{{ post.section_name || '其他版块' }}</el-tag>
              <el-tag size="small" :type="post.is_indexed ? 'success' : 'info'">{{ post.is_indexed ? '已入库' : '未入库' }}</el-tag>
            </div>
          </header>
          <h3>{{ post.title || '未命名帖子' }}</h3>
          <p>{{ post.summary || post.content }}</p>
          <div v-if="post.images?.length" class="post-images">
            <img v-for="img in post.images.slice(0, 3)" :key="img" :src="img" alt="校园频道图片" />
            <span v-if="post.images.length > 3">+{{ post.images.length - 3 }}</span>
          </div>
          <footer>
            <span>赞 {{ post.like_count || 0 }}</span>
            <span>评论 {{ post.comment_count || 0 }}</span>
            <span>分享 {{ post.share_count || 0 }}</span>
            <el-button link type="primary" @click="openDetail(post)">查看详情</el-button>
          </footer>
        </article>
        <el-pagination
          v-if="total > pageSize"
          layout="prev, pager, next"
          :total="total"
          :page-size="pageSize"
          v-model:current-page="page"
          @current-change="loadPosts"
        />
      </main>

      <aside class="stats-panel">
        <h3>频道概览</h3>
        <div class="stat-row"><span>帖子总数</span><strong>{{ stats.total_posts }}</strong></div>
        <div class="stat-row"><span>已入库</span><strong>{{ stats.indexed_posts }}</strong></div>
        <h4>版块数量</h4>
        <div v-for="item in stats.sections" :key="item.name" class="section-count">
          <span>{{ item.name }}</span><em>{{ item.count }}</em>
        </div>
        <p class="source-note">内容来源于校园公开频道，仅供信息聚合与问答参考，请以学校官方通知为准。</p>
      </aside>
    </div>

    <el-dialog v-model="detailVisible" :title="selectedPost?.title || '帖子详情'" width="680px">
      <div v-if="selectedPost" class="detail">
        <div class="detail-meta">
          {{ selectedPost.section_name || '其他版块' }} · {{ selectedPost.author_name || '频道用户' }} ·
          {{ selectedPost.publish_time_text || formatDate(selectedPost.publish_time || selectedPost.scraped_at) }}
        </div>
        <p>{{ selectedPost.content }}</p>
        <div v-if="selectedPost.images?.length" class="image-list">
          <img v-for="img in selectedPost.images" :key="img" :src="img" alt="校园频道图片" />
        </div>
        <section v-if="selectedPost.raw_data?.comments?.length" class="comments-block">
          <h4>公开评论预览</h4>
          <div v-for="comment in selectedPost.raw_data.comments" :key="`${comment.time}-${comment.content}`" class="comment-item">
            <span>{{ comment.time }}</span>
            <p>{{ comment.content }}</p>
          </div>
        </section>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Connection, Refresh } from '@element-plus/icons-vue';
import { useUserStore } from '../store/user';

const CHANNEL_URL = 'https://pd.qq.com/g/px50o26u67';
const userStore = useUserStore();
const router = useRouter();
const posts = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const loading = ref(false);
const scraping = ref(false);
const syncing = ref(false);
const detailVisible = ref(false);
const selectedPost = ref(null);
const stats = ref({ total_posts: 0, indexed_posts: 0, sections: [], latest_scraped_at: '' });
const filters = reactive({ section: '', keyword: '', sort_by: 'latest', indexed: 'all' });

const navSections = ['全部', '通知', '学习交流', '赛事组队', '失物招领|寻物启事', '组织小喇叭', '期末｜资料共享', '二手交易', '其他版块'];
const sections = computed(() => navSections.filter(s => s !== '全部'));

const authHeaders = () => ({ Authorization: `Bearer ${userStore.getToken}` });

const ensureLogin = () => {
  userStore.initAuthState();
  if (!userStore.getLoginStatus || !userStore.getToken) {
    ElMessage.warning('请先登录后再查看校园频道');
    router.push({ path: '/login', query: { redirect: '/campus-channel' } });
    return false;
  }
  return true;
};

const formatDate = (value) => {
  if (!value) return '未知时间';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
};

const loadStats = async () => {
  const resp = await fetch('/api/campus-channel/stats', { headers: authHeaders() });
  const data = await resp.json();
  stats.value = data.data || stats.value;
};

const loadPosts = async () => {
  if (!ensureLogin()) return;
  loading.value = true;
  try {
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize),
      sort_by: filters.sort_by,
      indexed: filters.indexed
    });
    if (filters.section) params.set('section', filters.section);
    if (filters.keyword) params.set('keyword', filters.keyword);
    const resp = await fetch(`/api/campus-channel/posts?${params}`, { headers: authHeaders() });
    const data = await resp.json();
    posts.value = data.data?.items || [];
    total.value = data.data?.total || 0;
  } catch (e) {
    ElMessage.error('校园频道内容加载失败');
  } finally {
    loading.value = false;
  }
};

const reload = async () => {
  page.value = 1;
  await Promise.all([loadPosts(), loadStats()]);
};

const scrapeChannel = async () => {
  if (!ensureLogin()) return;
  scraping.value = true;
  try {
    const resp = await fetch('/api/campus-channel/scrape', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        channel_url: CHANNEL_URL,
        max_posts: 100,
        since_days: 7,
        include_images: true,
        dry_run: false
      })
    });
    const data = await resp.json();
    if (!resp.ok || data.data?.success === false) throw new Error(data.data?.message || data.detail);
    ElMessage.success(data.data?.message || '校园频道采集完成');
    await reload();
  } catch (e) {
    ElMessage.error('校园频道内容采集失败，请稍后重试。若页面需要登录或限制访问，请检查频道公开访问状态。');
  } finally {
    scraping.value = false;
  }
};

const syncRag = async () => {
  if (!ensureLogin()) return;
  syncing.value = true;
  try {
    const resp = await fetch('/api/campus-channel/sync-rag', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_ids: [], sync_all_unindexed: true })
    });
    const data = await resp.json();
    ElMessage.success(`已同步 ${data.data?.indexed_count || 0} 条到知识库`);
    await reload();
  } catch {
    ElMessage.error('同步到知识库失败');
  } finally {
    syncing.value = false;
  }
};

const selectSection = (section) => {
  filters.section = section === '全部' ? '' : section;
  reload();
};

const openDetail = (post) => {
  selectedPost.value = post;
  detailVisible.value = true;
};

onMounted(reload);
</script>

<style scoped>
.campus-channel-page { padding: 24px; color: #2f2a24; }
.channel-hero { display: flex; justify-content: space-between; gap: 24px; padding: 22px 24px; background: #fff; border: 1px solid #ebe7df; border-radius: 8px; }
.channel-hero h1 { margin: 0 0 8px; font-size: 24px; }
.channel-hero p { margin: 0; color: #6f6a61; line-height: 1.6; }
.hero-meta { display: flex; gap: 12px; align-items: center; margin-top: 12px; color: #8a8479; }
.hero-actions { display: flex; align-items: flex-start; gap: 10px; }
.filters { display: grid; grid-template-columns: minmax(220px, 1fr) 160px 120px 130px 100px; gap: 10px; margin: 16px 0; }
.channel-layout { display: grid; grid-template-columns: 180px minmax(0, 1fr) 260px; gap: 16px; align-items: start; }
.section-nav, .stats-panel { background: #fff; border: 1px solid #ebe7df; border-radius: 8px; padding: 12px; }
.section-nav button { display: block; width: 100%; border: 0; background: transparent; text-align: left; padding: 10px 12px; border-radius: 6px; color: #5e5a52; cursor: pointer; }
.section-nav button.active, .section-nav button:hover { background: #f2efe8; color: #1f1c18; }
.post-feed { min-height: 420px; }
.post-card { background: #fff; border: 1px solid #ebe7df; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.post-card header, .post-card footer { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
.post-card header span, .post-card footer span { color: #918a80; font-size: 12px; }
.post-card h3 { margin: 12px 0 8px; font-size: 16px; }
.post-card p { margin: 0; color: #5e5a52; line-height: 1.7; white-space: pre-wrap; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.stats-panel h3 { margin: 2px 0 12px; }
.stats-panel h4 { margin: 18px 0 10px; font-size: 14px; }
.stat-row, .section-count { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0ede7; }
.section-count em { font-style: normal; color: #8a8479; }
.source-note { margin-top: 14px; color: #8a8479; line-height: 1.6; font-size: 12px; }
.detail-meta { color: #8a8479; margin-bottom: 12px; }
.detail p { white-space: pre-wrap; line-height: 1.7; }
.post-images { display: flex; gap: 8px; align-items: center; margin: 10px 0; }
.post-images img { width: 72px; height: 72px; border-radius: 6px; object-fit: cover; border: 1px solid #ece7de; }
.post-images span { color: #8a8479; font-size: 13px; }
.image-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; }
.image-list img { width: 100%; aspect-ratio: 1 / 1; border-radius: 6px; object-fit: cover; }
.comments-block { margin-top: 18px; border-top: 1px solid #ece7de; padding-top: 12px; }
.comments-block h4 { margin: 0 0 8px; color: #3b3833; }
.comment-item { padding: 8px 0; border-bottom: 1px solid #f2eee7; }
.comment-item span { color: #8a8479; font-size: 12px; }
.comment-item p { margin: 4px 0 0; }
@media (max-width: 1100px) {
  .channel-layout { grid-template-columns: 1fr; }
  .section-nav { display: flex; overflow-x: auto; }
  .section-nav button { white-space: nowrap; }
  .filters { grid-template-columns: 1fr 1fr; }
  .channel-hero { flex-direction: column; }
}
</style>
