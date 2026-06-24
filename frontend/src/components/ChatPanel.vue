<script setup>
// 재사용 LLM 챗 패널 (5.4, 와이어프레임 13, 김호준) — 같이 볼 영화 / 범용 추천 공용.
// streamFn(history, onDelta)으로 SSE 스트리밍을 부모가 주입(엔드포인트만 다름).
import { nextTick, ref } from "vue";

const props = defineProps({
  title: { type: String, default: "무비무비 AI" },
  subtitle: { type: String, default: "" },
  intro: { type: String, default: "" },        // 첫 안내 말풍선(서버 이력엔 미포함)
  placeholder: { type: String, default: "메시지 입력…" },
  streamFn: { type: Function, required: true }, // (history:[{role,content}], onDelta) => Promise
  // 봇 답변 텍스트에서 추천작을 찾아 {id,title,...}|null 반환 → 있으면 [지도에 표시하기] 노출(5.4)
  resolveFn: { type: Function, default: null },
  mappedIds: { type: Array, default: () => [] },   // 현재 지도에 표시된 추천작 id(버튼 on/off 표시)
});
const emit = defineEmits(["show-on-map"]);

const messages = ref(props.intro ? [{ role: "assistant", content: props.intro, intro: true }] : []);
const input = ref("");
const busy = ref(false);
const error = ref("");
const scroller = ref(null);

async function scrollDown() {
  await nextTick();
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight;
}

async function send() {
  const text = input.value.trim();
  if (!text || busy.value) return;
  input.value = "";
  error.value = "";
  messages.value.push({ role: "user", content: text });
  messages.value.push({ role: "assistant", content: "" });
  const assistant = messages.value[messages.value.length - 1];   // 반응형 객체 참조
  busy.value = true;
  await scrollDown();
  try {
    // 서버에 보낼 이력: intro(안내)·빈 응답 제외, role/content만.
    const history = messages.value
      .filter((m) => !m.intro && m.content)
      .map((m) => ({ role: m.role, content: m.content }));
    await props.streamFn(history, (d) => { assistant.content += d; scrollDown(); });
    if (!assistant.content) assistant.content = "(빈 응답)";
    // 답변 완성 후 추천작 매칭(여러 편 가능) → 말풍선 아래 영화별 [지도에 표시] 칩 노출
    if (props.resolveFn) assistant.movies = props.resolveFn(assistant.content);
  } catch {
    error.value = "응답을 받지 못했어요. 잠시 후 다시 시도해줘.";
    if (!assistant.content) messages.value.pop();   // 빈 응답 말풍선 제거
  } finally {
    busy.value = false;
    scrollDown();
  }
}
</script>

<template>
  <div class="chat">
    <header class="chat__head">
      <div class="chat__bot">
        🤖
      </div>
      <div class="chat__head-meta">
        <div class="chat__title">
          {{ title }}
        </div>
        <div
          v-if="subtitle"
          class="chat__sub"
        >
          {{ subtitle }}
        </div>
      </div>
    </header>

    <div
      ref="scroller"
      class="chat__msgs"
    >
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="row"
        :class="m.role === 'user' ? 'row--me' : 'row--bot'"
      >
        <div
          class="bubble"
          :class="m.role === 'user' ? 'bubble--me' : 'bubble--bot'"
        >
          {{ m.content }}<span
            v-if="m.role === 'assistant' && busy && i === messages.length - 1 && !m.content"
            class="dots"
          >…</span>
        </div>
        <div
          v-if="m.movies && m.movies.length"
          class="mapbtns"
        >
          <span class="mapbtns__label">지도에 표시</span>
          <button
            v-for="mv in m.movies"
            :key="mv.id"
            class="mapbtn"
            :class="{ 'mapbtn--on': mappedIds.includes(mv.id) }"
            type="button"
            @click="emit('show-on-map', mv)"
          >
            <span class="mapbtn__pin">{{ mappedIds.includes(mv.id) ? "✓" : "📍" }}</span> {{ mv.title }}
          </button>
        </div>
      </div>
      <p
        v-if="error"
        class="chat__error"
      >
        {{ error }}
      </p>
    </div>

    <form
      class="chat__input"
      @submit.prevent="send"
    >
      <input
        v-model="input"
        :placeholder="placeholder"
        :disabled="busy"
        type="text"
      >
      <button
        type="submit"
        :disabled="busy || !input.trim()"
      >
        전송
      </button>
    </form>
  </div>
</template>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 430px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--surface, #12141c);
}
.chat__head {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-alt, #1a1d27);
}
.chat__bot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2a2f3e;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex: none;
}
.chat__title {
  font-size: 13px;
  font-weight: 700;
}
.chat__sub {
  font-size: 10.5px;
  color: var(--text-muted);
  margin-top: 1px;
}
.chat__msgs {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.row--me {
  align-items: flex-end;
}
.row--bot {
  align-items: flex-start;
}
.bubble {
  max-width: 88%;
  padding: 9px 11px;
  font-size: 12.5px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
.mapbtns {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  max-width: 88%;
}
.mapbtns__label {
  font-size: 11px;
  color: var(--text-muted);
  margin-right: 1px;
}
.mapbtn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  font-family: var(--font);
  font-size: 12px;
  font-weight: 600;
  color: var(--gold, #e8c252);
  background: rgba(232, 194, 82, 0.1);
  border: 1px solid rgba(232, 194, 82, 0.45);
  border-radius: 999px;
  cursor: pointer;
}
.mapbtn:hover {
  background: rgba(232, 194, 82, 0.18);
}
.mapbtn__pin {
  font-size: 11px;
}
/* 표시된 상태: 마커 색(보라)과 맞춰 채움 + 켜질 때 팝 애니메이션 */
.mapbtn--on {
  color: #cbb6ff;
  background: rgba(168, 132, 255, 0.16);
  border-color: rgba(168, 132, 255, 0.55);
  animation: mapbtn-pop 0.32s ease;
}
.mapbtn--on:hover {
  background: rgba(168, 132, 255, 0.24);
}
@keyframes mapbtn-pop {
  0% { transform: scale(0.9); }
  60% { transform: scale(1.07); }
  100% { transform: scale(1); }
}
.bubble--bot {
  align-self: flex-start;
  background: var(--surface-alt, #1a1d27);
  border: 1px solid var(--border);
  border-radius: 12px 12px 12px 4px;
  color: var(--text);
}
.bubble--me {
  align-self: flex-end;
  background: var(--accent, #4a7dff);
  color: #fff;
  border-radius: 12px 12px 4px 12px;
}
.dots {
  color: var(--text-muted);
}
.chat__error {
  font-size: 11.5px;
  color: var(--danger);
  margin: 0;
}
.chat__input {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--border);
  background: var(--surface-alt, #1a1d27);
}
.chat__input input {
  flex: 1;
  font-family: var(--font);
  font-size: 12.5px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface, #12141c);
  color: var(--text);
}
.chat__input input:focus {
  outline: none;
  border-color: var(--accent, #4a7dff);
}
.chat__input button {
  font-family: var(--font);
  font-size: 12.5px;
  font-weight: 600;
  padding: 8px 14px;
  border: 0;
  border-radius: var(--radius-sm);
  background: var(--accent, #4a7dff);
  color: #fff;
  cursor: pointer;
}
.chat__input button:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
