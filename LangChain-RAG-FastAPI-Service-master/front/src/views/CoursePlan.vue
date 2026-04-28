<template>
  <div class="module-page page-container">
    <el-card shadow="never" class="module-card">
      <template #header>
        <div class="card-header">
          <span>课程规划（占位页）</span>
          <el-tag type="warning">待后端联调</el-tag>
        </div>
      </template>

      <el-empty description="课程规划功能开发中" />

      <el-alert
        title="计划支持：培养方案进度、学期课程建议"
        type="info"
        :closable="false"
        show-icon
      />
    </el-card>
  </div>
</template>

<script setup>
</script>

<style scoped>
.module-page {
  padding: 20px;
}

.module-card {
  min-height: 280px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
