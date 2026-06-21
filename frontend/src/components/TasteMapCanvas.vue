<script setup>
// 취향 지도 렌더러 (F-MAP-01, 김호준) — 어두운 배경 위 '내가 본 영화'만 빛나는 별.
// 별점 = 별의 크기 + 밝기(+색). 고평점=크고 또렷·따뜻, 저평점=작고 흐릿·차가움. 4.5↑ 반짝.
// 같은 좌표에 겹치는 영화는 살짝 흩뿌려(spiral) 둘 다 보이게 한다.
// 홈 프리뷰(읽기전용)·지도 페이지(인터랙티브) 공유. 데이터 fetch·게이트·탭은 부모 책임.
import { computed, ref } from "vue";

const props = defineProps({
  watched: { type: Array, required: true },     // [{movie_id,title,poster_path,release_year,x,y,rating}]
  interactive: { type: Boolean, default: true }, // 호버 툴팁·클릭 선택(프리뷰는 false)
  width: { type: Number, default: 640 },        // viewBox 비율(프리뷰는 와이드·낮게)
  height: { type: Number, default: 430 },
});
const emit = defineEmits(["select"]);

const W = props.width;
const H = props.height;
const PAD = 52;

const selectedId = ref(null);
const hovered = ref(null);             // { marker, x, y } 커서 옆 툴팁
const IMG = "https://image.tmdb.org/t/p/w185";

// 별점(0.5~5.0) → 크기·밝기·색. 레인지를 넓게 줘 별점 차이가 또렷하게 구분되도록.
function star(rating) {
  const t = Math.max(0, Math.min(1, (rating - 0.5) / 4.5));
  const a = [150, 164, 196], b = [255, 240, 205];   // 흐린 회청 → 밝은 크림
  const c = a.map((v, i) => Math.round(v + (b[i] - v) * t));
  return {
    color: `rgb(${c[0]},${c[1]},${c[2]})`,
    r: 3 + t * 8,                // 3 → 11  (크기)
    op: 0.32 + t * 0.68,         // 0.32 → 1.0 (밝기)
    bright: rating >= 4.5,
  };
}

