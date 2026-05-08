<template>
  <div class="ai-chat-container">
    <el-page-header title="AI问答" @back="goToSessions">
      <template #content>
        <span class="page-title">AI智能问答</span>
      </template>
      <template #extra>
        <el-button type="primary" @click="goToSessions">
          <el-icon><ChatLineSquare /></el-icon>
          会话管理
        </el-button>
      </template>
    </el-page-header>
    
    <div class="chat-content">
      <div class="messages-container" ref="messagesContainer">
        <div 
          v-for="(message, index) in messages" 
          :key="index"
          :class="['message', message.role === 'user' ? 'user-message' : 'ai-message']"
        >
          <div class="message-avatar">
            <el-avatar 
              :size="40" 
              :icon="message.role === 'user' ? User : ChatDotRound"
              :style="{ background: message.role === 'user' ? '#409EFF' : '#67C23A' }"
            />
          </div>
          <div class="message-content">
            <div v-if="message.role === 'assistant' && message.content === '' && !message.resultCard" class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div v-else v-html="formatMessage(message.content)"></div>

            <div v-if="message.role === 'assistant' && message.resultCard" class="result-card" :class="`result-card--${message.resultCard.type}`">
              <div class="result-card-header">
                <span class="result-card-title">{{ message.resultCard.title || '结果卡片' }}</span>
                <el-tag size="small" effect="light" :type="getResultCardTagType(message.resultCard.type)">
                  {{ getResultCardTypeLabel(message.resultCard.type) }}
                </el-tag>
              </div>

              <p v-if="message.resultCard.summary" class="result-card-summary">{{ message.resultCard.summary }}</p>

              <ul v-if="message.resultCard.type === 'answer' && message.resultCard.highlights?.length" class="card-list">
                <li v-for="(point, pointIndex) in message.resultCard.highlights" :key="`a-${index}-${pointIndex}`">{{ point }}</li>
              </ul>

              <div v-if="message.resultCard.type === 'recommendation'" class="card-section">
                <div v-if="message.resultCard.strategy" class="card-meta">推荐策略：{{ message.resultCard.strategy }}</div>
                <ul v-if="message.resultCard.recommendations?.length" class="card-recommend-list">
                  <li
                    v-for="(item, itemIndex) in message.resultCard.recommendations"
                    :key="`r-${index}-${itemIndex}`"
                    class="card-recommend-item"
                  >
                    <div class="card-recommend-head">
                      <span class="card-recommend-title">{{ item.title || `推荐项${itemIndex + 1}` }}</span>
                      <el-tag v-if="item.score" size="small" type="success" effect="plain">{{ item.score }}</el-tag>
                    </div>
                    <p v-if="item.reason" class="card-recommend-reason">{{ item.reason }}</p>
                    <div v-if="item.tags?.length" class="card-tags">
                      <el-tag v-for="(tag, tagIndex) in item.tags" :key="`rt-${index}-${itemIndex}-${tagIndex}`" size="small" effect="plain">
                        {{ tag }}
                      </el-tag>
                    </div>
                  </li>
                </ul>
              </div>

              <div v-if="message.resultCard.type === 'navigation'" class="card-section">
                <div class="card-meta" v-if="message.resultCard.start || message.resultCard.end">
                  {{ message.resultCard.start || '起点未提供' }} → {{ message.resultCard.end || '终点未提供' }}
                </div>
                <ul v-if="message.resultCard.routes?.length" class="card-route-list">
                  <li v-for="(routeItem, routeIndex) in message.resultCard.routes" :key="`n-${index}-${routeIndex}`" class="card-route-item">
                    <div class="card-route-head">
                      <span>{{ routeItem.title || `路线${routeIndex + 1}` }}</span>
                      <span class="card-route-meta">
                        {{ routeItem.duration || '时长未知' }}
                        <template v-if="routeItem.distance">· {{ routeItem.distance }}</template>
                      </span>
                    </div>
                    <ol v-if="routeItem.steps?.length" class="card-route-steps">
                      <li v-for="(stepText, stepIndex) in routeItem.steps" :key="`ns-${index}-${routeIndex}-${stepIndex}`">{{ stepText }}</li>
                    </ol>
                  </li>
                </ul>
                <div class="card-actions" v-if="message.resultCard.mapUrl">
                  <el-button v-if="message.resultCard.mapUrl" size="small" @click="openResultCardLink(message.resultCard.mapUrl)">
                    {{ message.resultCard.start ? '查看站内路线' : '查看地图' }}
                  </el-button>
                </div>
              </div>

              <div v-if="message.resultCard.type === 'schedule'" class="card-section">
                <div class="card-meta" v-if="message.resultCard.view">
                  {{ message.resultCard.view === 'week' ? '周课表视图' : '今日课表' }}
                  <span v-if="message.resultCard.events?.length">（{{ message.resultCard.events.length }} 节课）</span>
                </div>
                <div class="schedule-timeline" v-if="message.resultCard.view !== 'week' && message.resultCard.events?.length">
                  <div
                    v-for="(evt, evtIdx) in message.resultCard.events"
                    :key="`se-${index}-${evtIdx}`"
                    class="schedule-item"
                    :class="{ 'schedule-item--conflict': evt.conflict }"
                  >
                    <span class="schedule-time">{{ evt.time || '--:--' }}</span>
                    <span class="schedule-title">{{ evt.title }}</span>
                    <span class="schedule-loc" v-if="evt.location">{{ evt.location }}</span>
                  </div>
                </div>
                <div class="schedule-week-grid" v-if="message.resultCard.view === 'week' && message.resultCard.events?.length">
                  <div
                    v-for="(evt, evtIdx) in message.resultCard.events"
                    :key="`sw-${index}-${evtIdx}`"
                    class="schedule-week-item"
                  >
                    <span class="schedule-week-day">{{ evt.weekday || '--' }}</span>
                    <span class="schedule-week-time">{{ evt.time }}</span>
                    <span class="schedule-week-title">{{ evt.title }}</span>
                    <span class="schedule-week-loc" v-if="evt.location">{{ evt.location }}</span>
                  </div>
                </div>
              </div>

              <div v-if="message.resultCard.type === 'check'" class="card-section">
                <div class="card-meta">
                  校验结果：
                  <el-tag size="small" :type="getCheckStatusTagType(message.resultCard.status)">
                    {{ message.resultCard.status || 'unknown' }}
                  </el-tag>
                </div>
                <ul v-if="message.resultCard.checks?.length" class="card-check-list">
                  <li v-for="(checkItem, checkIndex) in message.resultCard.checks" :key="`c-${index}-${checkIndex}`" class="card-check-item">
                    <div class="card-check-head">
                      <span>{{ checkItem.name || `检查项${checkIndex + 1}` }}</span>
                      <el-tag size="small" :type="getCheckStatusTagType(checkItem.status)">
                        {{ checkItem.status || 'unknown' }}
                      </el-tag>
                    </div>
                    <p v-if="checkItem.detail" class="card-check-detail">{{ checkItem.detail }}</p>
                    <p v-if="checkItem.suggestion" class="card-check-suggestion">建议：{{ checkItem.suggestion }}</p>
                  </li>
                </ul>
              </div>
            </div>

            <div v-if="message.role === 'assistant' && message.toolCalls?.length" class="tool-calls">
              <div
                v-for="(tc, tcIdx) in message.toolCalls"
                :key="`tc-${index}-${tcIdx}`"
                class="tool-call-chip"
                :class="{ 'tool-call--running': tc.status === 'running', 'tool-call--done': tc.status === 'done' }"
              >
                <span class="tool-call-icon">{{ tc.status === 'running' ? '⏳' : '✅' }}</span>
                <span class="tool-call-label">{{ tc.tool }}</span>
              </div>
            </div>

            <div v-if="message.role === 'assistant' && message.sources?.length" class="message-sources">
              <button
                v-for="(source, sourceIndex) in message.sources"
                :key="source.source_id || `${index}-${sourceIndex}`"
                class="source-pill"
                type="button"
                @click="openSourceDialog(source)"
              >
                {{ getSourceName(source, sourceIndex) }}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div class="input-area">
        <div v-if="pendingFiles.length" class="file-chips">
          <el-tag
            v-for="(f, idx) in pendingFiles"
            :key="idx"
            closable
            size="small"
            type="info"
            @close="removeFile(idx)"
          >
            {{ f.name }}
          </el-tag>
        </div>
        <div class="input-container">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :show-file-list="false"
            :limit="3"
            accept=".pdf,.docx,.txt"
            @change="onFileChange"
          >
            <el-button :disabled="isLoading" size="large" circle>
              <el-icon><Link /></el-icon>
            </el-button>
          </el-upload>
          <el-input
            v-model="userInput"
            type="textarea"
            :rows="3"
            placeholder="输入问题或上传课表 PDF..."
            class="chat-input"
            resize="none"
            @keydown.enter.prevent="handleEnter"
          />
          <el-button
            type="primary"
            size="large"
            class="send-button"
            :disabled="isLoading || (!userInput.trim() && !pendingFiles.length)"
            @click="sendMessage"
          >
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="sourceDialogVisible" title="来源文件" width="520px" class="source-dialog">
      <div v-if="selectedSource" class="source-dialog-body">
        <div class="source-detail-row"><span class="source-detail-label">文件名</span><span class="source-detail-value">{{ getSourceName(selectedSource) }}</span></div>
        <div class="source-detail-row"><span class="source-detail-label">知识库类型</span><span class="source-detail-value">{{ selectedSource.kb_type || '暂无类型信息' }}</span></div>
        <div class="source-detail-row"><span class="source-detail-label">文档分类</span><span class="source-detail-value">{{ selectedSource.category || '暂无分类信息' }}</span></div>
        <div v-if="selectedSource.source === 'training_program' || selectedSource.kb_type === 'training_program'" class="source-detail-row"><span class="source-detail-label">学院</span><span class="source-detail-value">{{ selectedSource.college || '暂无学院信息' }}</span></div>
        <div v-if="selectedSource.source === 'training_program' || selectedSource.kb_type === 'training_program'" class="source-detail-row"><span class="source-detail-label">专业</span><span class="source-detail-value">{{ selectedSource.major || '暂无专业信息' }}</span></div>
        <div v-if="selectedSource.relativePath" class="source-detail-row"><span class="source-detail-label">文件路径</span><span class="source-detail-value">{{ selectedSource.relativePath }}</span></div>
        <div v-if="selectedSource.chunkIndex !== undefined && selectedSource.chunkIndex !== null" class="source-detail-row"><span class="source-detail-label">切片序号</span><span class="source-detail-value">第 {{ Number(selectedSource.chunkIndex) + 1 }} 段</span></div>
        <div class="source-detail-row"><span class="source-detail-label">页码</span><span class="source-detail-value">{{ selectedSource.page ? `第 ${selectedSource.page} 页` : '暂无页码信息' }}</span></div>
        <div class="source-snippet"><div class="source-detail-label">命中片段</div><p>{{ selectedSource.snippet || selectedSource.content || '暂无命中片段' }}</p></div>
        <div v-if="!canDownloadSelectedSource" class="source-download-tip">当前来源文件暂不支持下载</div>
      </div>
      <template #footer>
        <el-button @click="sourceDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!canDownloadSelectedSource || isDownloadingSource" @click="downloadSelectedSource">下载文件</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, nextTick, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Link, User, ChatDotRound, ChatLineSquare, Promotion } from '@element-plus/icons-vue';
