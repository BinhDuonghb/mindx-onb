<template>
  <div class="branded-card shadow-custom">
    <div class="card-header">
      <img src="/logo.svg" alt="MindX Logo" class="logo" />
      <h3 class="card-title">{{ title }}</h3>
    </div>
    <div class="card-content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string;
}

defineProps<Props>();
</script>

<style scoped>
.branded-card {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(139, 92, 246, 0.05));
  border: 1px solid var(--slidev-color-border);
  border-radius: 12px;
  padding: 1.5rem;
  margin: 1rem 0;
  transition: all 0.3s ease;
}

.branded-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 35px rgba(59, 130, 246, 0.15);
}

.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
}

.card-title {
  margin: 0 0 0 1rem;
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  color: var(--slidev-color-primary);
}

.card-content {
  font-family: 'Nunito Sans', sans-serif;
  line-height: 1.6;
  color: var(--slidev-color-text);
}
</style>
