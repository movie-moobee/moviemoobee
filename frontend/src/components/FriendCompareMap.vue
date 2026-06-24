<script setup>
// 친구 취향 비교 지도 (F-FRD-05, 5.3, 와이어프레임 13, 김호준) — 현재 '별' 취향 지도와
// 똑같은 룩(어두운 배경·성운·대륙·빛나는 별 모양)에 두 사람의 본 영화를 겹쳐 그린다.
// 별 색만 주인별로: 내 시청=연분홍 / 친구 시청=연한 청록 / 둘 다 본 공통작= 진한 노랑(강조).
// 무게중심(나/친구 점) 비교는 폐기(A-15) — 집합 기반 별 오버레이만. 공유 TasteMapCanvas는
// 별 스킨·탐색 핀과 한 세트라, 두 사용자 비교는 별도 캔버스로 둔다(룩은 동일하게 재현).
import { computed, ref } from "vue";

const props = defineProps({
  anchors: { type: Array, default: () => [] },   // [{name,x,y}] 장르 대륙(고정 뷰포트 랜드마크)
  mine: { type: Array, required: true },         // 내 본 영화 [{movie_id,title,poster_path,release_year,x,y,rating}]
  theirs: { type: Array, required: true },        // 친구 본 영화 (같은 형식)
  sharedIds: { type: Array, default: () => [] },  // 둘 다 본 영화 id
  friendName: { type: String, default: "친구" },
  recommended: { type: Array, default: () => [] }, // AI '지도에 표시' 추천작 [{id,title,poster_path,x,y}] (5.4)
});

const W = 640, H = 430, PAD = 56;
const IMG = "https://image.tmdb.org/t/p/w185";
// 색: 공통 시청작이 가장 눈에 띄도록 진한 노랑, 나·상대는 연한 파스텔로 양보.
const COLORS = { mine: "#ff9ecb", theirs: "#7fe0d6", shared: "#ffd21e" };

const hovered = ref(null);   // { marker, x, y }
const selectedId = ref(null);   // 클릭 선택한 별(취향 지도와 동일: 커지고 발광 + 라벨 앞으로)
function onSelect(m) {
  selectedId.value = selectedId.value === m.movie_id ? null : m.movie_id;
}

// 좌표→픽셀: 앵커 있으면 원점 중심 고정 뷰포트(대륙이 늘 같은 자리). TasteMapCanvas 와 동일 규칙.
const transform = computed(() => {
  let rx = 1, ry = 1;
  for (const a of props.anchors) { rx = Math.max(rx, Math.abs(a.x)); ry = Math.max(ry, Math.abs(a.y)); }
  rx *= 1.1; ry *= 1.12;
  return { sx: (W - 2 * PAD) / (2 * rx), sy: (H - 2 * PAD) / (2 * ry) };
});
const project = (x, y) => [W / 2 + x * transform.value.sx, H / 2 - y * transform.value.sy];

const anchorMarkers = computed(() =>
  props.anchors.map((a) => { const [px, py] = project(a.x, a.y); return { name: a.name, px, py }; }),
);

// 5각 별 path (TasteMapCanvas 별 모드와 동일). 바깥 r, 안쪽 0.42r, 위 꼭짓점부터.
function starPath(cx, cy, r) {
  const inner = r * 0.42;
  let d = "";
  for (let i = 0; i < 10; i++) {
    const ang = (Math.PI / 5) * i - Math.PI / 2;
    const rad = i % 2 === 0 ? r : inner;
    d += (i ? "L" : "M") + (cx + Math.cos(ang) * rad).toFixed(1) + "," + (cy + Math.sin(ang) * rad).toFixed(1);
  }
  return d + "Z";
}