import { marked } from 'marked';
import { markedHighlight } from 'marked-highlight';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import 'highlight.js/styles/monokai-sublime.css';
import 'highlight.js/lib/common';
import { useUserStore } from '../store/user';
import { useSessionStore } from '../store/session';

// 从cookie中获取CSRF token
const getCsrfToken = () => {
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  return cookieValue || '';
};

// 聊天消息
const messages = ref([
  { role: 'assistant', content: '你好！我是AI助手，有什么可以帮助你的吗？', sources: [], resultCard: null }
]);
const userInput = ref('');
const messagesContainer = ref(null);
const isLoading = ref(false);
const sessionId = ref('');
const hasJumped = ref(false);
const sourceDialogVisible = ref(false);
const selectedSource = ref(null);
const isDownloadingSource = ref(false);
const pendingFiles = ref([]);
const uploadRef = ref(null);

const canDownloadSelectedSource = computed(() => {
  if (!selectedSource.value) return false;
  return Boolean(selectedSource.value.downloadable && (selectedSource.value.file_id || selectedSource.value.download_url));
});

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const sessionStore = useSessionStore();

const requireLogin = () => {
  userStore.initAuthState();
  if (!userStore.getLoginStatus || !userStore.getToken) {
    ElMessage.warning('请先登录后再使用问答功能');
    router.push({
      path: '/login',
      query: { redirect: route.fullPath }
    });
    return false;
  }

  return true;
};

