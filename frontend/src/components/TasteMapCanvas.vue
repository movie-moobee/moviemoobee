<script setup>
// 취향 지도 렌더러 (F-MAP-01, 김호준) — 두 모드 토글: 'stars'(글로우 별) / 'posters'(포스터 섬).
//  · stars : 별점 = 별 크기·밝기·색. 4.5↑ 반짝. 어두운 배경 + 격자.
//  · posters: 좌표에 포스터 썸네일(별점=크기+하단 금색 바), 군집 뒤 소프트 섬.
// 같은 좌표 겹침은 황금각 나선으로 분산. 홈 프리뷰·지도 페이지 공유. fetch·게이트는 부모 책임.
import { computed, ref } from "vue";

const props = defineProps({
  watched: { type: Array, required: true },     // [{movie_id,title,poster_path,release_year,x,y,rating}]
  interactive: { type: Boolean, default: true }, // 호버 툴팁·클릭 선택(프리뷰는 false)
  width: { type: Number, default: 640 },        // viewBox 비율(프리뷰는 와이드·낮게)
  height: { type: Number, default: 430 },
  highlightId: { type: Number, default: null }, // 지도 내 검색(3.4): 이 영화 마커 반짝
  mode: { type: String, default: "stars" },     // 'stars' | 'posters'
});
const emit = defineEmits(["select"]);

const W = props.width;
const H = props.height;
const PAD = 56;
const ISLE_R = Math.min(W, H) * 0.18;   // 포스터 모드 섬 블롭 반경
const THUMB = "https://image.tmdb.org/t/p/w92";
const IMG = "https://image.tmdb.org/t/p/w185";

const selectedId = ref(null);
const hovered = ref(null);             // { marker, x, y } 커서 옆 툴팁

// 별점(0.5~5.0) → 별/포스터 시각값.
function vis(rating) {
  const t = Math.max(0, Math.min(1, (rating - 0.5) / 4.5));
  const a = [150, 164, 196], b = [255, 240, 205];   // 흐린 회청 → 밝은 크림(별)
  const c = a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const ph = 26 + t * 16, pw = ph * 0.67;            // 포스터 크기
  return {
    color: `rgb(${c[0]},${c[1]},${c[2]})`,
    r: 3 + t * 8, op: 0.32 + t * 0.68, bright: rating >= 4.5,   // 별
    pw, ph, barW: pw * (rating / 5),                            // 포스터
  };
}

// 본 영화 범위에 맞춰 UMAP→픽셀 변환. 좌표 전역 고정(불변식), viewport만 맞춤. 겹침 나선 분산.
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
    const v = vis(w.rating);
    let px = W / 2 + (w.x - cx) * scale;
    let py = H / 2 - (w.y - cy) * scale;   // 화면 y는 아래로 + → 부호 뒤집어 위로 +y
    const sep = v.r + 5;
    for (let k = 0; placed.some((p) => Math.hypot(p.px - px, p.py - py) < sep) && k < 16; k++) {
      const ang = k * 2.39996, rad = sep + k * 1.6;
      px = (W / 2 + (w.x - cx) * scale) + Math.cos(ang) * rad;
      py = (H / 2 - (w.y - cy) * scale) + Math.sin(ang) * rad;
    }
    placed.push({ px, py });
    return { ...w, px, py, thumb: w.poster_path ? THUMB + w.poster_path : "", ...v };
  });
});
// 포스터 모드: 겹칠 때 고평점이 위로 오도록 별점 오름차순.
const drawOrder = computed(() => [...markers.value].sort((a, b) => a.rating - b.rating));
const selected = computed(() => markers.value.find((m) => m.movie_id === selectedId.value) || null);
const highlighted = computed(() => markers.value.find((m) => m.movie_id === props.highlightId) || null);

function ringR(m) {
  return props.mode === "posters" ? m.ph / 2 + 8 : m.r + 9;
}
function onSelect(m) {
  if (!props.interactive) return;
  if (selectedId.value === m.movie_id) {   // 같은 별 재클릭 → 선택 해제(패널·링 사라짐)
    selectedId.value = null;
    emit("select", null);
    return;
  }
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
        <radialGradient id="isle">
          <stop
            offset="0%"
            stop-color="#2b6f6a"
            stop-opacity="0.28"
          />
          <stop
            offset="60%"
            stop-color="#1f534f"
            stop-opacity="0.08"
          />
          <stop
            offset="100%"
            stop-color="#1f534f"
            stop-opacity="0"
          />
        </radialGradient>
      </defs>

      <rect
        :width="W"
        :height="H"
        :fill="mode === 'posters' ? '#080a10' : '#0e1018'"
      />

      <!-- ===== 별 모드 ===== -->
      <template v-if="mode === 'stars'">
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
      </template>

      <!-- ===== 포스터 모드 ===== -->
      <template v-else>
        <!-- 섬: 조밀할수록 또렷한 블롭 -->
        <g>
          <circle
            v-for="m in markers"
            :key="`i${m.movie_id}`"
            :cx="m.px"
            :cy="m.py"
            :r="ISLE_R"
            fill="url(#isle)"
          />
        </g>
        <!-- 포스터 썸네일 (별점 = 크기 + 하단 금색 바) -->
        <g
          v-for="m in drawOrder"
          :key="m.movie_id"
          :class="{ 'thumb--live': interactive }"
          @click="onSelect(m)"
          @mouseenter="onHover(m, $event)"
          @mousemove="onHover(m, $event)"
          @mouseleave="hovered = null"
        >
          <image
            v-if="m.thumb"
            :href="m.thumb"
            :x="m.px - m.pw / 2"
            :y="m.py - m.ph / 2"
            :width="m.pw"
            :height="m.ph"
            preserveAspectRatio="xMidYMid slice"
          />
          <rect
            v-else
            :x="m.px - m.pw / 2"
            :y="m.py - m.ph / 2"
            :width="m.pw"
            :height="m.ph"
            fill="#222838"
          />
          <rect
            :x="m.px - m.pw / 2"
            :y="m.py - m.ph / 2"
            :width="m.pw"
            :height="m.ph"
            fill="none"
            stroke="#000"
            stroke-opacity="0.35"
            :class="{ 'thumb__edge--sel': selectedId === m.movie_id }"
          />
          <rect
            :x="m.px - m.pw / 2"
            :y="m.py + m.ph / 2 - 3"
            :width="m.barW"
            height="3"
            fill="#f4b860"
          />
        </g>
      </template>

      <!-- 선택 강조 링 -->
      <circle
        v-if="interactive && selected"
        :cx="selected.px"
        :cy="selected.py"
        :r="ringR(selected)"
        fill="none"
        stroke="#aee1ff"
        stroke-width="1.6"
        opacity="0.9"
      />
      <!-- 지도 내 검색: 매칭 마커 반짝 (3.4) -->
      <circle
        v-if="highlighted"
        :cx="highlighted.px"
        :cy="highlighted.py"
        :r="ringR(highlighted) + 3"
        fill="none"
        stroke="#aee1ff"
        stroke-width="2.5"
        class="blink"
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
.thumb--live {
  cursor: pointer;
}
.thumb--live:hover .thumb__edge--sel,
.thumb__edge--sel {
  stroke: #aee1ff;
  stroke-opacity: 1;
  stroke-width: 2.5;
}
.blink {
  animation: blink 0.85s ease-in-out infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.15; }
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