// 두 세트를 movie_id 로 합쳐 주인 판정. 공유는 한 번만(같은 좌표) 보라로.
const SEP_GAP = 3;   // 별 사이 최소 여백
function visOf(m) {   // 별점 → 크기·밝기(취향 지도 별 모드와 동일 폭)
  const t = Math.max(0, Math.min(1, (m.rating - 0.5) / 4.5));
  return { t, r: (3 + t * 8) * (m.owner === "shared" ? 1.15 : 1), op: 0.32 + t * 0.68, bright: m.rating >= 4.5 };
}
const markers = computed(() => {
  const shared = new Set(props.sharedIds);
  const byId = new Map();
  for (const m of props.mine) byId.set(m.movie_id, { ...m, owner: shared.has(m.movie_id) ? "shared" : "mine", myRating: m.rating });
  for (const m of props.theirs) {
    const ex = byId.get(m.movie_id);
    if (ex) ex.friendRating = m.rating;                              // 공유 — 친구 별점 합치기
    else byId.set(m.movie_id, { ...m, owner: "theirs", friendRating: m.rating });
  }
  // 배치: 공통작 먼저(실제 위치 고정) → 나·상대 별이 비켜간다. 충돌은 '두 별 반경 합 + 여백'으로.
  const placed = [], pos = new Map();
  const order = [...byId.values()].sort((a, b) => (b.owner === "shared") - (a.owner === "shared"));
  for (const m of order) {
    const v = visOf(m);
    const [bx, by] = project(m.x, m.y);
    let px = bx, py = by;
    for (let k = 1; placed.some((p) => Math.hypot(p.px - px, p.py - py) < p.r + v.r + SEP_GAP) && k < 64; k++) {
      const ang = k * 2.39996, rad = (v.r + SEP_GAP) + k * 2.2;   // 황금각 나선으로 빈자리 탐색
      px = bx + Math.cos(ang) * rad; py = by + Math.sin(ang) * rad;
    }
    placed.push({ px, py, r: v.r });
    pos.set(m.movie_id, { px, py, ...v });
  }
  // 렌더 순서는 공통작을 마지막에 그려 위로 오게(강조 안 가려지게).
  return [...byId.values()]
    .sort((a, b) => (a.owner === "shared") - (b.owner === "shared"))
    .map((m) => {
      const p = pos.get(m.movie_id);
      return { ...m, px: p.px, py: p.py, r: p.r, op: p.op, bright: p.bright, color: COLORS[m.owner] };
    });
});

const selected = computed(() => markers.value.find((m) => m.movie_id === selectedId.value) || null);

// AI 추천작(지도에 표시) — 본 영화 별과 겹치지 않게 동일한 겹침 로직(황금각 나선) 적용.
// 본 영화 별을 먼저 깔고(markers) 추천을 그 빈자리로 밀어낸다. REC_R=링 반경(14) 기준.
const REC_R = 14;
const recMarkers = computed(() => {
  const placed = markers.value.map((m) => ({ px: m.px, py: m.py, r: m.r }));
  return (props.recommended || []).map((m) => {
    const [bx, by] = project(m.x, m.y);
    let px = bx, py = by;
    for (let k = 1; placed.some((p) => Math.hypot(p.px - px, p.py - py) < p.r + REC_R + SEP_GAP) && k < 64; k++) {
      const ang = k * 2.39996, rad = (REC_R + SEP_GAP) + k * 2.2;
      px = bx + Math.cos(ang) * rad; py = by + Math.sin(ang) * rad;
    }
    placed.push({ px, py, r: REC_R });
    return { ...m, px, py };
  });
});

// 성운(별 모드 배경) — 캔버스 비율 고정. TasteMapCanvas 와 동일 4덩이.
const nebulae = computed(() => [
  { cx: W * 0.2, cy: H * 0.62, r: Math.min(W, H) * 0.42 },
  { cx: W * 0.74, cy: H * 0.34, r: Math.min(W, H) * 0.36 },
  { cx: W * 0.55, cy: H * 0.82, r: Math.min(W, H) * 0.3 },
  { cx: W * 0.88, cy: H * 0.58, r: Math.min(W, H) * 0.26 },
]);

function onHover(m, e) { hovered.value = { marker: m, x: e.clientX, y: e.clientY }; }
function poster(p) { return p ? IMG + p : ""; }
</script>