// 配置marked使用marked-highlight插件
marked.use(markedHighlight({
  langPrefix: 'hljs language-',
  highlight(code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
    return hljs.highlight(code, { language }).value;
  }
}));

// 格式化消息内容（支持Markdown和代码高亮）
const formatMessage = (content) => {
  if (!content) return '';
  try {
    // 使用marked解析Markdown，并用DOMPurify清理HTML
    const parsed = marked(content, {
      breaks: true,
      gfm: true,
      headerIds: false,
      mangle: false
    });
    const sanitized = DOMPurify.sanitize(parsed);
    return sanitized;
  } catch (error) {
    console.error('Markdown解析错误:', error);
    return content;
  }
};

const normalizeCardType = (typeValue) => {
  const rawType = String(typeValue || '').toLowerCase();

  const mapping = {
    answer: 'answer',
    qa: 'answer',
    question_answer: 'answer',
    recommendation: 'recommendation',
    recommend: 'recommendation',
    suggestion: 'recommendation',
    navigation: 'navigation',
    route: 'navigation',
    map: 'navigation',
    schedule: 'schedule',
    timetable: 'schedule',
    check: 'check',
    validation: 'check',
    verify: 'check',
    audit: 'check'
  };

  return mapping[rawType] || '';
};

const toArray = (value) => {
  if (Array.isArray(value)) return value;
  if (value === null || value === undefined || value === '') return [];
  return [value];
};

const parseObjectFromJSONString = (value) => {
  if (typeof value !== 'string') return null;
  const text = value.trim();
  if (!text.startsWith('{') || !text.endsWith('}')) return null;

  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
};

const getResultCardTypeLabel = (type) => {
  const labelMap = {
    answer: '问答型',
    recommendation: '推荐型',
    navigation: '导航型',
    schedule: '课表型',
    check: '检查型'
  };

  return labelMap[type] || '结果型';
};

const getResultCardTagType = (type) => {
  const tagMap = {
    answer: 'primary',
    recommendation: 'success',
    navigation: 'warning',
    schedule: 'success',
    check: 'danger'
  };

  return tagMap[type] || 'info';
};

