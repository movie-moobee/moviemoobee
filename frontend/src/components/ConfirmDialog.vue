<script setup>
// 공용 확인 다이얼로그 (계정 삭제·시청기록 삭제·리뷰 삭제 등 위험 액션 2차 확인).
defineProps({
  title: { type: String, required: true },
  message: { type: String, default: "" },
  confirmLabel: { type: String, default: "확인" },
  cancelLabel: { type: String, default: "취소" },
  danger: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
});
const emit = defineEmits(["confirm", "cancel"]);
</script>

<template>
  <div
    class="overlay"
    @click.self="emit('cancel')"
  >
    <div class="dialog">
      <h3 class="dialog__title">
        {{ title }}
      </h3>
      <p
        v-if="message"
        class="dialog__msg"
      >
        {{ message }}
      </p>
      <div class="dialog__actions">
        <button
          class="btn"
          :class="danger ? 'btn--danger' : 'btn--primary'"
          type="button"
          :disabled="busy"
          @click="emit('confirm')"
        >
          {{ busy ? "처리 중…" : confirmLabel }}
        </button>
        <button
          class="btn btn--ghost"
          type="button"
          :disabled="busy"
          @click="emit('cancel')"
        >
          {{ cancelLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 20px;
}
.dialog {
  width: 100%;
  max-width: 360px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
}
.dialog__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 8px;
}
.dialog__msg {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
  margin: 0 0 20px;
}
.dialog__actions {
  display: flex;
  gap: 8px;
}
.btn {
  flex: 1;
  padding: 11px;
  border: 0;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn--primary {
  background: var(--gold);
  color: #1a1206;
}
.btn--danger {
  background: var(--danger);
  color: #fff;
}
.btn--ghost {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border-hover);
  font-weight: 400;
}
</style>
