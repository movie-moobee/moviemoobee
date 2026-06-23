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
  anchors: { type: Array, default: () => [] },  // [{name,x,y}] 장르 대륙(A-14). 있으면 고정 뷰포트.
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

// 장르 대륙 색(월드 모드). 마커는 가장 가까운 대륙 색을 입어 '어느 영토에 있나'가 한눈에.
const GENRE_COLORS = {
  공포: "#a55ec9", 스릴러: "#7d5fff", 범죄: "#b066c9", 미스터리: "#5b6ee0",
  드라마: "#7fa8e8", 로맨스: "#fd79a8", 액션: "#ff7a6b", SF: "#19c6c0",
  모험: "#1dd1a1", 전쟁: "#9bd14e", 역사: "#c2d14e", 가족: "#3fbf8e",
  코미디: "#f0c050", 판타지: "#c56cf0", 애니메이션: "#4aa8e8", 음악: "#e0b84a",
};
function lighten(hex, m) {
  const n = parseInt(hex.slice(1), 16);
  const f = (c) => Math.round(c + (255 - c) * m);
  return `rgb(${f((n >> 16) & 255)},${f((n >> 8) & 255)},${f(n & 255)})`;
}
function nearestColor(x, y) {
  let best = "#9aa3bd", bd = Infinity;
  for (const a of props.anchors || []) {
    const d = (a.x - x) ** 2 + (a.y - y) ** 2;
    if (d < bd) { bd = d; best = GENRE_COLORS[a.name] || best; }
  }
  return best;
}

// 좌표→픽셀 변환. 앵커(대륙) 있으면 '전역 고정 뷰포트'(원점 중심, 대륙이 항상 같은 자리=안정적
// 랜드마크, A-14). 없으면 본 영화 범위 auto-fit(홈 프리뷰 등). 좌표 자체는 전역 고정(불변식).
const transform = computed(() => {
  if (props.anchors?.length) {
    // 대륙 있으면 x·y 각각 캔버스에 맞춰 채운다(와이드 캔버스 활용). 좌표 원점 중심 고정.
    let rx = 1, ry = 1;
    for (const a of props.anchors) { rx = Math.max(rx, Math.abs(a.x)); ry = Math.max(ry, Math.abs(a.y)); }
    rx *= 1.1; ry *= 1.12;   // 대륙 바깥 여백
    return { cx: 0, cy: 0, sx: (W - 2 * PAD) / (2 * rx), sy: (H - 2 * PAD) / (2 * ry) };
  }
  const xs = props.watched.map((w) => w.x);
  const ys = props.watched.map((w) => w.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const s = Math.min((W - 2 * PAD) / Math.max(maxX - minX, 1), (H - 2 * PAD) / Math.max(maxY - minY, 1));
  return { cx: (minX + maxX) / 2, cy: (minY + maxY) / 2, sx: s, sy: s };
});
const project = (x, y, t) => [W / 2 + (x - t.cx) * t.sx, H / 2 - (y - t.cy) * t.sy];

// 본 영화 마커. 겹침은 황금각 나선으로 분산.
const markers = computed(() => {
  if (!props.watched?.length) return [];
  const t = transform.value;
  const placed = [];
  return props.watched.map((w) => {
    const v = vis(w.rating);
    let [px, py] = project(w.x, w.y, t);   // 화면 y는 아래로 + → project가 부호 뒤집음
    const [bx, by] = [px, py];
    const sep = v.r + 5;
    for (let k = 0; placed.some((p) => Math.hypot(p.px - px, p.py - py) < sep) && k < 16; k++) {
      const ang = k * 2.39996, rad = sep + k * 1.6;
      px = bx + Math.cos(ang) * rad;
      py = by + Math.sin(ang) * rad;
    }
    placed.push({ px, py });
    return {
      ...w, px, py, thumb: w.poster_path ? THUMB + w.poster_path : "",
      dotColor: nearestColor(w.x, w.y), ...v,
    };
  });
});
// 대륙(앵커) 라벨·영토 위치 — 마커와 같은 변환으로 투영.
const anchorMarkers = computed(() => {
  const t = transform.value;
  return (props.anchors || []).map((a) => {
    const [px, py] = project(a.x, a.y, t);
    const c = GENRE_COLORS[a.name] || "#6b76a0";
    return { name: a.name, px, py, color: c, colorSoft: lighten(c, 0.32) };
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
        <radialGradient id="continent">
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
        <filter
          id="softTer"
          x="-80%"
          y="-80%"
          width="260%"
          height="260%"
        >
          <feGaussianBlur stdDeviation="22" />
        </filter>
        <filter
          id="dotglow"
          x="-150%"
          y="-150%"
          width="400%"
          height="400%"
        >
          <feGaussianBlur stdDeviation="2.6" />
        </filter>
      </defs>

      <rect
        :width="W"
        :height="H"
        :fill="mode === 'posters' ? '#080a10' : '#0e1018'"
      />

      <!-- 장르 대륙 글로우(배경 — 별 뒤). 월드 모드는 장르색 파스텔 영토. 라벨은 최상단(A-14). -->
      <g
        v-if="anchorMarkers.length"
        class="continents"
      >
        <g
          v-if="mode === 'clean'"
          filter="url(#softTer)"
          opacity="0.4"
        >
          <circle
            v-for="a in anchorMarkers"
            :key="`cg${a.name}`"
            :cx="a.px"
            :cy="a.py"
            :r="Math.min(W, H) * 0.16"
            :fill="a.colorSoft"
          />
        </g>
        <template v-else>
          <circle
            v-for="a in anchorMarkers"
            :key="`cg${a.name}`"
            :cx="a.px"
            :cy="a.py"
            :r="Math.min(W, H) * 0.075"
            fill="url(#continent)"
          />
        </template>
      </g>

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
      <template v-else-if="mode === 'posters'">
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

      <!-- ===== 월드 모드: 깔끔한 점(흰 코어 + 대륙색 링), 크기=별점 ===== -->
      <template v-else>
        <g
          v-for="m in markers"
          :key="m.movie_id"
          :class="{ 'thumb--live': interactive }"
          @click="onSelect(m)"
          @mouseenter="onHover(m, $event)"
          @mousemove="onHover(m, $event)"
          @mouseleave="hovered = null"
        >
          <circle
            :cx="m.px"
            :cy="m.py"
            :r="m.r + 3"
            :fill="m.dotColor"
            fill-opacity="0.45"
            filter="url(#dotglow)"
          />
          <circle
            :cx="m.px"
            :cy="m.py"
            :r="m.r"
            fill="#ffffff"
          />
          <circle
            :cx="m.px"
            :cy="m.py"
            :r="m.r"
            fill="none"
            :stroke="m.dotColor"
            stroke-width="2.4"
          />
        </g>
      </template>

      <!-- 대륙 라벨 — 별 위에 떠서 항상 읽히는 '지도 범례' 레이어 (A-14) -->
      <g
        v-if="anchorMarkers.length"
        class="continents"
      >
        <text
          v-for="a in anchorMarkers"
          :key="`ct${a.name}`"
          :x="a.px"
          :y="a.py"
          class="continent-label"
        >{{ a.name }}</text>
      </g>

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
.continents {
  pointer-events: none;
}
.continent-label {
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