const getCheckStatusTagType = (status) => {
  const normalized = String(status || '').toLowerCase();
  if (['pass', 'ok', 'success'].includes(normalized)) return 'success';
  if (['warn', 'warning', 'pending'].includes(normalized)) return 'warning';
  if (['fail', 'error', 'blocked'].includes(normalized)) return 'danger';
  return 'info';
};

const openResultCardLink = (url) => {
  if (!url) return;
  if (url.startsWith('/')) {
    router.push(url);
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
};

const normalizeResultCard = (rawCard) => {
  if (!rawCard || typeof rawCard !== 'object') return null;

  let type = normalizeCardType(rawCard.type || rawCard.card_type || rawCard.kind);

  if (!type) {
    if (rawCard.recommendations || rawCard.candidates || rawCard.strategy) {
      type = 'recommendation';
    } else if (rawCard.routes || rawCard.start || rawCard.end || rawCard.from || rawCard.to) {
      type = 'navigation';
    } else if (rawCard.checks || rawCard.verdict || rawCard.issues || rawCard.compliance) {
      type = 'check';
    } else if (rawCard.summary || rawCard.highlights || rawCard.key_points) {
      type = 'answer';
    }
  }

  if (!type) return null;

  const baseCard = {
    type,
    title: rawCard.title || rawCard.name || getResultCardTypeLabel(type),
    summary: rawCard.summary || rawCard.description || ''
  };

  if (type === 'answer') {
    return {
      ...baseCard,
      highlights: toArray(rawCard.highlights || rawCard.key_points || rawCard.points)
    };
  }

  if (type === 'recommendation') {
    const recommendationItems = toArray(rawCard.recommendations || rawCard.items || rawCard.candidates).map((item, index) => {
      if (typeof item === 'string') {
        return {
          title: `推荐项${index + 1}`,
          reason: item,
          score: '',
          tags: []
        };
      }

      return {
        title: item?.title || item?.name || `推荐项${index + 1}`,
        reason: item?.reason || item?.description || '',
        score: item?.score ? String(item.score) : '',
        tags: toArray(item?.tags)
      };
    });

    return {
      ...baseCard,
      strategy: rawCard.strategy || rawCard.goal || '',
      recommendations: recommendationItems
    };
  }

  if (type === 'navigation') {
    const routeItems = toArray(rawCard.routes || rawCard.items).map((item, index) => {
      if (typeof item === 'string') {
        return {
          title: `路线${index + 1}`,
          duration: '',
          distance: '',
          steps: [item]
        };
      }

      return {
        title: item?.title || item?.name || `路线${index + 1}`,
        duration: item?.duration || item?.eta || '',
        distance: item?.distance || '',
        steps: toArray(item?.steps || item?.instructions)
      };
    });

    return {
      ...baseCard,
      start: rawCard.start || rawCard.from || '',
      end: rawCard.end || rawCard.to || rawCard.destination || '',
      mapUrl: rawCard.mapUrl || rawCard.map_url || '',
      routes: routeItems
    };
  }

  if (type === 'schedule') {
    const scheduleEvents = toArray(rawCard.events || rawCard.items).map((item, index) => {
      if (typeof item === 'string') {
        return { title: item, time: '', location: '', weekday: '' };
      }
      return {
        title: item?.title || item?.name || `课程${index + 1}`,
        time: item?.time || item?.startTime || `${item?.start || ''}${item?.end ? '-' + item.end : ''}`,
        location: item?.location || item?.place || '',
        weekday: item?.weekday || item?.day || '',
        type: item?.type || '',
      };
    });

    return {
      ...baseCard,
      view: rawCard.view || (scheduleEvents.length > 10 ? 'week' : 'day'),
      events: scheduleEvents,
    };
  }

  if (type === 'check') {
    const checkItems = toArray(rawCard.checks || rawCard.items || rawCard.issues).map((item, index) => {
      if (typeof item === 'string') {
        return {
          name: `检查项${index + 1}`,
          status: '',
          detail: item,
          suggestion: ''
        };
      }

      return {
        name: item?.name || item?.title || `检查项${index + 1}`,
        status: item?.status || item?.result || '',
        detail: item?.detail || item?.description || '',
        suggestion: item?.suggestion || item?.advice || ''
      };
    });

    return {
      ...baseCard,
      status: rawCard.status || rawCard.verdict || rawCard.compliance || '',
      checks: checkItems
    };
  }

  return null;
};

const extractResultCard = (payload) => {
  if (!payload || typeof payload !== 'object') return null;

  const candidates = [
    payload.result_card,
    payload.resultCard,
    payload.card,
    payload.card_data,
    payload.result,
    payload.data
  ];

  if (payload.type || payload.card_type || payload.kind) {
    candidates.unshift(payload);
  }

  for (const candidate of candidates) {
    const normalized = normalizeResultCard(candidate);
    if (normalized) return normalized;
  }

  return null;
};

const updateAssistantResultCard = (payload) => {
  const currentMessage = messages.value[messages.value.length - 1];
  if (!currentMessage || currentMessage.role !== 'assistant') return;

  const parsedCard = extractResultCard(payload);
  if (parsedCard) {
    currentMessage.resultCard = parsedCard;
  }
};

const normalizeSources = (sourcePayload) => {
  if (!sourcePayload) return [];

  if (Array.isArray(sourcePayload)) {
    return sourcePayload
      .map((item, index) => {
        if (typeof item === 'string') {
          return {
            title: `来源${index + 1}`,
            content: item,
            url: ''
          };
        }

        if (!item || typeof item !== 'object') {
          return null;
        }

        return {
          ...item,
          source_id: item.source_id || item.id || `source_${index + 1}`,
          file_id: item.file_id || '',
          doc_name: item.doc_name || item.file_name || item.title || item.name || `来源${index + 1}`,
          file_name: item.file_name || item.doc_name || item.title || item.name || `来源${index + 1}`,
          source: item.source || '',
          kb_type: item.kb_type || '',
          category: item.category || '',
          college: item.college || '',
          major: item.major || '',
          relativePath: item.relativePath || item.relative_path || '',
          chunkIndex: item.chunkIndex ?? item.chunk_index,
          fileType: item.fileType || item.file_type || '',
          page: item.page,
          snippet: item.snippet || item.content || item.text || '',
          downloadable: Boolean(item.downloadable || item.file_id || item.download_url),
          download_url: item.download_url || '',
          title: item.title || item.doc_name || item.file_name || item.name || `来源${index + 1}`,
          content: item.content || item.snippet || item.text || '',
          url: item.url || item.link || ''
        };
      })
      .filter(Boolean);
  }

  if (typeof sourcePayload === 'string') {
    return [{ title: '来源', content: sourcePayload, url: '' }];
  }

  return [];
};

const updateAssistantSources = (payload) => {
  const currentMessage = messages.value[messages.value.length - 1];
  if (!currentMessage || currentMessage.role !== 'assistant') return;

  const rawSources = payload?.sources || payload?.references || payload?.docs;
  const parsedSources = normalizeSources(rawSources);
  if (parsedSources.length > 0) {
    currentMessage.sources = parsedSources;
  }
};

const getSourceName = (source, index = 0) => {
  return source?.doc_name || source?.file_name || source?.title || source?.name || `来源${index + 1}`;
};

const openSourceDialog = (source) => {
  selectedSource.value = source;
  sourceDialogVisible.value = true;
  if (!source?.file_id && !source?.download_url) {
    ElMessage.info('当前来源文件暂不支持下载');
  }
};

const downloadSelectedSource = async () => {
  if (!canDownloadSelectedSource.value || !selectedSource.value) {
    ElMessage.info('当前来源文件暂不支持下载');
    return;
  }

  if (!requireLogin()) return;

  const token = userStore.getToken;
  const source = selectedSource.value;
  const downloadUrl = source.download_url || `/api/source-file/download/${source.file_id}`;

  try {
    isDownloadingSource.value = true;
    const response = await fetch(downloadUrl, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error(`download failed: ${response.status}`);
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = getSourceName(source);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
    sourceDialogVisible.value = false;
  } catch (error) {
    console.error('文件下载失败:', error);
    ElMessage.error('文件下载失败，请稍后重试');
  } finally {
    isDownloadingSource.value = false;
  }
};

// 文件选择
const onFileChange = (uploadFile) => {
  if (!uploadFile || !uploadFile.raw) return;
  const file = uploadFile.raw;
  const allowed = ['.pdf', '.docx', '.txt'];
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  if (!allowed.includes(ext)) {
    ElMessage.warning('仅支持 PDF、DOCX、TXT 文件');
    return;
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 20MB');
    return;
  }
  if (pendingFiles.value.length >= 3) {
    ElMessage.warning('最多上传 3 个文件');
    return;
  }
  pendingFiles.value.push(file);
  uploadRef.value?.clearFiles();
};

const removeFile = (idx) => {
  pendingFiles.value.splice(idx, 1);
};

const uploadSingleFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const token = userStore.getToken;
  const resp = await fetch('/api/agent/upload', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `上传失败 (${resp.status})`);
  }
  const json = await resp.json();
  return json.data || json;
};

