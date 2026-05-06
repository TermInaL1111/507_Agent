<template>
  <div class="chat-shell">
    <aside class="session-panel" :class="{ collapsed: isSessionPanelCollapsed }">
      <div class="session-panel-top">
        <el-button text class="collapse-btn" @click="toggleSessionPanel">
          <el-icon><component :is="isSessionPanelCollapsed ? Expand : Fold" /></el-icon>
        </el-button>
        <template v-if="!isSessionPanelCollapsed">
          <el-button type="primary" plain class="new-session-btn" @click="startNewSession">
            <el-icon><Plus /></el-icon>
            新会话
          </el-button>
          <el-button text :loading="sessionRefreshing" @click="refreshSessionList(true)">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </template>
      </div>

      <div v-if="!isSessionPanelCollapsed" class="session-panel-content">
        <div v-if="sessionStore.isLoading && !sessionStore.sessions.length" class="session-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载会话中...</span>
        </div>

        <el-empty v-else-if="!sessionStore.sessions.length" description="暂无会话" :image-size="72" />

        <div v-else class="session-list">
          <div
            v-for="session in sessionStore.sessions"
            :key="session.session_id"
            class="session-item"
            :class="{ active: isCurrentSession(session.session_id) }"
            @click="openSession(session.session_id)"
          >
            <div class="session-item-main">
              <div class="session-item-title">{{ session.title || '新会话' }}</div>
              <div class="session-item-time">{{ formatSessionTime(session.updated_at || session.created_at) }}</div>
            </div>
            <el-button text type="danger" class="session-delete-btn" @click.stop="removeSession(session.session_id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </aside>

    <div class="ai-chat-container">
      <div class="chat-header">
        <div class="chat-header-left">
          <el-button text class="mobile-toggle" @click="toggleSessionPanel">
            <el-icon><Menu /></el-icon>
          </el-button>
          <span class="page-title">AI智能问答</span>
        </div>
      </div>

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

              <div v-if="message.role === 'assistant' && message.sources?.length" class="message-sources">
                <div class="sources-title">引用来源</div>
                <ul class="sources-list">
                  <li
                    v-for="(source, sourceIndex) in message.sources"
                    :key="`${index}-${sourceIndex}`"
                    class="source-item"
                  >
                    <div class="source-head">
                      <span class="source-index">[{{ sourceIndex + 1 }}]</span>
                      <span class="source-title">{{ source.title || `来源${sourceIndex + 1}` }}</span>
                    </div>
                    <p v-if="source.content" class="source-content">{{ source.content }}</p>
                    <a
                      v-if="source.url"
                      :href="source.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="source-link"
                    >
                      {{ source.url }}
                    </a>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div class="input-container">
          <el-dropdown trigger="click" @command="handleFeatureCommand">
            <el-button plain class="feature-button">
              <el-icon><Grid /></el-icon>
              功能菜单
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="item in featureMenuItems" :key="item.path" :command="item.path">
                  <el-icon><component :is="item.icon" /></el-icon>
                  <span>{{ item.label }}</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-input
            v-model="userInput"
            type="textarea"
            :rows="3"
            placeholder="请输入问题..."
            class="chat-input"
            resize="none"
            @keydown.enter.prevent="handleEnter"
          />
          <el-button
            type="primary"
            size="large"
            class="send-button"
            :disabled="isLoading || !userInput.trim()"
            @click="sendMessage"
          >
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  User,
  ChatDotRound,
  Promotion,
  Plus,
  Refresh,
  Delete,
  Loading,
  Menu,
  Fold,
  Expand,
  Grid,
  Calendar,
  Reading,
  Notebook,
  Location,
  Document,
  Collection,
  UserFilled,
  Setting
} from '@element-plus/icons-vue';
import { marked } from 'marked';
import { markedHighlight } from 'marked-highlight';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import 'highlight.js/styles/monokai-sublime.css';
import 'highlight.js/lib/common';
import { useUserStore } from '../store/user';
import { useSessionStore } from '../store/session';

