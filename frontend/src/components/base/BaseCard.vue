<script setup></script>

<template>
  <div class="card">
    <slot />
  </div>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
}
</style>