// 处理回车键发送
const handleEnter = (e) => {
  if (!e.shiftKey) {
    sendMessage();
  }
};

// 发送消息
const sendMessage = async () => {
  const hasText = userInput.value.trim();
  const hasFiles = pendingFiles.value.length > 0;
  if ((!hasText && !hasFiles) || isLoading.value) return;
  if (!requireLogin()) return;

  isLoading.value = true;

  // 先上传文件
  let fileContext = '';
  if (hasFiles) {
    try {
      for (const file of pendingFiles.value) {
        const result = await uploadSingleFile(file);
        if (result.events_count > 0) {
          fileContext += `\n📎 已从「${file.name}」导入 ${result.events_count} 条课表。`;
        } else {
          fileContext += `\n📎 已上传「${file.name}」${result.warning ? '（' + result.warning + '）' : ''}。`;
        }
      }
      pendingFiles.value = [];
      uploadRef.value?.clearFiles();
    } catch (e) {
      ElMessage.error(`文件上传失败: ${e.message}`);
      isLoading.value = false;
      return;
    }
  }

  const userMessage = (userInput.value.trim() || '查看我的课表') + fileContext;
  userInput.value = '';

  // 添加用户消息
  messages.value.push({ role: 'user', content: userMessage });
  // 添加AI消息占位
  messages.value.push({ role: 'assistant', content: '', sources: [], resultCard: null });
  
  // 滚动到底部
  await nextTick();
  scrollToBottom();
  
  // 发送请求
  isLoading.value = true;
  try {
    await fetchAIResponse(userMessage);
  } catch (error) {
    console.error('Error fetching AI response:', error);
    if (error.authRequired) {
      messages.value.pop();
      userInput.value = userMessage;
      return;
    }
    // 更新最后一条消息为错误信息
    messages.value[messages.value.length - 1].content = `发生错误: ${error.message || '请检查网络连接和API设置'}`;
  } finally {
    isLoading.value = false;
    await nextTick();
    scrollToBottom();
  }
};

