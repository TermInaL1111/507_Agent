<template>
  <div class="agent-fab" @click="openChat" title="AI 助手">
    <el-icon :size="24"><ChatDotRound /></el-icon>
  </div>
</template>

<script setup>
import { ChatDotRound } from '@element-plus/icons-vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const openChat = () => router.push('/aichat');
</script>

<style scoped>
.agent-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(64, 158, 255, .4);
  z-index: 999;
  transition: transform .2s, box-shadow .2s;
}
.agent-fab:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 20px rgba(64, 158, 255, .6);
}
</style>
