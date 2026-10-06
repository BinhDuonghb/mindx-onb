<template>
  <div class="minimal-card-wrapper">
    <div class="minimal-card-simple">
      <div class="card-header-minimal" v-if="title">
        <h3 class="card-title-minimal">{{ title }}</h3>
      </div>
      <div class="card-content-minimal">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title?: string;
}

defineProps<Props>();
</script>

<style scoped>
.minimal-card-wrapper {
  margin: 1rem 0;
}

.minimal-card-simple {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
  transition: border-color 0.2s ease;
}

.minimal-card-simple:hover {
  border-color: #cbd5e1;
}

.card-header-minimal {
  margin-bottom: 0.75rem;
}

.card-title-minimal {
  margin: 0;
  font-family: 'Inter', sans-serif;
  font-weight: 500;
  font-size: 1.125rem;
  color: #334155;
}

.card-content-minimal {
  font-family: 'Inter', sans-serif;
  font-weight: 400;
  line-height: 1.6;
  color: #64748b;
}

.card-content-minimal :deep(p) {
  margin: 0 0 0.5rem 0;
}

.card-content-minimal :deep(p:last-child) {
  margin-bottom: 0;
}
</style>