// 获取AI响应（使用SSE）
const fetchAIResponse = async (userMessage) => {
  try {
    // 确保使用正确的相对路径，通过Vite代理访问
    const url = '/api/agent/query/stream';
    // 从localStorage获取token
    const token = userStore.getToken;
    if (!token) {
      const authError = new Error('请先登录后再使用问答功能');
      authError.authRequired = true;
      throw authError;
    }
    // console.log('发送AI请求到:', url);
    // console.log('使用的token:', token);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        session_id: sessionId.value || undefined,
        query: userMessage
      })
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      if (response.status === 401) {
        userStore.clearAuthState();
        ElMessage.warning('登录已失效，请重新登录');
        router.push({
          path: '/login',
          query: { redirect: route.fullPath }
        });
        const authError = new Error('登录已失效，请重新登录');
        authError.authRequired = true;
        throw authError;
      }
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }
    
    // 处理SSE流
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let aiResponse = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (!data) continue;
        
        try {
          const json = JSON.parse(data);
          
          switch (json.type) {
            case 'step':
              break;
            case 'tool_call': {
              const curMsg = messages.value[messages.value.length - 1];
              if (curMsg && curMsg.role === 'assistant') {
                if (!curMsg.toolCalls) curMsg.toolCalls = [];
                curMsg.toolCalls.push({ tool: json.tool, args: json.args, result: null, status: 'running' });
              }
              break;
            }
            case 'tool_result': {
              const curMsg2 = messages.value[messages.value.length - 1];
              if (curMsg2 && curMsg2.role === 'assistant' && curMsg2.toolCalls) {
                const running = curMsg2.toolCalls.filter(tc => tc.status === 'running');
                if (running.length) {
                  running[0].result = json.result;
                  running[0].status = 'done';
                }
              }
              break;
            }
            case 'response':
              let content = '';

              if (typeof json.content === 'string') {
                content = json.content;
                const parsedObjectPayload = parseObjectFromJSONString(json.content);
                if (parsedObjectPayload) {
                  const extractedText = parsedObjectPayload.answer || parsedObjectPayload.response || parsedObjectPayload.content || '';
                  content = extractedText;
                  updateAssistantSources(parsedObjectPayload);
                  updateAssistantResultCard(parsedObjectPayload);
                }
              } else if (json.content && typeof json.content === 'object') {
                content = json.content.answer || json.content.response || json.content.content || '';
                updateAssistantSources(json.content);
                updateAssistantResultCard(json.content);
              }

              updateAssistantSources(json);
              updateAssistantResultCard(json);

              if (content) {
                aiResponse += content;
                
                // 逐字符显示打字机效果
                const displayContent = messages.value[messages.value.length - 1].content || '';
                const remainingContent = aiResponse.substring(displayContent.length);
                
                for (const char of remainingContent) {
                  messages.value[messages.value.length - 1].content += char;
                  await nextTick();
                  scrollToBottom();
                  // 控制打字速度，每个字符延迟8ms
                  await new Promise(resolve => setTimeout(resolve, 8));
                }
              }
              // 保存会话ID（不立即跳转，避免中断SSE）
              if (json.session_id && typeof json.session_id === 'string' && json.session_id.trim()) {
                sessionId.value = json.session_id;
              }
              break;
            case 'done':
              updateAssistantSources(json);
              updateAssistantResultCard(json);

              // 如果 steps 存在且 toolCalls 为空，从 steps 填充
              if (json.steps && json.steps.length) {
                const lastMsg = messages.value[messages.value.length - 1];
                if (lastMsg && lastMsg.role === 'assistant' && (!lastMsg.toolCalls || !lastMsg.toolCalls.length)) {
                  lastMsg.toolCalls = json.steps.map(s => ({
                    tool: s.tool,
                    args: s.tool_input,
                    result: s.tool_output,
                    status: 'done',
                  }));
                }
              }

              // 保存会话ID并在所有数据接收完成后跳转
              if (json.session_id && typeof json.session_id === 'string' && json.session_id.trim()) {
                sessionId.value = json.session_id;
                // 如果当前路由没有sessionId参数，跳转到带sessionId的路由
                if (!route.params.sessionId) {
                  router.push(`/aichat/${json.session_id}`);
                }
              }
              break;
            case 'sources':
            case 'source':
              updateAssistantSources(json);
              updateAssistantResultCard(json);
              break;
            case 'error':
              throw new Error(json.content || 'API错误');
              break;
          }
        } catch (e) {
          console.error('Error parsing SSE data:', e);
        }
      }
    }
  }
  
  // 如果没有收到任何内容
  const currentMessage = messages.value[messages.value.length - 1];
  if (!aiResponse && !currentMessage?.resultCard) {
    messages.value[messages.value.length - 1].content = '抱歉，我无法生成回复。请检查API设置或稍后再试。';
  }
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
};