<template>
  <div class="cmp-wrap">
    <svg
      :viewBox="`0 0 ${W} ${H}`"
      class="cmp-svg"
      @mouseleave="hovered = null"
    >
      <defs>
        <filter
          id="cmpGlow"
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
        <radialGradient id="cmpContinent">
          <stop
            offset="0%"
            stop-color="#3a4560"
            stop-opacity="0.30"
          />
          <stop
            offset="100%"
            stop-color="#2a3550"
            stop-opacity="0"
          />
        </radialGradient>
        <radialGradient id="cmpNebula">
          <stop
            offset="0%"
            stop-color="#3a5a8c"
            stop-opacity="0.5"
          />
          <stop
            offset="55%"
            stop-color="#243a63"
            stop-opacity="0.16"
          />
          <stop
            offset="100%"
            stop-color="#243a63"
            stop-opacity="0"
          />
        </radialGradient>
      </defs>

      <rect
        :width="W"
        :height="H"
        fill="#090b13"
      />

      <!-- 장르 대륙 글로우(배경 — 별 뒤) -->
      <g class="cmp-continents">
        <circle
          v-for="a in anchorMarkers"
          :key="`cg${a.name}`"
          :cx="a.px"
          :cy="a.py"
          :r="Math.min(W, H) * 0.075"
          fill="url(#cmpContinent)"
        />
      </g>

      <!-- 성운 가스 구름 -->
      <g class="cmp-continents">
        <circle
          v-for="(n, i) in nebulae"
          :key="`neb${i}`"
          :cx="n.cx"
          :cy="n.cy"
          :r="n.r"
          fill="url(#cmpNebula)"
        />
      </g>

      <!-- 옅은 점선 격자 -->
      <g
        stroke="#1b1f2e"
        stroke-width="1"
        stroke-dasharray="2 6"
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

      <!-- 본 영화 = 빛나는 별. 색=주인(나 빨강/친구 청록/공통 보라), 크기·밝기=별점 -->
      <g filter="url(#cmpGlow)">
        <path
          v-for="m in markers"
          :key="m.movie_id"
          :d="starPath(m.px, m.py, m.r)"
          :fill="m.color"
          :fill-opacity="m.op"
          class="cmp-star"
          :class="{ 'cmp-star--bright': m.bright, 'cmp-star--sel': selectedId === m.movie_id }"
          @click="onSelect(m)"
          @mouseenter="onHover(m, $event)"
          @mousemove="onHover(m, $event)"
          @mouseleave="hovered = null"
        />
      </g>

      <!-- 대륙 라벨(최상단 범례 레이어) -->
      <g class="cmp-continents">
        <text
          v-for="a in anchorMarkers"
          :key="`ct${a.name}`"
          :x="a.px"
          :y="a.py"
          class="cmp-label"
        >{{ a.name }}</text>
      </g>

      <!-- 선택한 별을 라벨 위에 한 번 더 그려 '앞으로' 보낸다(겹쳐 가려도 클릭 시 보이게) -->
      <g
        v-if="selected"
        filter="url(#cmpGlow)"
        style="pointer-events: none"
      >
        <path
          :d="starPath(selected.px, selected.py, selected.r)"
          :fill="selected.color"
          class="cmp-star cmp-star--sel"
        />
      </g>

      <!-- AI 추천작(지도에 표시) — 금빛 별 + 링, 라벨 위. 호버 시 정보 -->
      <g
        v-for="m in recMarkers"
        :key="`rec${m.id}`"
        class="cmp-rec"
        filter="url(#cmpGlow)"
        @mouseenter="onHover({ ...m, owner: 'rec' }, $event)"
        @mousemove="onHover({ ...m, owner: 'rec' }, $event)"
        @mouseleave="hovered = null"
      >
        <circle
          :cx="m.px"
          :cy="m.py"
          r="14"
          fill="none"
          stroke="#a884ff"
          stroke-width="2"
        />
        <path
          :d="starPath(m.px, m.py, 9)"
          fill="#cbb6ff"
        />
      </g>
    </svg>

    <!-- 커서 옆 호버 툴팁 -->
    <div
      v-if="hovered"
      class="cmp-tip"
      :style="{ left: hovered.x + 14 + 'px', top: hovered.y + 14 + 'px' }"
    >
      <img
        v-if="poster(hovered.marker.poster_path)"
        :src="poster(hovered.marker.poster_path)"
        :alt="hovered.marker.title"
        class="cmp-tip__poster"
      >
      <div class="cmp-tip__meta">
        <div class="cmp-tip__title">
          {{ hovered.marker.title }}
        </div>
        <div class="cmp-tip__sub">
          <template v-if="hovered.marker.owner === 'rec'">
            <b style="color: #cbb6ff">AI 추천</b> · 같이 볼 영화
          </template>
          <template v-else-if="hovered.marker.owner === 'shared'">
            둘 다 봄 · 나 ★{{ hovered.marker.myRating * 2 }} / {{ friendName }} ★{{ hovered.marker.friendRating * 2 }} / 10
          </template>
          <template v-else-if="hovered.marker.owner === 'mine'">
            나만 봄 · ★{{ hovered.marker.myRating * 2 }} / 10
          </template>
          <template v-else>
            {{ friendName }}만 봄 · ★{{ hovered.marker.friendRating * 2 }} / 10
          </template>
        </div>
      </div>
    </div>

    <!-- 범례(와이어프레임 13) -->
    <div class="cmp-legend">
      <span class="cmp-legend__item"><b :style="{ color: COLORS.mine }">★</b> 내 시청</span>
      <span class="cmp-legend__item"><b :style="{ color: COLORS.theirs }">★</b> {{ friendName }} 시청</span>
      <span class="cmp-legend__item"><b :style="{ color: COLORS.shared }">★</b> 공통 시청작</span>
    </div>
  </div>
