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
  // 지도 탐색(4.4): 추천 핀 오버레이 [{id,title,poster_path,release_year,vote_average,x,y,num,kind}].
  // kind: 'safe'(하늘색) | 'unexplored'(호박색). 비면 핀 없음(취향 지도 탭).
  pins: { type: Array, default: () => [] },
});
const emit = defineEmits(["select", "pin-click"]);

const W = props.width;
const H = props.height;
const PAD = 56;
const THUMB = "https://image.tmdb.org/t/p/w92";
const IMG = "https://image.tmdb.org/t/p/w185";

const selectedId = ref(null);
const hovered = ref(null);             // { marker, x, y } 커서 옆 툴팁

// ── 확대/축소 (item 1) — 마우스 휠로 커서 지점 기준 확대·축소, 확대 상태에선 드래그로 팬.
//    데이터 레이어 전체를 한 그룹(viewTransform)으로 변환. 우하단 미니맵으로 현재 영역 표시. ──
const svgEl = ref(null);
const zoom = ref(1);                     // 1~4배
const pan = ref({ x: 0, y: 0 });         // viewBox 단위 이동
const viewTransform = computed(() => {
  const z = zoom.value, cx = W / 2, cy = H / 2;
  return `translate(${pan.value.x},${pan.value.y}) translate(${cx},${cy}) scale(${z}) translate(${-cx},${-cy})`;
});
function clientToVB(e) {                  // 화면 좌표 → viewBox 좌표
  const r = svgEl.value.getBoundingClientRect();
  return { x: ((e.clientX - r.left) / r.width) * W, y: ((e.clientY - r.top) / r.height) * H };
}
// nz 배율로 바꾸되 anchor(화면점) 아래 지점이 그대로 머물게 pan 보정 → 커서 기준 확대
function applyZoom(nz, anchor) {
  const cx = W / 2, cy = H / 2, z = zoom.value;
  const a = { x: cx + (anchor.x - pan.value.x - cx) / z, y: cy + (anchor.y - pan.value.y - cy) / z };
  nz = Math.max(1, Math.min(4, nz));
  if (nz === 1) { zoom.value = 1; pan.value = { x: 0, y: 0 }; return; }
  zoom.value = nz;
  pan.value = { x: anchor.x - cx - nz * (a.x - cx), y: anchor.y - cy - nz * (a.y - cy) };
}
function onWheel(e) {
  if (!props.interactive) return;
  e.preventDefault();
  applyZoom(zoom.value * (e.deltaY < 0 ? 1.18 : 1 / 1.18), clientToVB(e));
}
// 확대 상태에서 드래그 팬
let dragStart = null;
const panMoved = ref(false);             // 드래그였으면 클릭(선택) 무시
function onPointerDown(e) {
  if (!props.interactive || zoom.value <= 1) return;
  dragStart = { x: e.clientX, y: e.clientY, px: pan.value.x, py: pan.value.y };
  panMoved.value = false;
}
function onPointerMove(e) {
  if (!dragStart) return;
  const k = W / svgEl.value.getBoundingClientRect().width;   // 화면 px → viewBox 단위
  const dx = (e.clientX - dragStart.x) * k, dy = (e.clientY - dragStart.y) * k;
  if (Math.hypot(dx, dy) > 3) panMoved.value = true;
  pan.value = { x: dragStart.px + dx, y: dragStart.py + dy };
}
function onPointerUp() { dragStart = null; }

// 미니맵(확대 시 우하단): 전체 지도 + 현재 보는 영역 박스 (item 1)
const MINI_W = 150;
const miniScale = MINI_W / W;
const miniH = H * (MINI_W / W);
const miniView = computed(() => {        // 화면(0..W,0..H)에 해당하는 콘텐츠 범위를 미니맵 좌표로
  const z = zoom.value, cx = W / 2, cy = H / 2, s = miniScale;
  const x0 = cx + (-pan.value.x - cx) / z, x1 = cx + (W - pan.value.x - cx) / z;
  const y0 = cy + (-pan.value.y - cy) / z, y1 = cy + (H - pan.value.y - cy) / z;
  return { x: x0 * s, y: y0 * s, w: (x1 - x0) * s, h: (y1 - y0) * s };
});
const miniDots = computed(() =>          // 컨텍스트용 별 점(축소)
  markers.value.map((m) => ({ x: m.px * miniScale, y: m.py * miniScale, r: Math.max(0.6, m.r * miniScale) })));