// 跳转到会话管理页面
const goToSessions = () => {
  router.push('/sessions');
};

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// 监听消息变化，自动滚动
watch(messages, () => {
  nextTick(() => {
    scrollToBottom();
  });
}, { deep: true });

// 监听路由参数变化，重新加载会话历史
watch(() => route.params.sessionId, async (newSessionId) => {
  if (newSessionId) {
    try {
      const result = await sessionStore.getSession(newSessionId);
      if (result.success && sessionStore.currentSession) {
        loadSessionHistory(sessionStore.currentSession);
      } else {
        ElMessage.error('加载会话历史失败');
      }
    } catch (error) {
      console.error('加载会话历史失败:', error);
      ElMessage.error('加载会话历史失败');
    }
  }
}, { immediate: true });

// 组件挂载时检查是否有当前会话或路由参数中的会话ID
onMounted(async () => {
  // 检查路由参数中是否有sessionId
  const routeSessionId = route.params.sessionId;
  
  if (routeSessionId) {
    // 从路由参数获取会话ID，加载会话历史
    try {
      const result = await sessionStore.getSession(routeSessionId);
      if (result.success && sessionStore.currentSession) {
        loadSessionHistory(sessionStore.currentSession);
      } else {
        ElMessage.error('加载会话历史失败');
      }
    } catch (error) {
      console.error('加载会话历史失败:', error);
      ElMessage.error('加载会话历史失败');
    }
  } else if (sessionStore.currentSession) {
    // 从store中加载会话历史
    loadSessionHistory(sessionStore.currentSession);
  }
  
  scrollToBottom();
});

// 加载会话历史
const loadSessionHistory = (session) => {
  if (session.history && session.history.length > 0) {
    // 清空当前消息
    messages.value = [];
    // 加载历史消息
    session.history.forEach(([userMsg, aiMsg]) => {
      const parsedHistoryPayload = parseObjectFromJSONString(aiMsg);
      const historyCard = parsedHistoryPayload ? extractResultCard(parsedHistoryPayload) : null;
      const historySources = parsedHistoryPayload ? normalizeSources(parsedHistoryPayload.sources || parsedHistoryPayload.references || parsedHistoryPayload.docs) : [];
      const historyContent = parsedHistoryPayload
        ? (parsedHistoryPayload.answer || parsedHistoryPayload.response || parsedHistoryPayload.content || '')
        : aiMsg;

      messages.value.push({ role: 'user', content: userMsg });
      messages.value.push({
        role: 'assistant',
        content: historyContent,
        sources: historySources,
        resultCard: historyCard
      });
    });
    // 设置会话ID
    sessionId.value = session.session_id;
  }
};
</script>

<style scoped>
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

:deep(.el-page-header) {
  margin-bottom: 20px;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 20px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 85%;
}

.user-message {
  flex-direction: row-reverse;
  margin-left: auto;
}

.ai-message {
  margin-right: auto;
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  padding: 12px 16px;
  border-radius: 8px;
  word-break: break-word;
  line-height: 1.6;
}

.user-message .message-content {
  background-color: #ecf5ff;
  color: #303133;
  border: 1px solid #d9ecff;
}

.ai-message .message-content {
  background-color: #f5f7fa;
  color: #303133;
  border: 1px solid #e4e7ed;
}

.result-card {
  margin-top: 12px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #dcdfe6;
  background-color: #fff;
}

.result-card--answer {
  border-left: 4px solid #409eff;
}

.result-card--recommendation {
  border-left: 4px solid #67c23a;
}

.result-card--navigation {
  border-left: 4px solid #e6a23c;
}

.result-card--check {
  border-left: 4px solid #f56c6c;
}

.result-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.result-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.result-card-summary {
  margin: 8px 0 0;
  font-size: 13px;
  color: #606266;
}

.card-section {
  margin-top: 8px;
}

.card-meta {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.card-list {
  margin: 8px 0 0;
  padding-left: 18px;
}

.card-list li {
  margin-bottom: 4px;
  font-size: 13px;
  color: #606266;
}

.card-recommend-list,
.card-route-list,
.card-check-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-recommend-item,
.card-route-item,
.card-check-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 8px;
}

.card-recommend-head,
.card-route-head,
.card-check-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card-recommend-title {
  font-weight: 500;
  color: #303133;
}