</template>

<style scoped>
.cmp-wrap {
  position: relative;
}
.cmp-svg {
  display: block;
  width: 100%;
  border-radius: var(--radius);
}
.cmp-continents {
  pointer-events: none;
}
.cmp-label {
  fill: #99a2cc;
  font-size: 13px;
  font-weight: 500;
  text-anchor: middle;
  dominant-baseline: middle;
  letter-spacing: 0.04em;
  paint-order: stroke;
  stroke: #0e1018;
  stroke-width: 4px;
  stroke-linejoin: round;
}
.cmp-star {
  cursor: pointer;
  transition: fill-opacity 0.15s;
}
.cmp-star:hover {
  fill-opacity: 1 !important;
}
.cmp-star--bright {
  animation: cmp-twinkle 2.6s ease-in-out infinite;
}
@keyframes cmp-twinkle {
  0%, 100% { fill-opacity: 1; }
  50% { fill-opacity: 0.62; }
}
/* 선택된 별: 커지면서 발광 + 흰 테두리 (취향 지도와 동일 효과, 주인색 유지).
   .cmp-star.cmp-star--sel = 우선순위를 bright(twinkle)보다 높여 고평점 별도 펄스 적용 */
.cmp-star.cmp-star--sel {
  fill-opacity: 1 !important;
  stroke: #fff7e0;
  stroke-width: 0.7;
  paint-order: stroke;
  transform-box: fill-box;
  transform-origin: center;
  animation: cmp-sel 1.5s ease-in-out infinite;
}
@keyframes cmp-sel {
  0%, 100% { transform: scale(1.25); }
  50% { transform: scale(1.5); }
}
.cmp-rec {
  cursor: default;
  transform-box: fill-box;
  transform-origin: center;
  animation: cmp-recpulse 1.8s ease-in-out infinite;
}
@keyframes cmp-recpulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.cmp-legend {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-muted);
}
.cmp-legend__item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.cmp-legend__item b {
  font-size: 14px;
}
.cmp-tip {
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
.cmp-tip__poster {
  width: 38px;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  border-radius: 3px;
  flex: none;
}
.cmp-tip__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.35;
}
.cmp-tip__sub {
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--text-muted);
}
</style>