// 聊天消息
const messages = ref([
  { role: 'assistant', content: '你好！我是AI助手，有什么可以帮助你的吗？', sources: [], resultCard: null }
]);
const userInput = ref('');
const messagesContainer = ref(null);
const isLoading = ref(false);
const sessionId = ref('');
const isSessionPanelCollapsed = ref(false);
const sessionRefreshing = ref(false);

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const sessionStore = useSessionStore();

const featureMenuItems = [
  { path: '/schedule', label: '课表服务', icon: Calendar },
  { path: '/course-plan', label: '课程规划', icon: Reading },
  { path: '/course-recommend', label: '选课建议', icon: Notebook },
  { path: '/campus-map', label: '校园导航', icon: Location },
  { path: '/document-assistant', label: '文书辅助', icon: Document },
  { path: '/knowledge-manage', label: '知识库管理', icon: Collection },
  { path: '/profile', label: '个人中心', icon: UserFilled },
  { path: '/settings', label: '系统设置', icon: Setting }
];

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

const resetToWelcomeMessage = () => {
  messages.value = [
    { role: 'assistant', content: '你好！我是AI助手，有什么可以帮助你的吗？', sources: [], resultCard: null }
  ];
};

const toggleSessionPanel = () => {
  isSessionPanelCollapsed.value = !isSessionPanelCollapsed.value;
};

const getCurrentUserId = () => {
  if (!userStore.userInfo) return '';
  return userStore.userInfo.uuid || userStore.userInfo.id || userStore.userInfo.user_id || '';
};

const loadSessionList = async (showSuccess = false) => {
  if (!userStore.getLoginStatus) return;

  if (!userStore.userInfo) {
    const profileResult = await userStore.getUserInfoDetail();
    if (!profileResult.success) {
      ElMessage.error(profileResult.message || '获取用户信息失败');
      return;
    }
  }

  const userId = getCurrentUserId();
  if (!userId) {
    ElMessage.error('获取用户ID失败，请重新登录后重试');
    return;
  }

  const result = await sessionStore.getUserSessions(userId);
  if (result.success) {
    if (showSuccess) {
      ElMessage.success('会话列表已刷新');
    }
  } else {
    ElMessage.error(result.message || '获取会话列表失败');
  }
};

const refreshSessionList = async (showSuccess = false) => {
  sessionRefreshing.value = true;
  try {
    await loadSessionList(showSuccess);
  } finally {
    sessionRefreshing.value = false;
  }
};

const formatSessionTime = (timeString) => {
  if (!timeString) return '';
  try {
    return new Date(timeString).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return timeString;
  }
};

const isCurrentSession = (id) => {
  return sessionId.value === id || route.params.sessionId === id;
};

const openSession = (id) => {
  router.push(`/aichat/${id}`);
};

const startNewSession = () => {
  sessionId.value = '';
  sessionStore.setCurrentSession(null);
  resetToWelcomeMessage();
  router.push('/aichat');
};

const removeSession = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该会话吗？删除后无法恢复。', '删除会话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    });
  } catch {
    return;
  }

  const result = await sessionStore.deleteSession(id);
  if (!result.success) {
    ElMessage.error(result.message || '删除会话失败');
    return;
  }

  ElMessage.success('会话已删除');

  if (isCurrentSession(id)) {
    startNewSession();
  }

  await loadSessionList(false);
};

const handleFeatureCommand = (path) => {
  if (!path || typeof path !== 'string') return;
  router.push(path);
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
    check: '检查型'
  };

  return labelMap[type] || '结果型';
};

const getResultCardTagType = (type) => {
  const tagMap = {
    answer: 'primary',
    recommendation: 'success',
    navigation: 'warning',
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
      routes: routeItems
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
          title: item.title || item.name || `来源${index + 1}`,
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

// 处理回车键发送
const handleEnter = (e) => {
  if (!e.shiftKey) {
    sendMessage();
  }
};

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return;
  
  // 检查是否登录
  if (!userStore.getLoginStatus) {
    ElMessage.warning('请先登录');
    return;
  }
  
  // 添加用户消息
  const userMessage = userInput.value.trim();
  messages.value.push({ role: 'user', content: userMessage });
  userInput.value = '';
  
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
    const token = localStorage.getItem('jwt_token') || userStore.token;
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

              // 保存会话ID并在所有数据接收完成后跳转
              if (json.session_id && typeof json.session_id === 'string' && json.session_id.trim()) {
                sessionId.value = json.session_id;
                // 如果当前路由没有sessionId参数，跳转到带sessionId的路由
                if (!route.params.sessionId) {
                  router.push(`/aichat/${json.session_id}`);
                }
              }
              await loadSessionList(false);
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
  } else {
    sessionId.value = '';
    sessionStore.setCurrentSession(null);
    resetToWelcomeMessage();
  }
}, { immediate: true });