.card-recommend-reason,
.card-check-detail,
.card-check-suggestion {
  margin: 6px 0 0;
  font-size: 12px;
  color: #606266;
}

.card-tags {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.card-route-meta {
  font-size: 12px;
  color: #909399;
}

.card-route-steps {
  margin: 6px 0 0;
  padding-left: 18px;
}

.card-route-steps li {
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
}

.tool-calls {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tool-call-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 12px;
  border: 1px solid #dcdfe6;
  background: #fafafa;
}

.tool-call-chip.tool-call--running {
  background: #ecf5ff;
  border-color: #a0cfff;
  animation: pulse-border 1.5s ease-in-out infinite;
}

.tool-call-chip.tool-call--done {
  background: #f0f9eb;
  border-color: #b3e19d;
}

.tool-call-icon {
  font-size: 12px;
}

.tool-call-label {
  color: #606266;
  font-family: monospace;
  font-size: 11px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@keyframes pulse-border {
  0%, 100% { border-color: #a0cfff; }
  50% { border-color: #409eff; }
}

.message-sources {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #dcdfe6;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-pill {
  border: 1px solid #d9ecff;
  border-radius: 999px;
  background: #ecf5ff;
  color: #337ecc;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  max-width: 240px;
  overflow: hidden;
  padding: 6px 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-pill:hover {
  background: #d9ecff;
  border-color: #a0cfff;
}

.source-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-detail-row {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 12px;
}

.source-detail-label {
  color: #909399;
  font-size: 13px;
}

.source-detail-value {
  color: #303133;
  font-size: 13px;
  word-break: break-word;
}

.source-snippet p {
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
  margin: 8px 0 0;
  padding: 10px;
}

.source-download-tip {
  color: #e6a23c;
  font-size: 12px;
}

.input-area {
  display: flex;
  flex-direction: column;
}

.file-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 20px 0 20px;
  background-color: #fff;
  border-radius: 8px 8px 0 0;
}

.input-container {
  display: flex;
  gap: 12px;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
}

.send-button {
  height: fit-content;
}

.schedule-timeline {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.schedule-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 6px;
  background: #f5f7fa;
  border-left: 3px solid #409eff;
  font-size: 13px;
}

.schedule-item--conflict {
  border-left-color: #f56c6c;
  background: #fef0f0;
}

.schedule-time {
  font-family: monospace;
  font-weight: 600;
  color: #303133;
  min-width: 90px;
}

.schedule-title {
  flex: 1;
  color: #303133;
  font-weight: 500;
}

.schedule-loc {
  color: #909399;
  font-size: 12px;
}

.schedule-week-grid {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  gap: 6px 12px;
  margin-top: 8px;
}

.schedule-week-item {
  display: contents;
  font-size: 12px;
}

.schedule-week-day {
  font-weight: 600;
  color: #409eff;
  padding: 2px 6px;
  background: #ecf5ff;
  border-radius: 4px;
  text-align: center;
  min-width: 36px;
}

.schedule-week-time {
  font-family: monospace;
  color: #606266;
}

.schedule-week-title {
  color: #303133;
  font-weight: 500;
}

.schedule-week-loc {
  color: #909399;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

/* Markdown 样式 */
.message-content pre {
  background-color: #f8f8f8;
  padding: 10px;
  border-radius: 5px;
  overflow-x: auto;
}

.message-content code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
}

.message-content img {
  max-width: 100%;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  padding: 5px;
}

.typing-indicator span {
  height: 8px;
  width: 8px;
  background-color: #999;
  border-radius: 50%;
  margin: 0 2px;
  display: inline-block;
  animation: bounce 1.5s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-5px);
  }
}

/* Markdown样式 */
:deep(pre) {
  background-color: #1e1e1e;
  padding: 15px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 10px 0;
  color: #d4d4d4;
}

:deep(pre code) {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
  color: #d4d4d4;
}

:deep(code) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

:deep(p) {
  margin: 8px 0;
  line-height: 1.5;
}

:deep(ul), :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

:deep(li) {
  margin: 4px 0;
  line-height: 1.5;
}

:deep(a) {
  color: #1989fa;
  text-decoration: none;
}

:deep(a:hover) {
  text-decoration: underline;
}

:deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
  margin: 12px 0 8px 0;
  font-weight: bold;
}

:deep(h1) {
  font-size: 1.5em;
}

:deep(h2) {
  font-size: 1.3em;
}

:deep(h3) {
  font-size: 1.1em;
}

:deep(blockquote) {
  border-left: 4px solid #1989fa;
  padding-left: 10px;
  margin: 10px 0;
  color: #666;
  background-color: #f9f9f9;
  padding: 8px 12px;
  border-radius: 0 4px 4px 0;
}

:deep(hr) {
  border: 0;
  border-top: 1px solid #eee;
  margin: 16px 0;
}

:deep(img) {
  max-width: 100%;
  border-radius: 4px;
  margin: 8px 0;
}

:deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
}

:deep(th), :deep(td) {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

:deep(th) {
  background-color: #f2f2f2;
  font-weight: bold;
}
</style>
