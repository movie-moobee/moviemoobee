<script setup>
defineProps({
  variant: { type: String, default: 'primary' }, // primary | secondary | danger
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
})
</script>

<template>
  <button :type="type" :disabled="disabled" :class="['btn', `btn--${variant}`]">
    <slot />
  </button>
</template>

<style scoped>
.btn {
  font-family: var(--font);
  font-size: 14px;
  padding: 10px 18px;
  border-radius: var(--radius-sm);
  border: 0.5px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
}
.btn:disabled { opacity: 0.45; cursor: not-allowed; }

.btn--primary { background: var(--gold); color: #1A1206; }
.btn--primary:hover:not(:disabled) { filter: brightness(1.08); }

.btn--secondary { background: transparent; color: var(--text); border-color: var(--border-hover); }
.btn--secondary:hover:not(:disabled) { background: var(--surface-2); }

.btn--danger { background: transparent; color: var(--danger); border-color: var(--danger); }
.btn--danger:hover:not(:disabled) { background: rgba(226,75,74,0.1); }
</style>
