# Agent-First UX — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every page agent-interactive: fix map markers, embed Agent chat on schedule/map pages, make tool outputs render as structured cards.

**Architecture:** Each page gets an embedded Agent chat sidebar (reusable `AgentPanel.vue` component). Map markers trigger Agent queries via this panel. Agent tool outputs return JSON result_cards (schedule/navigation/recommendation) that render as interactive widgets.

**Tech Stack:** Vue 3 + Element Plus + AMap JSAPI v2 + DeepSeek V3 + LangChain

---

### Task 1: Fix campus map markers — click to show info + trigger Agent

**Files:**
- Modify: `front/src/views/CampusMap.vue`

**Problem:** `renderMarkers()` creates markers with `marker.on('click', () => selectLocation(location))` but `selectLocation` calls `map.setZoomAndCenter` and `openInfoWindow`. The issue is likely the AMap SDK not being fully loaded or the marker events not firing because markers are cleared improperly.

**Root cause analysis:** The `clearMarkers()` function uses `map.clearMap()` which removes all overlays including markers. But if the AMap instance is recreated, old markers become orphaned. Also, the `selectLocation` depends on `isRenderableLocation(location)` which checks longitude/latitude are finite numbers.

- [ ] **Step 1: Verify marker click event binding**

Read current `selectLocation` and `openInfoWindow` implementations (lines 196-200). The issue is that `marker.on('click', ...)` may fail if AMap SDK isn't loaded. Add a guard.

Update `/root/zhsx/front/src/views/CampusMap.vue` `renderMarkers()` (line 159):

```js
const renderMarkers = () => {
  if (!map || !AMapInstance) return;
  clearMarkers();

  markers = filteredLocations.value
    .filter(isRenderableLocation)
    .map((location) => {
      const marker = new AMapInstance.Marker({
        position: [location.longitude, location.latitude],
        title: location.name,
        anchor: 'bottom-center',
        clickable: true,
      });
      marker.on('click', (e) => {
        e.stopPropagation?.();
        selectLocation(location);
      });
      marker.setMap(map);
      return marker;
    });

  if (markers.length) {
    if (activeCampus.value !== 'all') {
      const c = campusCenters[activeCampus.value];
      map.setZoomAndCenter(c.zoom, [c.lng, c.lat]);
    } else {
      map.setFitView(markers, false, [80, 80, 80, 80]);
    }
  }
};
```

Key fix: `marker.setMap(map)` explicitly assigns each marker to the map (more reliable than `map.add(markers)`).

- [ ] **Step 2: Fix clearMarkers to properly remove**

Update clearMarkers (create if needed):

```js
const clearMarkers = () => {
  markers.forEach(m => m.setMap(null));
  markers = [];
  if (infoWindow) infoWindow.close();
};
```

- [ ] **Step 3: Commit**

```bash
cd /root/zhsx && git add front/src/views/CampusMap.vue && git commit -m "fix: map markers clickable with explicit setMap + proper cleanup"
```

---

### Task 2: Create reusable AgentPanel component

**Files:**
- Create: `front/src/components/AgentPanel.vue`

A compact Agent chat panel that can be embedded on any page. Shows the same chat UI but in a smaller sidebar format.

- [ ] **Step 1: Write AgentPanel component**

Write `/root/zhsx/front/src/components/AgentPanel.vue`:

```vue
<template>
  <div class="agent-panel" :class="{ 'agent-panel--open': open }">
    <div class="agent-panel__toggle" @click="open = !open">
      <el-icon :size="20"><ChatDotRound /></el-icon>
      <span v-if="!open">AI 助手</span>
    </div>
    <div v-if="open" class="agent-panel__body">
      <div class="agent-panel__messages" ref="panelMsgs">
        <div v-if="!messages.length" class="agent-panel__empty">
          问我关于课表、导航、办事流程的问题
        </div>
        <div v-for="(msg, i) in messages" :key="i" :class="'panel-msg--' + msg.role">
          {{ msg.content }}
        </div>
        <div v-if="loading" class="panel-msg--assistant">思考中...</div>
      </div>
      <div class="agent-panel__input">
        <el-input v-model="input" size="small" placeholder="问 AI..." @keydown.enter="send" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue';
import { ChatDotRound } from '@element-plus/icons-vue';
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

  const token = userStore.getToken;
  const resp = await fetch('/api/agent/query/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ query: ctx + q, session_id: '' }),
  });
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
          } else if (json.type === 'done') {
            // done
          }
        } catch {}
      }
    }
    await nextTick();
  }
  loading.value = false;
};
</script>

<style scoped>
.agent-panel { position: fixed; right: 0; top: 60px; z-index: 998; display: flex; flex-direction: column; align-items: flex-end; }
.agent-panel__toggle { background: #409eff; color: #fff; padding: 8px 16px; border-radius: 20px 0 0 20px; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 14px; }
.agent-panel__body { width: 320px; height: calc(100vh - 120px); background: #fff; box-shadow: -2px 0 12px rgba(0,0,0,.1); display: flex; flex-direction: column; }
.agent-panel__messages { flex: 1; overflow-y: auto; padding: 12px; }
.agent-panel__empty { color: #c0c4cc; font-size: 13px; text-align: center; margin-top: 40px; }
.agent-panel__input { padding: 8px; border-top: 1px solid #e4e7ed; }
.panel-msg--user { text-align: right; color: #409eff; margin: 4px 0; font-size: 13px; }
.panel-msg--assistant { color: #303133; margin: 4px 0; font-size: 13px; white-space: pre-wrap; }
</style>
```

