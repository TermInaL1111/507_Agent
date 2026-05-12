<template>
  <div class="agent-panel" :class="{ 'agent-panel--open': open }">
    <div class="agent-panel__toggle" @click="open = !open">
      <el-icon :size="20"><ChatDotRound /></el-icon>
      <span v-if="!open">AI 助手</span>
    </div>
    <div v-if="open" class="agent-panel__body">
      <div class="agent-panel__header">
        AI 助手
        <el-button link @click="open = false"><el-icon><Close /></el-icon></el-button>
      </div>
      <div class="agent-panel__messages" ref="panelMsgs">
        <div v-if="!messages.length" class="agent-panel__empty">
          💡 问我关于课表、导航、办事流程的问题
        </div>
        <div v-for="(msg, i) in messages" :key="i" :class="'panel-msg--' + msg.role">
          <span class="panel-msg-text">{{ msg.content }}</span>
        </div>
        <div v-if="loading" class="panel-msg--assistant">
          <span class="panel-msg-text typing">思考中...</span>
        </div>
      </div>
      <div class="agent-panel__input">
        <el-input v-model="input" size="small" placeholder="问 AI..." @keydown.enter="send" :disabled="loading" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue';
import { ChatDotRound, Close } from '@element-plus/icons-vue';
import { useUserStore } from '../store/user';

const props = defineProps({ context: { type: String, default: '' } });
const userStore = useUserStore();
const open = ref(false);
const input = ref('');
const loading = ref(false);
const messages = ref([]);
const panelMsgs = ref(null);

const send = async () => {
  const q = input.value.trim();
  if (!q || loading.value) return;
  input.value = '';
  loading.value = true;
  const ctx = props.context ? `[当前页面: ${props.context}] ` : '';
  messages.value.push({ role: 'user', content: q });

  try {
    const token = userStore.getToken;
    const resp = await fetch('/api/agent/query/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ query: ctx + q, session_id: '' }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let answer = '';
    messages.value.push({ role: 'assistant', content: '' });
    const last = () => messages.value[messages.value.length - 1];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const json = JSON.parse(line.slice(6));
            if (json.type === 'response' && typeof json.content === 'string') {
              answer += json.content;
              last().content = answer;
            }
          } catch {}
        }
      }
      await nextTick();
    }
  } catch (e) {
    messages.value.push({ role: 'assistant', content: `抱歉，请求失败：${e.message}` });
  }
  loading.value = false;
};
</script>

<style scoped>
.agent-panel { position: fixed; right: 0; top: 60px; z-index: 998; display: flex; flex-direction: column; align-items: flex-end; }
.agent-panel__toggle { background: #409eff; color: #fff; padding: 8px 16px; border-radius: 20px 0 0 20px; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 14px; box-shadow: -2px 0 8px rgba(64,158,255,.3); user-select: none; }
.agent-panel__toggle:hover { background: #337ecc; }
.agent-panel__body { width: 340px; height: calc(100vh - 100px); background: #fff; box-shadow: -2px 0 12px rgba(0,0,0,.08); display: flex; flex-direction: column; border-radius: 8px 0 0 8px; overflow: hidden; }
.agent-panel__header { padding: 10px 14px; border-bottom: 1px solid #e4e7ed; font-weight: 600; font-size: 14px; color: #303133; display: flex; justify-content: space-between; align-items: center; }
.agent-panel__messages { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 6px; }
.agent-panel__empty { color: #c0c4cc; font-size: 13px; text-align: center; margin-top: 40px; }
.agent-panel__input { padding: 8px 10px; border-top: 1px solid #e4e7ed; }
.panel-msg--user { text-align: right; align-self: flex-end; max-width: 85%; }
.panel-msg--user .panel-msg-text { background: #ecf5ff; color: #409eff; padding: 6px 10px; border-radius: 12px 12px 0 12px; font-size: 13px; display: inline-block; }
.panel-msg--assistant { align-self: flex-start; max-width: 90%; }
.panel-msg--assistant .panel-msg-text { background: #f5f7fa; color: #303133; padding: 6px 10px; border-radius: 12px 12px 12px 0; font-size: 13px; display: inline-block; white-space: pre-wrap; word-break: break-word; }
.typing { animation: blink 1s infinite; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: .3; } }
</style>