// 组件挂载时检查是否有当前会话或路由参数中的会话ID
onMounted(async () => {
  await loadSessionList(false);

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
  } else {
    resetToWelcomeMessage();
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
.chat-shell {
  display: flex;
  height: 100%;
  min-height: 0;
  background: #f3f4f6;
}

.session-panel {
  width: 280px;
  height: 100%;
  background: #101826;
  border-right: 1px solid #1f2d3d;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
  flex-shrink: 0;
}

.session-panel.collapsed {
  width: 64px;
}

.session-panel-top {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid #1f2d3d;
}

.collapse-btn {
  color: #d7deea;
}

.new-session-btn {
  flex: 1;
}

.session-panel-content {
  flex: 1;
  overflow: hidden;
  padding: 10px;
}

.session-loading {
  color: #d7deea;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 8px;
}

.session-list {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  border: 1px solid transparent;
}

.session-item:hover {
  background: rgba(64, 158, 255, 0.15);
}

.session-item.active {
  background: rgba(64, 158, 255, 0.2);
  border-color: rgba(64, 158, 255, 0.45);
}

.session-item-main {
  flex: 1;
  min-width: 0;
}

.session-item-title {
  color: #f3f6fd;
  font-size: 13px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item-time {
  margin-top: 5px;
  color: #9aa8bf;
  font-size: 12px;
}

.session-delete-btn {
  opacity: 0;
}

.session-item:hover .session-delete-btn,
.session-item.active .session-delete-btn {
  opacity: 1;
}

.ai-chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  padding: 16px;
  box-sizing: border-box;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-toggle {
  display: none;
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
  border-radius: 12px;
  margin-bottom: 12px;
  border: 1px solid #e9eef5;
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

.message-sources {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #dcdfe6;
}

.sources-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.sources-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-item {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 8px 10px;
}

.source-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.source-index {
  color: #409eff;
  font-weight: 600;
}

.source-title {
  color: #303133;
  font-size: 13px;
  font-weight: 500;
}

.source-content {
  margin: 6px 0 0;
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
}

.source-link {
  display: inline-block;
  margin-top: 6px;
  font-size: 12px;
  color: #409eff;
  word-break: break-all;
}

.input-container {
  display: flex;
  gap: 12px;
  padding: 14px;
  background-color: #fff;
  border-radius: 12px;
  align-items: flex-end;
  border: 1px solid #e9eef5;
}

.feature-button {
  height: 40px;
  align-self: flex-end;
}

.chat-input {
  flex: 1;
}

.send-button {
  height: 40px;
}

@media (max-width: 992px) {
  .chat-shell {
    position: relative;
  }

  .session-panel {
    position: absolute;
    z-index: 20;
    left: 0;
    top: 0;
    height: 100%;
    box-shadow: 2px 0 12px rgba(0, 0, 0, 0.2);
  }

  .session-panel.collapsed {
    width: 280px;
    transform: translateX(-100%);
  }

  .ai-chat-container {
    padding: 10px;
  }

  .mobile-toggle {
    display: inline-flex;
  }

  .messages-container {
    padding: 12px;
  }

  .message {
    max-width: 100%;
  }

  .input-container {
    gap: 8px;
    padding: 10px;
    flex-wrap: wrap;
  }

  .feature-button {
    order: 1;
  }

  .chat-input {
    order: 2;
    width: 100%;
    flex-basis: 100%;
  }

  .send-button {
    order: 3;
    margin-left: auto;
  }
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