- [ ] **Step 2: Add AgentPanel to Schedule page**

In `/root/zhsx/front/src/views/Schedule.vue`, add import and component:

```js
import AgentPanel from '../components/AgentPanel.vue';
```

Add to template (before closing `</template>`):

```html
<AgentPanel context="课表日程页面" />
```

- [ ] **Step 3: Add AgentPanel to CampusMap page**

In `/root/zhsx/front/src/views/CampusMap.vue`, add import and component (same pattern).

- [ ] **Step 4: Commit**

```bash
cd /root/zhsx && git add front/src/components/AgentPanel.vue front/src/views/Schedule.vue front/src/views/CampusMap.vue && git commit -m "feat: AgentPanel — embedded Agent chat on Schedule + CampusMap pages"
```

---

### Task 3: Agent tool outputs return structured result_cards

**Files:**
- Modify: `backend/app/agent/agent_tools.py`
- Modify: `front/src/views/AIChat.vue`

- [ ] **Step 1: Update get_schedule_today to return schedule card JSON**

Already partially done. Verify the `<!--CARD:...-->` marker is parsed by frontend.

- [ ] **Step 2: Frontend — parse CARD markers in SSE response content**

Add card extraction in AIChat.vue SSE handler for `response` type:

In the `case 'response'` handler, after setting the content, check if it contains `<!--CARD:...-->` and extract:

```js
case 'response': {
  const curMsg = messages.value[messages.value.length - 1];
  if (curMsg && curMsg.role === 'assistant') {
    curMsg.content += (typeof json.content === 'string' ? json.content : '');
    // Extract embedded card
    if (typeof json.content === 'string') {
      const cardMatch = json.content.match(/<!--CARD:(.*?)-->/);
      if (cardMatch) {
        try {
          const card = JSON.parse(cardMatch[1]);
          curMsg.resultCard = normalizeResultCard(card);
          curMsg.content = curMsg.content.replace(/<!--CARD:.*?-->/, '');
        } catch {}
      }
    }
  }
  break;
}
```

- [ ] **Step 3: Commit**

```bash
cd /root/zhsx && git add backend/app/agent/agent_tools.py front/src/views/AIChat.vue && git commit -m "feat: Agent tools return structured result_cards — schedule cards render in chat"
```

---

### Task 4: Build, deploy, verify, push

- [ ] **Step 1: Build both images**

```bash
cd /root/zhsx && docker-compose build backend frontend 2>&1 | tail -5
```

- [ ] **Step 2: Deploy**

```bash
docker rm -f 507-agent-backend 507-agent-frontend 2>/dev/null
# See .env.example for required environment variables. Deploy with docker-compose or source .env first.
docker rm -f 507-agent-backend 507-agent-frontend 2>/dev/null
docker run -d --name 507-agent-backend --network zhsx_default --env-file .env -v 507_agent_backend_data:/app/data -v "./Training Program:/Training Program:ro" -v ./documents:/app/documents:ro zhsx_backend:latest
docker run -d --name 507-agent-frontend --network zhsx_default -p 80:80 zhsx_frontend:latest
docker run -d --name 507-agent-frontend --network zhsx_default -p 80:80 zhsx_frontend:latest
```

- [ ] **Step 3: Verify**

```bash
sleep 15 && docker ps --filter name=507-agent --format "{{.Names}} {{.Status}}" && docker logs 507-agent-backend --tail 2
```

- [ ] **Step 4: Push**

```bash
cd /root/zhsx && git push origin agent-centric
```
