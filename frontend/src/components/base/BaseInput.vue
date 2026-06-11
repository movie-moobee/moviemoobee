<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <label class="field">
    <span v-if="label" class="field__label">{{ label }}</span>
    <input
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      class="field__input"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  </label>
</template>

<style scoped>
.field { display: flex; flex-direction: column; gap: 6px; }
.field__label { font-size: 13px; color: var(--text-muted); }
.field__input {
  font-family: var(--font);
  font-size: 14px;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 0.5px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  transition: border-color 0.15s;
}
.field__input::placeholder { color: var(--text-faint); }
.field__input:focus { outline: none; border-color: var(--gold); }
</style>