// 본 영화 범위에 맞춰 UMAP→픽셀 변환. 좌표 자체는 전역 고정(불변식), viewport만 맞춤(빈 화면 방지).
const markers = computed(() => {
  if (!props.watched?.length) return [];
  const xs = props.watched.map((w) => w.x);
  const ys = props.watched.map((w) => w.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  const scale = Math.min(
    (W - 2 * PAD) / Math.max(maxX - minX, 1),
    (H - 2 * PAD) / Math.max(maxY - minY, 1),
  );
  const placed = [];
  return props.watched.map((w) => {
    const s = star(w.rating);
    let px = W / 2 + (w.x - cx) * scale;
    let py = H / 2 - (w.y - cy) * scale;   // 화면 y는 아래로 + → 부호 뒤집어 위로 +y
    // 겹침 분산: 이미 놓인 별과 너무 가까우면 황금각 나선으로 살짝 밀어 둘 다 보이게.
    const sep = s.r + 5;
    for (let k = 0; placed.some((p) => Math.hypot(p.px - px, p.py - py) < sep) && k < 16; k++) {
      const ang = k * 2.39996, rad = sep + k * 1.6;
      px = (W / 2 + (w.x - cx) * scale) + Math.cos(ang) * rad;
      py = (H / 2 - (w.y - cy) * scale) + Math.sin(ang) * rad;
    }
    placed.push({ px, py });
    return { ...w, px, py, ...s };
  });
});
const selected = computed(() => markers.value.find((m) => m.movie_id === selectedId.value) || null);

function onSelect(m) {
  if (!props.interactive) return;
  selectedId.value = m.movie_id;
  emit("select", m);
}
function onHover(m, e) {
  if (!props.interactive) return;
  hovered.value = { marker: m, x: e.clientX, y: e.clientY };
}
function poster(p) {
  return p ? IMG + p : "";
}
</script>

<template>
  <div class="canvas-wrap">
    <svg
      :viewBox="`0 0 ${W} ${H}`"
      class="mapsvg"
      @mouseleave="hovered = null"
    >
      <defs>
        <filter
          id="glow"
          x="-120%"
          y="-120%"
          width="340%"
          height="340%"
        >
          <feGaussianBlur
            stdDeviation="2.2"
            result="b"
          />
          <feMerge>
            <feMergeNode in="b" /><feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <rect
        :width="W"
        :height="H"
        fill="#0e1018"
      />
      <!-- 옅은 격자 -->
      <g
        stroke="#1c1f2c"
        stroke-width="1"
      >
        <line
          v-for="i in 4"
          :key="`h${i}`"
          x1="0"
          :y1="(H / 5) * i"
          :x2="W"
          :y2="(H / 5) * i"
        />
        <line
          v-for="i in 7"
          :key="`v${i}`"
          :x1="(W / 8) * i"
          y1="0"
          :x2="(W / 8) * i"
          :y2="H"
        />
      </g>

      <!-- 본 영화 = 빛나는 별 (별점 = 크기·밝기) -->
      <g filter="url(#glow)">
        <circle
          v-for="m in markers"
          :key="m.movie_id"
          :cx="m.px"
          :cy="m.py"
          :r="m.r"
          :fill="m.color"
          :fill-opacity="m.op"
          class="star"
          :class="{ 'star--bright': m.bright, 'star--live': interactive, 'star--sel': selectedId === m.movie_id }"
          @click="onSelect(m)"
          @mouseenter="onHover(m, $event)"
          @mousemove="onHover(m, $event)"
          @mouseleave="hovered = null"
        />
      </g>

      <!-- 선택 별 강조 링 -->
      <circle
        v-if="interactive && selected"
        :cx="selected.px"
        :cy="selected.py"
        :r="selected.r + 7"
        fill="none"
        stroke="#aee1ff"
        stroke-width="1.6"
        opacity="0.9"
      />
    </svg>

    <!-- 커서 옆 호버 툴팁 (별점 10점 표기) -->
    <div
      v-if="interactive && hovered"
      class="tip"
      :style="{ left: hovered.x + 14 + 'px', top: hovered.y + 14 + 'px' }"
    >
      <img
        v-if="poster(hovered.marker.poster_path)"
        :src="poster(hovered.marker.poster_path)"
        :alt="hovered.marker.title"
        class="tip__poster"
      >
      <div class="tip__meta">
        <div class="tip__title">
          {{ hovered.marker.title }}
        </div>
        <div class="tip__sub">
          {{ hovered.marker.release_year || "" }} · ★ {{ hovered.marker.rating * 2 }} / 10
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.canvas-wrap {
  position: relative;
}
.mapsvg {
  display: block;
  width: 100%;
}
.star--live {
  cursor: pointer;
  transition: fill-opacity 0.15s;
}
.star--live:hover,
.star--sel {
  fill-opacity: 1 !important;
}
.star--bright {
  animation: twinkle 2.6s ease-in-out infinite;
}
@keyframes twinkle {
  0%, 100% { fill-opacity: 1; }
  50% { fill-opacity: 0.62; }
}

/* 커서 추적 툴팁 */
.tip {
  position: fixed;
  z-index: 50;
  display: flex;
  gap: 8px;
  padding: 8px;
  max-width: 230px;
  background: rgba(14, 16, 24, 0.96);
  border: 1px solid #2c3142;
  border-radius: 6px;
  pointer-events: none;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
}
.tip__poster {
  width: 38px;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  border-radius: 3px;
  flex: none;
}
.tip__meta {
  min-width: 0;
}
.tip__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.35;
}
.tip__sub {
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--text-muted);
}
</style>