// 별점(0.5~5.0) → 별/포스터 시각값.
function vis(rating) {
  const t = Math.max(0, Math.min(1, (rating - 0.5) / 4.5));
  // 별 크기: 하한 6.5px(=원래 5/10점 크기 — 저평점도 충분히 보임) + 고평점일수록 가속(t^1.8)
  //         → 8·9·10점 크기 차이가 뚜렷, 1·2점도 안 사라짐 (item 2)
  const ts = Math.pow(t, 1.8);
  const a = [150, 164, 196], b = [255, 240, 205];   // 흐린 회청 → 밝은 크림(별)
  const c = a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const ph = 26 + t * 16, pw = ph * 0.67;            // 포스터 크기
  return {
    color: `rgb(${c[0]},${c[1]},${c[2]})`,
    r: 6 + ts * 7, op: 0.32 + t * 0.68, bright: rating >= 4.5,   // 별
    pw, ph, barW: pw * (rating / 5),                            // 포스터
  };
}

// 좌표→픽셀 변환. 앵커(대륙) 있으면 '전역 고정 뷰포트'(원점 중심, 대륙이 항상 같은 자리=안정적
// 랜드마크, A-14). 없으면 본 영화 범위 auto-fit(홈 프리뷰 등). 좌표 자체는 전역 고정(불변식).
const transform = computed(() => {
  if (props.anchors?.length) {
    // 대륙 있으면 x·y 각각 캔버스에 맞춰 채운다(와이드 캔버스 활용). 좌표 원점 중심 고정.
    let rx = 1, ry = 1;
    for (const a of props.anchors) { rx = Math.max(rx, Math.abs(a.x)); ry = Math.max(ry, Math.abs(a.y)); }
    rx *= 1.1; ry *= 1.12;   // 대륙 바깥 여백
    // 균일 스케일(x·y 동일) — 좌표 모양 보존. 비균일이면 와이드 캔버스(프리뷰)에서 세로로 찌그러짐.
    const s = Math.min((W - 2 * PAD) / (2 * rx), (H - 2 * PAD) / (2 * ry));
    return { cx: 0, cy: 0, sx: s, sy: s };
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
    // 겹침 분산 간격: 포스터 모드는 썸네일 크기 기준(별 반경보다 훨씬 큼 — item 9b)
    const sep = props.mode === "posters" ? Math.max(v.pw, v.ph) * 0.62 + 4 : v.r + 5;
    for (let k = 0; placed.some((p) => Math.hypot(p.px - px, p.py - py) < sep) && k < 16; k++) {
      const ang = k * 2.39996, rad = sep + k * 1.6;
      px = bx + Math.cos(ang) * rad;
      py = by + Math.sin(ang) * rad;
    }
    placed.push({ px, py });
    return {
      ...w, px, py, thumb: w.poster_path ? THUMB + w.poster_path : "", ...v,
    };
  });
});
// 대륙(앵커) 라벨·영토 위치 — 마커와 같은 변환으로 투영.
const anchorMarkers = computed(() => {
  const t = transform.value;
  return (props.anchors || []).map((a) => {
    const [px, py] = project(a.x, a.y, t);
    return { name: a.name, px, py };
  });
});
// 지도 탐색(4.4) 추천 핀 — 마커와 같은 변환으로 투영. 겹치면 황금각 나선 분산 + 원위치 연결선.
const PIN_SEP = 30;
const pinMarkers = computed(() => {
  if (!props.pins?.length) return [];
  const t = transform.value;
  const placed = [];
  return props.pins.map((m) => {
    const [bx, by] = project(m.x, m.y, t);
    let px = bx, py = by;
    for (let k = 0; placed.some((p) => Math.hypot(p.px - px, p.py - py) < PIN_SEP) && k < 24; k++) {
      const ang = k * 2.39996, rad = PIN_SEP + k * 4;
      px = bx + Math.cos(ang) * rad;
      py = by + Math.sin(ang) * rad;
    }
    placed.push({ px, py });
    const safe = m.kind === "safe";
    return { ...m, px, py, bx, by, moved: Math.hypot(px - bx, py - by) > 2,
      fill: safe ? "#5bc5ff" : "#ff9d2e", textColor: safe ? "#07283a" : "#241a07" };
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
  if (!props.interactive || panMoved.value) return;   // 드래그 팬이었으면 선택 무시
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
function onPinHover(m, e) {
  hovered.value = { marker: m, x: e.clientX, y: e.clientY, pin: true };   // 핀=추천(평점 10점)
}
function onPinClick(m) {
  if (panMoved.value) return;   // 드래그-줌이었으면 핀 클릭(상세 이동) 무시
  emit("pin-click", m);
}
function poster(p) {
  return p ? IMG + p : "";
}

// 5각 별 path (별 모드). 바깥 반경 r, 안쪽 0.42r. 위 꼭짓점부터 시계방향.
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

// 성운(별 모드 배경) — 좌표는 캔버스 비율 고정. 푸른 가스 구름 4덩이.
const nebulae = computed(() => [
  { cx: W * 0.2, cy: H * 0.62, r: Math.min(W, H) * 0.42 },
  { cx: W * 0.74, cy: H * 0.34, r: Math.min(W, H) * 0.36 },
  { cx: W * 0.55, cy: H * 0.82, r: Math.min(W, H) * 0.3 },
  { cx: W * 0.88, cy: H * 0.58, r: Math.min(W, H) * 0.26 },
]);
</script>

<template>
  <div class="canvas-wrap">
    <svg
      ref="svgEl"
      :viewBox="`0 0 ${W} ${H}`"
      class="mapsvg"
      :class="{ 'mapsvg--grab': interactive && zoom > 1 }"
      @mouseleave="hovered = null"
      @wheel="onWheel"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointerleave="onPointerUp"
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
        <radialGradient id="nebula">
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

      <!-- 확대/축소·팬 대상: 배경 rect를 뺀 모든 데이터/장식 레이어를 한 그룹으로 변환 (item 1) -->
      <g :transform="viewTransform">
      <!-- 공통 배경(별·포스터 모드 통일, item 9): 성운 + 옅은 격자 -->
      <g class="continents">
        <circle
          v-for="(n, i) in nebulae"
          :key="`neb${i}`"
          :cx="n.cx"
          :cy="n.cy"
          :r="n.r"
          fill="url(#nebula)"
        />
      </g>
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
      <!-- 장르 대륙 글로우(별 뒤). 라벨은 최상단(A-14). -->
      <g
        v-if="anchorMarkers.length"
        class="continents"
      >
        <circle
          v-for="a in anchorMarkers"
          :key="`cg${a.name}`"
          :cx="a.px"
          :cy="a.py"
          :r="Math.min(W, H) * 0.075"
          fill="url(#continent)"
        />
      </g>

      <!-- ===== 별 모드 ===== -->
      <template v-if="mode === 'stars'">
        <!-- 본 영화 = 빛나는 별 (별점 = 크기·밝기). 별 모양 path. -->
        <g filter="url(#glow)">
          <path
            v-for="m in markers"
            :key="m.movie_id"
            :d="starPath(m.px, m.py, m.r)"
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

      <!-- ===== 포스터 모드 (배경은 별 모드와 공통) ===== -->
      <template v-else-if="mode === 'posters'">
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

      <!-- 지도 탐색(4.4) 추천 핀 — 토글 켠 것만, 번호. 겹치면 분산 + 원위치 연결선. -->
      <g
        v-for="m in pinMarkers"
        :key="`pin${m.id}`"
        class="pinmk"
        @click="onPinClick(m)"
        @mouseenter="onPinHover(m, $event)"
        @mousemove="onPinHover(m, $event)"
        @mouseleave="hovered = null"
      >
        <line
          v-if="m.moved"
          :x1="m.bx"
          :y1="m.by"
          :x2="m.px"
          :y2="m.py"
          :stroke="m.fill"
          stroke-opacity="0.4"
          stroke-width="1"
        />
        <circle
          v-if="m.moved"
          :cx="m.bx"
          :cy="m.by"
          r="2"
          :fill="m.fill"
          fill-opacity="0.5"
        />
        <circle
          :cx="m.px"
          :cy="m.py"
          r="13"
          :fill="m.fill"
          filter="url(#glow)"
        />
        <text
          :x="m.px"
          :y="m.py + 4"
          :fill="m.textColor"
          font-size="12"
          font-weight="700"
          text-anchor="middle"
          style="pointer-events: none"
        >{{ m.num }}</text>
      </g>

      <!-- 선택 표시는 별 자체에 (star--sel) — 색변경 + 커짐 + 발광. 포스터 모드는 테두리 강조. -->
      <!-- 선택한 별은 장르 라벨 위에 한 번 더 그려 '앞으로' 보낸다(겹쳐 가려도 클릭 시 보이게).
           pointer-events:none → 밑의 원본 별이 그대로 클릭(재클릭=해제)을 받는다. -->
      <g
        v-if="interactive && mode === 'stars' && selected"
        filter="url(#glow)"
        style="pointer-events: none"
      >
        <path
          :d="starPath(selected.px, selected.py, selected.r)"
          fill="#ffe6a8"
          class="star star--sel"
        />
      </g>
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
      </g>
    </svg>

    <!-- 미니맵: 확대 중일 때 우하단에 현재 보는 영역 표시 (item 1) -->
    <svg
      v-if="interactive && zoom > 1"
      class="minimap"
      :viewBox="`0 0 ${MINI_W} ${miniH}`"
      :width="MINI_W"
      :height="miniH"
    >
      <rect
        :width="MINI_W"
        :height="miniH"
        fill="#0b0e18"
        stroke="#2c3142"
      />
      <circle
        v-for="(d, i) in miniDots"
        :key="`md${i}`"
        :cx="d.x"
        :cy="d.y"
        :r="d.r"
        fill="#9fb4e6"
        fill-opacity="0.7"
      />
      <rect
        :x="miniView.x"
        :y="miniView.y"
        :width="miniView.w"
        :height="miniView.h"
        fill="#ffd479"
        fill-opacity="0.12"
        stroke="#ffd479"
        stroke-width="1.2"
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
          {{ hovered.marker.release_year || "" }} · ★ {{ hovered.pin ? hovered.marker.vote_average : hovered.marker.rating * 2 }} / 10
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
  touch-action: none;
}
.mapsvg--grab {
  cursor: grab;        /* 확대 상태: 드래그로 이동 */
}
.mapsvg--grab:active {
  cursor: grabbing;
}
.minimap {
  position: absolute;
  right: 12px;
  bottom: 12px;
  border-radius: 6px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
  pointer-events: none;
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
.star--live:hover {
  fill-opacity: 1 !important;
}
/* 선택된 별: 금빛으로 변하고 커지면서 발광 + 테두리 (item 4).
   .star.star--sel = 우선순위를 .star--bright(twinkle)보다 높여 고평점(9·10점) 별도 선택 시 펄스 적용 */
.star.star--sel {
  fill: #ffe6a8 !important;
  fill-opacity: 1 !important;
  stroke: #fff7e0;
  stroke-width: 0.7;
  paint-order: stroke;
  transform-box: fill-box;
  transform-origin: center;
  animation: starsel 1.5s ease-in-out infinite;
}
@keyframes starsel {
  0%, 100% { transform: scale(1.25); }
  50% { transform: scale(1.5); }
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
.pinmk {
  cursor: pointer;
}
.pinmk:hover circle {
  filter: brightness(1.25);
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
