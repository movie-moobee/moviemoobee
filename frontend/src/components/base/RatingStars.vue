<script setup>
// 0.5 단위 별점 입력/표시 (F-WAT-02 규칙). 온보딩·상세·지도 공용 재사용.
import { ref, computed } from "vue";

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  readonly: { type: Boolean, default: false },
  size: { type: Number, default: 32 },
});
const emit = defineEmits(["update:modelValue"]);

const hover = ref(0);
const display = computed(() => hover.value || props.modelValue);

// 별 i(1~5)의 채움 비율: 0 / 50 / 100
function pct(i) {
  const v = display.value - (i - 1);
  if (v >= 1) return 100;
  if (v >= 0.5) return 50;
  return 0;
}
function set(i, half) {
  if (props.readonly) return;
  emit("update:modelValue", half ? i - 0.5 : i);
}
function onHover(i, half) {
  if (!props.readonly) hover.value = half ? i - 0.5 : i;
}
</script>

<template>
  <div
    class="stars"
    :class="{ readonly }"
    @mouseleave="hover = 0"
  >
    <span
      v-for="i in 5"
      :key="i"
      class="star"
      :style="{ fontSize: size + 'px' }"
    >
      <span class="star__bg">★</span>
      <span
        class="star__fg"
        :style="{ width: pct(i) + '%' }"
      >★</span>
      <template v-if="!readonly">
        <button
          class="zone zone--left"
          type="button"
          aria-label="half"
          @mouseenter="onHover(i, true)"
          @click="set(i, true)"
        />
        <button
          class="zone zone--right"
          type="button"
          aria-label="full"
          @mouseenter="onHover(i, false)"
          @click="set(i, false)"
        />
      </template>
    </span>
  </div>
</template>

<style scoped>
.stars {
  display: inline-flex;
  gap: 4px;
  line-height: 1;
}
.star {
  position: relative;
  display: inline-block;
}
.star__bg {
  color: #d8dadf;
}
.star__fg {
  position: absolute;
  top: 0;
  left: 0;
  overflow: hidden;
  white-space: nowrap;
  color: #f0a020;
}
.zone {
  position: absolute;
  top: 0;
  width: 50%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.zone--left {
  left: 0;
}
.zone--right {
  right: 0;
}
.stars.readonly .star {
  pointer-events: none;
}
</style>
