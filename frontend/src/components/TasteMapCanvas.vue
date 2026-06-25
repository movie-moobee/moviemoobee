<script setup>
// 취향 지도 렌더러 (F-MAP-01, 김호준) — 두 모드 토글: 'stars'(글로우 별) / 'posters'(포스터 섬).
//  · stars : 별점 = 별 크기·밝기·색. 4.5↑ 반짝. 어두운 배경 + 격자.
//  · posters: 좌표에 포스터 썸네일(별점=크기+하단 금색 바), 군집 뒤 소프트 섬.
// 같은 좌표 겹침은 황금각 나선으로 분산. 홈 프리뷰·지도 페이지 공유. fetch·게이트는 부모 책임.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  watched: { type: Array, required: true },     // [{movie_id,title,poster_path,release_year,x,y,rating}]
  interactive: { type: Boolean, default: true }, // 호버 툴팁·클릭 선택(프리뷰는 false)
  width: { type: Number, default: 640 },        // viewBox 비율(프리뷰는 와이드·낮게)
  height: { type: Number, default: 430 },
  highlightId: { type: Number, default: null }, // 지도 내 검색(3.4): 이 영화 마커 반짝
  anchors: { type: Array, default: () => [] },  // [{name,x,y}] 장르 대륙(A-14). 있으면 고정 뷰포트.
  showGenreLabels: { type: Boolean, default: false }, // 대륙(장르) 글자 표시 토글
  showStarLabels: { type: Boolean, default: true }, // 고평점 영화 제목 라벨 표시 토글
  // 지도 탐색(4.4): 추천 핀 오버레이 [{id,title,poster_path,release_year,vote_average,x,y,num,kind}].
  // kind: 'safe'(하늘색) | 'unexplored'(호박색) | 'rec'(보라, AI 같이 볼 영화·번호 없음). 비면 핀 없음.
  pins: { type: Array, default: () => [] },
  // 색 기준: 'rating'(평점 티어) | 'owner'(친구 비교 — watched 각 별의 owner: mine/theirs/shared 로 색).
  colorBy: { type: String, default: "rating" },
  friendName: { type: String, default: "친구" },  // owner 모드 툴팁 표기용
  twinkleOwners: { type: Array, default: () => [] },  // owner 모드: 이 owner('mine'/'theirs'/'shared') 별을 반짝
});
const emit = defineEmits(["select", "pin-click", "open-detail", "clear-highlight"]);

const W = props.width;
const H = props.height;
const PAD = 56;
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

// 시안(Carbon) 별 팔레트 — 평점 티어별 색(c)·글로우 헤일로(g).
const STAR_PALETTE = {
  gold: { c: "#FFF0CD", g: "rgba(255,230,168,0.9)" },   // 9~10점(인생작)
  teal: { c: "#5DCAA5", g: "rgba(93,202,165,0.85)" },   // 7~8점(인상적)
  alabaster: { c: "#F2F0EB", g: "rgba(242,240,235,0.75)" },     // 5~6점(짙고 어두운 빨강)
  white: { c: "#C9D0E0", g: "rgba(201,208,224,0.7)" },  // 5점 미만(무난)
};

// 배경 별밭(장식) — 시안 지도처럼 본 영화 별 뒤에 흩뿌린 작은 별들. 영화 마커가 아니라 순수 배경
// 앰비언스(클릭·데이터 없음, 도메인 규칙과 무관). 매 렌더마다 흔들리지 않게 setup에서 1회만 생성.
const FIELD = (() => {
  const rnd = (a, b) => a + Math.random() * (b - a);
  // 본 영화 별(금/청록/흰)과 헷갈리지 않게, 배경은 흐릿한 청회색 계열만 사용.
  const cols = ["#414a66", "#4d567a", "#5a6390"];
  return Array.from({ length: 76 }, () => {
    return {
      x: rnd(14, W - 14), y: rnd(14, H - 14), r: rnd(0.7, 2.0),
      color: cols[Math.floor(Math.random() * cols.length)],
      twinkle: Math.random() < 0.5, delay: `${-rnd(0, 4).toFixed(2)}s`,
    };
  });
})();

// 친구 비교(owner 모드) 별 색 — 주인별. 내=분홍 / 친구=청록 / 공통작=진한 노랑(강조).
const OWNER_PALETTE = {
  mine: { c: "#ff9ecb", g: "rgba(255,158,203,0.7)" },
  theirs: { c: "#7fe0d6", g: "rgba(127,224,214,0.7)" },
  shared: { c: "#ffd21e", g: "rgba(255,210,30,0.8)" },
};

// 별점(0.5~5.0) → 별/포스터 시각값. 별은 시안과 동일한 '헤일로+도트' 글로우.
// owner 모드면 색은 주인별, 공통작은 살짝 크게(강조).
function vis(rating, owner) {
  const t = Math.max(0, Math.min(1, (rating - 0.5) / 4.5));
  const ts = Math.pow(t, 1.8);                          // 고평점일수록 가속
  const useOwner = props.colorBy === "owner" && owner;
  // 색 티어(표시 10점 기준): 9~10 노랑 / 7~8 초록 / 5~6 짙은 빨강 / 그 아래 흰색
  const p = useOwner ? OWNER_PALETTE[owner]
    : rating >= 4.5 ? STAR_PALETTE.gold
      : rating >= 3.5 ? STAR_PALETTE.teal
        : rating >= 2.5 ? STAR_PALETTE.alabaster
          : STAR_PALETTE.white;
  const r = (2.5 + ts * 2.0) * (useOwner && owner === "shared" ? 1.2 : 1);  // 도트 반경(시안 ~3.6, 평점가변)
  return {
    color: p.c, glow: p.g, r, haloR: r * 3.2,           // 별(도트+헤일로)
    op: 0.5 + t * 0.5, bright: rating >= 4.5,
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
    // 와이드 웹 캔버스를 가로로 꽉 채운다 — x·y 각각 프레임에 맞춰 독립 스케일(별자리가 좌우로
    // 길게 퍼져 가운데 뭉침·좌우 여백이 사라짐). 좌표 자체는 전역 고정(불변식), 표시 스케일만 조정.
    const sx = (W - 2 * PAD) / (2 * rx);
    const sy = (H - 2 * PAD) / (2 * ry);
    return { cx: 0, cy: 0, sx, sy };
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
    const v = vis(w.rating, w.owner);
    let [px, py] = project(w.x, w.y, t);   // 화면 y는 아래로 + → project가 부호 뒤집음
    const [bx, by] = [px, py];
    const sep = v.r + 5;   // 겹침 분산 간격(별 반경 기준)
    for (let k = 0; placed.some((p) => Math.hypot(p.px - px, p.py - py) < sep) && k < 16; k++) {
      const ang = k * 2.39996, rad = sep + k * 1.6;
      px = bx + Math.cos(ang) * rad;
      py = by + Math.sin(ang) * rad;
    }
    placed.push({ px, py });
    return { ...w, px, py, ...v };
  });
});
// 별자리 연결선(별 모드) — 7점 이상(rating ≥ 3.5)이면서 '가까운'(같은 장르 대륙권) 별끼리만 잇는다.
// 각자 최근접 1개와 잇되, 그 거리가 임계값을 넘으면(다른 장르) 잇지 않는다. 쌍 중복 제거.
const starLinks = computed(() => {
  if (props.colorBy === "owner") return [];   // 친구 비교 모드: 두 사람 별을 섞어 잇지 않음
  const ms = markers.value.filter((m) => m.rating >= 3.5);
  if (ms.length < 2) return [];
  const maxD2 = (Math.min(W, H) * 0.16) ** 2;  // 이 거리 안의 별끼리만(=비슷한 장르). 넘으면 끊음
  const seen = new Set();
  const out = [];
  ms.forEach((a, i) => {
    let best = -1, bd = Infinity;
    ms.forEach((b, j) => {
      if (i === j) return;
      const d = (a.px - b.px) ** 2 + (a.py - b.py) ** 2;
      if (d < bd) { bd = d; best = j; }
    });
    if (best < 0 || bd > maxD2) return;   // 최근접조차 너무 멀면(장르 다름) 연결 안 함
    const key = i < best ? `${i}-${best}` : `${best}-${i}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ x1: a.px, y1: a.py, x2: ms[best].px, y2: ms[best].py });
  });
  return out;
});
// 대륙(앵커) 라벨·영토 위치 — 마커와 같은 변환으로 투영.
function labelWidth(title) {
  return String(title || "").split("").reduce((sum, ch) => {
    const code = ch.charCodeAt(0);
    return sum + (code > 255 ? 12 : 7);
  }, 0) + 4;
}
function labelPriority(a, b) {
  const ratingDiff = Number(b.rating || 0) - Number(a.rating || 0);
  if (ratingDiff) return ratingDiff;
  const dateA = Date.parse(a.watched_on || a.created_at || "") || 0;
  const dateB = Date.parse(b.watched_on || b.created_at || "") || 0;
  if (dateA !== dateB) return dateB - dateA;
  return String(a.title || "").localeCompare(String(b.title || ""), "ko", { numeric: true });
}
function intersects(a, b) {
  return !(a.x2 < b.x1 || b.x2 < a.x1 || a.y2 < b.y1 || b.y2 < a.y1);
}
function circleIntersectsBox(c, box) {
  const x = Math.max(box.x1, Math.min(c.x, box.x2));
  const y = Math.max(box.y1, Math.min(c.y, box.y2));
  return (c.x - x) ** 2 + (c.y - y) ** 2 < c.r ** 2;
}
const starLabels = computed(() => {
  if (!props.showStarLabels) return [];
  const candidates = [...markers.value]
    .filter((m) => props.colorBy === "owner" ? m.owner === "shared" : m.bright)
    .sort(labelPriority);
  const placed = [];
  const out = [];
  const gap = 18;
  const h = 15;
  const pad = 2;
  const starBounds = markers.value.map((m) => ({
    id: m.movie_id,
    x: m.px,
    y: m.py,
    r: Math.max(m.r + 8, 11),
  }));

  for (const m of candidates) {
    const w = labelWidth(m.title);
    const cx = m.px;
    const cy = m.py;
    const positions = [
      { x: cx + m.r + gap, y: cy + 4, anchor: "start", rank: 0 },
      { x: cx - m.r - gap, y: cy + 4, anchor: "end", rank: 1 },
      { x: cx, y: cy - m.r - gap, anchor: "middle", rank: 2 },
      { x: cx, y: cy + m.r + gap + h, anchor: "middle", rank: 3 },
      { x: cx + m.r + gap, y: cy - m.r - gap, anchor: "start", rank: 4 },
      { x: cx - m.r - gap, y: cy - m.r - gap, anchor: "end", rank: 5 },
      { x: cx + m.r + gap, y: cy + m.r + gap + h, anchor: "start", rank: 6 },
      { x: cx - m.r - gap, y: cy + m.r + gap + h, anchor: "end", rank: 7 },
    ];
    const choices = positions.map((p) => {
      const box = p.anchor === "start"
        ? { x1: p.x - pad, x2: p.x + w + pad, y1: p.y - h + pad, y2: p.y + pad }
        : p.anchor === "end"
          ? { x1: p.x - w - pad, x2: p.x + pad, y1: p.y - h + pad, y2: p.y + pad }
          : { x1: p.x - w / 2 - pad, x2: p.x + w / 2 + pad, y1: p.y - h + pad, y2: p.y + pad };
      if (box.x1 < 0 || box.x2 > W || box.y1 < 0 || box.y2 > H) return false;
      if (placed.some((b) => intersects(box, b))) return false;
      const overlaps = starBounds
        .filter((s) => s.id !== m.movie_id && circleIntersectsBox(s, box))
        .length;
      return { ...p, box, score: overlaps * 20 + p.rank };
    }).filter(Boolean).sort((a, b) => a.score - b.score);
    const hit = choices[0];
    if (hit) {
      placed.push(hit.box);
      out.push({ ...m, labelX: hit.x, labelY: hit.y, labelAnchor: hit.anchor });
    }
  }
  return out;
});
const anchorMarkers = computed(() => {
  const t = transform.value;
  return (props.anchors || []).map((a) => {
    const [px, py] = project(a.x, a.y, t);
    return { name: a.name, px, py };
  });
});
// 지도 탐색(4.4) 추천 핀.
//  · safe       : 가장 가까운 본 영화 별 주위를 천천히 공전(빙빙) → 호버하면 멈춰서 좌표(툴팁) 표시.
//  · unexplored : 좌표에 고정된 번호 핀.  · rec(AI) : 좌표에 보라 링.
const hoveredOrbit = ref(null);
function pinVisual(m, px, py) {
  const safe = m.kind === "safe";
  const rec = m.kind === "rec";
  return { ...m, px, py, rec,
    fill: rec ? "#cbb6ff" : safe ? "#5bc5ff" : "#ff9d2e", textColor: safe ? "#07283a" : "#241a07" };
}
// safe 제외 정적 핀(좌표 고정). 미탐색끼리 좌표가 비슷해 겹치면 황금각 나선으로 분산(기존 방식).
const STATIC_SEP = 30;
const staticPins = computed(() => {
  if (!props.pins?.length) return [];
  const t = transform.value;
  const placed = [];
  return props.pins.filter((m) => m.kind !== "safe").map((m) => {
    const [bx, by] = project(m.x, m.y, t);
    let px = bx, py = by;
    for (let k = 0; placed.some((p) => Math.hypot(p.px - px, p.py - py) < STATIC_SEP) && k < 24; k++) {
      const ang = k * 2.39996, rad = STATIC_SEP + k * 4;   // 황금각(≈137.5°) 나선
      px = bx + Math.cos(ang) * rad;
      py = by + Math.sin(ang) * rad;
    }
    placed.push({ px, py });
    return pinVisual(m, px, py);
  });
});
// safe 추천 — 가장 가까운 본 영화 별별로 묶어 그 별 주위를 공전.
//  핀은 '실제 좌표(bx,by)'에 그리고, 공전은 transform translate 로 변위 → 호버 시 변위 0(=제자리 복귀·정지).
const SAFE_DUR = 18;   // 한 바퀴 공전 시간(초)
const CLUSTER_R = 46;   // 이 거리(viewBox) 안의 safe 추천은 한 궤도로 묶음
const HOME_SEP = 30;    // 호버 시 '제자리'가 겹치지 않도록 황금각 분산 간격(클릭 가능하게)
const orbitSystems = computed(() => {
  const safe = (props.pins || []).filter((m) => m.kind === "safe");
  const stars = markers.value;
  if (!safe.length || !stars.length) return [];
  const t = transform.value;

  // 각 safe: 실제 좌표 + 최근접 별 + 호버 시 '제자리'(겹치면 황금각 나선으로 분산해 클릭 가능).
  const placed = [];
  const nodes = safe.map((m) => {
    const [bx, by] = project(m.x, m.y, t);
    let star = stars[0], sd = Infinity;
    for (const s of stars) {
      const d = Math.hypot(s.px - bx, s.py - by);
      if (d < sd) { sd = d; star = s; }
    }
    let hx = bx, hy = by;
    for (let k = 0; placed.some((p) => Math.hypot(p.hx - hx, p.hy - hy) < HOME_SEP) && k < 24; k++) {
      const ang = k * 2.39996, rad = HOME_SEP + k * 4;   // 황금각 나선
      hx = bx + Math.cos(ang) * rad;
      hy = by + Math.sin(ang) * rad;
    }
    placed.push({ hx, hy });
    return { m, bx, by, hx, hy, starId: star.movie_id };
  });

  // union-find: 좌표 근접(궤도 교차 방지) 또는 같은 최근접 별(같은 원에 겹쳐 돎 방지)이면 한 궤도로.
  const parent = nodes.map((_, i) => i);
  const find = (x) => { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; };
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (nodes[i].starId === nodes[j].starId
        || Math.hypot(nodes[i].bx - nodes[j].bx, nodes[i].by - nodes[j].by) < CLUSTER_R) {
        parent[find(i)] = find(j);
      }
    }
  }
  const comps = new Map();
  nodes.forEach((nd, i) => {
    const r = find(i);
    if (!comps.has(r)) comps.set(r, []);
    comps.get(r).push(nd);
  });

  // 묶음마다 '평균에 가장 가까운 별'을 궤도 중심으로 정한 뒤,
  // 중심 별이 같은 묶음끼리 다시 합친다 — 같은 별을 같은 반경으로 돌아 딱 겹쳐 도는 일 방지(핵심).
  const byCenter = new Map();
  for (const items of comps.values()) {
    const mx = items.reduce((a, p) => a + p.bx, 0) / items.length;
    const my = items.reduce((a, p) => a + p.by, 0) / items.length;
    let star = stars[0], sd = Infinity;
    for (const s of stars) {
      const d = Math.hypot(s.px - mx, s.py - my);
      if (d < sd) { sd = d; star = s; }
    }
    if (!byCenter.has(star.movie_id)) byCenter.set(star.movie_id, { star, items: [] });
    byCenter.get(star.movie_id).items.push(...items);
  }

  // 중심별마다: 멤버 수에 맞춰 '안 겹치는' 반경에 고루 배치.
  let ci = 0;
  return [...byCenter.values()].map(({ star, items }) => {
    const n = items.length;
    // 이웃 핀 간격이 핀 지름(≈26)+여유를 넘도록: 2·R·sin(π/n) ≥ 36 → R = 18/sin(π/n).
    const R = Math.max(26, Math.ceil(18 / Math.sin(Math.PI / Math.max(n, 2))));
    let maxHome = 0;
    for (const nd of items) maxHome = Math.max(maxHome, Math.hypot(nd.hx - star.px, nd.hy - star.py));
    const hitR = Math.max(R, maxHome) + 18;   // 호버 캐처: 공전 궤도 + 흩어진 제자리까지 덮음
    const pins = items.map((nd, i) => ({
      ...pinVisual(nd.m, nd.hx, nd.hy),   // 그리는 위치 = 제자리(호버 시 여기). 공전은 transform.
      baseAngle: (i / n) * Math.PI * 2,   // 원주 분산용 시작 각
    }));
    return { id: `${star.movie_id}-${ci++}`, cx: star.px, cy: star.py, R, hitR, pins };
  });
});
// 공전 위상(rAF 누적). 호버 중인 묶음 핀은 변위 0(제자리 정지), 나머지는 별 주위로 변위.
const orbitT = ref(0);
let orbitRaf = null, orbitLast = 0;
function orbitTick(ts) {
  if (orbitLast) orbitT.value = (orbitT.value + ((ts - orbitLast) / 1000) * (2 * Math.PI / SAFE_DUR)) % (2 * Math.PI);
  orbitLast = ts;
  orbitRaf = requestAnimationFrame(orbitTick);
}
function pinTransform(sys, pin) {
  if (hoveredOrbit.value === sys.id) return "translate(0px,0px)";   // 실제 좌표로 복귀(정지)
  const a = pin.baseAngle + orbitT.value;
  const dx = sys.cx + sys.R * Math.cos(a) - pin.px;
  const dy = sys.cy + sys.R * Math.sin(a) - pin.py;
  return `translate(${dx.toFixed(2)}px,${dy.toFixed(2)}px)`;
}

const selected = computed(() => markers.value.find((m) => m.movie_id === selectedId.value) || null);
const highlighted = computed(() => markers.value.find((m) => m.movie_id === props.highlightId) || null);

function ringR(m) {
  return m.r + 9;
}
// 비교 지도 강조(owner 모드): 선택된 owner 별은 크게·밝게·펄스, 나머지는 흐리게.
const anyTwinkle = computed(() => props.colorBy === "owner" && props.twinkleOwners.length > 0);
const isEmph = (m) => props.colorBy === "owner" && props.twinkleOwners.includes(m.owner);
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
// 지도 빈 곳(별·핀 아닌 배경) 클릭 → 선택·찾기 하이라이트 모두 해제. 드래그 팬이면 무시.
function onBackdropClick() {
  if (panMoved.value) return;
  if (selectedId.value !== null) {
    selectedId.value = null;
    emit("select", null);
  }
  if (props.highlightId !== null) emit("clear-highlight");
}
function onHover(m, e) {
  if (!props.interactive) return;
  hovered.value = { marker: m, x: e.clientX, y: e.clientY };
  placeTip();
}
function onPinHover(m, e) {
  hovered.value = { marker: m, x: e.clientX, y: e.clientY, pin: true };   // 핀=추천(평점 10점)
  placeTip();
}
function onPinClick(m) {
  if (panMoved.value) return;   // 드래그-줌이었으면 핀 클릭(상세 이동) 무시
  emit("pin-click", m);
}
function poster(p) {
  return p ? IMG + p : "";
}

// ── 선택/찾기한 별의 '고정 카드'(상세보기 포함)와 호버 툴팁을 별/커서 '위쪽'에 띄우고,
//    지도 경계를 벗어나면 아래로 뒤집거나(flip) 좌우로 클램프(예외처리). ──
const pinnedMarker = computed(() =>           // 클릭 선택 또는 찾기-하이라이트면 그 별의 카드를 띄움
  props.interactive ? (selected.value || highlighted.value) : null);
const cardEl = ref(null);
const cardStyle = ref(null);
const tipEl = ref(null);
const tipStyle = ref(null);

// 앵커(ax,ay, 화면 px) 위쪽 중앙에 el을 놓되, 지도(svg) 경계를 넘으면 예외처리.
function floatPos(ax, ay, el, gap) {
  const rect = svgEl.value?.getBoundingClientRect();
  if (!el || !rect) return null;
  const w = el.offsetWidth, h = el.offsetHeight, pad = 8;
  const left = Math.max(rect.left + pad, Math.min(ax - w / 2, rect.right - w - pad));  // 좌우 클램프
  let top = ay - gap - h;                                  // 기본: 위쪽
  if (top < rect.top + pad) top = ay + gap;                // 위로 넘침(최상단 별) → 아래로 뒤집기
  top = Math.max(rect.top + pad, Math.min(top, rect.bottom - h - pad));               // 상하 클램프
  return { left: `${left}px`, top: `${top}px` };
}
// 별 viewBox 좌표 → 화면 px (줌/팬 변환 반영). r은 화면상 별 반경.
function markerScreen(m) {
  const rect = svgEl.value?.getBoundingClientRect();
  if (!m || !rect) return null;
  const z = zoom.value, cx = W / 2, cy = H / 2;
  const vx = m.px * z + pan.value.x + cx * (1 - z);
  const vy = m.py * z + pan.value.y + cy * (1 - z);
  return {
    x: rect.left + (vx / W) * rect.width,
    y: rect.top + (vy / H) * rect.height,
    r: m.r * z * (rect.width / W),
  };
}
function placeCard() {
  const m = pinnedMarker.value;
  if (!m) { cardStyle.value = null; return; }
  nextTick(() => {
    const a = markerScreen(m);
    cardStyle.value = a && cardEl.value ? floatPos(a.x, a.y - a.r, cardEl.value, 12) : null;
  });
}
function placeTip() {
  const h = hovered.value;
  if (!h) { tipStyle.value = null; return; }
  nextTick(() => {
    tipStyle.value = h && tipEl.value ? floatPos(h.x, h.y, tipEl.value, 16) : null;
  });
}
function goDetail() {
  if (pinnedMarker.value) emit("open-detail", pinnedMarker.value);
}
watch([pinnedMarker, zoom, pan], placeCard, { deep: true });
onMounted(() => {
  window.addEventListener("resize", placeCard);
  if (props.interactive) orbitRaf = requestAnimationFrame(orbitTick);   // safe 추천 공전 루프
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", placeCard);
  cancelAnimationFrame(orbitRaf);
});

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
        <!-- 시안(Carbon) 도트 텍스처(28px 격자) — grid-tex 와 동일 -->
        <pattern
          id="dotgrid"
          width="28"
          height="28"
          patternUnits="userSpaceOnUse"
        >
          <circle
            cx="1"
            cy="1"
            r="1"
            fill="rgba(255,255,255,0.05)"
          />
        </pattern>
        <!-- 웜 비네트(골드/틸) — 시안 프레임 글로우를 SVG 안에 재현 -->
        <radialGradient
          id="vigGold"
          cx="35%"
          cy="25%"
          r="65%"
        >
          <stop
            offset="0%"
            stop-color="#E6B566"
            stop-opacity="0.10"
          />
          <stop
            offset="55%"
            stop-color="#E6B566"
            stop-opacity="0"
          />
        </radialGradient>
        <radialGradient
          id="vigTeal"
          cx="85%"
          cy="105%"
          r="60%"
        >
          <stop
            offset="0%"
            stop-color="#5DCAA5"
            stop-opacity="0.07"
          />
          <stop
            offset="50%"
            stop-color="#5DCAA5"
            stop-opacity="0"
          />
        </radialGradient>
      </defs>

      <!-- 정적 배경(줌/팬과 무관): 잉크색 + 도트 텍스처 + 웜 비네트 (시안 프레임과 동일) -->
      <rect
        :width="W"
        :height="H"
        fill="#0C0C0F"
      />
      <rect
        :width="W"
        :height="H"
        fill="url(#dotgrid)"
      />
      <rect
        :width="W"
        :height="H"
        fill="url(#vigGold)"
      />
      <rect
        :width="W"
        :height="H"
        fill="url(#vigTeal)"
      />
      <!-- 배경 별밭(장식) — 본 영화 별 뒤로 흩뿌린 작은 별들. 영화 마커가 아니라 순수 배경 앰비언스 -->
      <g style="pointer-events: none">
        <circle
          v-for="(s, i) in FIELD"
          :key="`fs${i}`"
          :cx="s.x"
          :cy="s.y"
          :r="s.r"
          :fill="s.color"
          opacity="0.6"
          :class="{ twinkle: s.twinkle }"
          :style="s.twinkle ? { animationDelay: s.delay } : null"
        />
      </g>

      <!-- 확대/축소·팬 대상: 배경 rect를 뺀 모든 데이터/장식 레이어를 한 그룹으로 변환 (item 1) -->
      <g :transform="viewTransform">
      <!-- 빈 곳 클릭 캐처: 별·핀 아닌 배경 클릭 시 선택 해제(별·핀은 위에 그려져 클릭 가로챔) -->
      <rect
        v-if="interactive"
        :x="-W"
        :y="-H"
        :width="W * 3"
        :height="H * 3"
        fill="transparent"
        @click="onBackdropClick"
      />
      <!-- 장르 대륙 글로우(별 뒤). 별·포스터 모드 공통(A-14). -->
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

      <!-- 대륙(장르) 글자 — 토글로 표시. 별 뒤에 옅게(클릭 영향 없음). -->
      <g
        v-if="showGenreLabels && anchorMarkers.length"
        class="genrelabels"
      >
        <text
          v-for="a in anchorMarkers"
          :key="`gl${a.name}`"
          :x="a.px"
          :y="a.py"
          class="genrelabel"
        >{{ a.name }}</text>
      </g>

      <!-- ===== 본 영화 별 ===== -->
      <!-- 별자리 연결선(시안과 동일) — 별 뒤에 옅게 -->
      <line
        v-for="(l, i) in starLinks"
          :key="`lnk${i}`"
          :x1="l.x1"
          :y1="l.y1"
          :x2="l.x2"
          :y2="l.y2"
          stroke="rgba(255,255,255,0.32)"
          stroke-width="1.4"
          style="pointer-events: none"
        />
        <!-- 본 영화 = 빛나는 별: 글로우 헤일로 + 도트 (별점 = 크기·색 티어, 시안과 동일). -->
        <g
          v-for="m in markers"
          :key="m.movie_id"
          class="star"
          :class="{ 'star--live': interactive }"
          :style="{ opacity: anyTwinkle && !isEmph(m) ? 0.14 : 1 }"
          @click="onSelect(m)"
          @mouseenter="onHover(m, $event)"
          @mousemove="onHover(m, $event)"
          @mouseleave="hovered = null"
        >
          <circle
            :cx="m.px"
            :cy="m.py"
            :r="isEmph(m) ? m.haloR * 1.5 : m.haloR"
            :fill="m.glow"
            :opacity="isEmph(m) ? 0.5 : 0.16"
            style="pointer-events: none"
          />
          <circle
            :cx="m.px"
            :cy="m.py"
            :r="isEmph(m) ? m.r * 1.9 : m.r"
            :fill="m.color"
            :fill-opacity="isEmph(m) ? 1 : m.op"
            :class="{ twinkle: (m.bright && selectedId !== m.movie_id) || isEmph(m) }"
            style="pointer-events: none"
          />
          <!-- 강조 펄스 링(owner 토글 켰을 때) -->
          <circle
            v-if="isEmph(m)"
            :cx="m.px"
            :cy="m.py"
            :r="m.r * 1.9 + 7"
            fill="none"
            :stroke="m.color"
            stroke-width="2"
            class="blink"
            style="pointer-events: none"
          />
          <!-- 작은 도트도 잘 눌리도록 투명 히트 타깃 -->
          <circle
            :cx="m.px"
            :cy="m.py"
            :r="Math.max((isEmph(m) ? m.r * 1.9 : m.r) + 6, 11)"
            fill="transparent"
          />
        </g>
        <!-- 제목 라벨 — 평점 모드: 고평점 별 / owner(친구 비교) 모드: 공통 시청작만(너무 많지 않게) -->
        <text
          v-for="m in starLabels"
          :key="`lbl${m.movie_id}`"
          :x="m.labelX"
          :y="m.labelY"
          :text-anchor="m.labelAnchor"
          class="starlabel"
        >{{ m.title }}</text>

      <!-- 지도 탐색(4.4) 정적 추천 핀(unexplored·AI). safe 는 아래 공전으로. -->
      <g
        v-for="m in staticPins"
        :key="`pin${m.id}`"
        class="pinmk"
        @click="onPinClick(m)"
        @mouseenter="onPinHover(m, $event)"
        @mousemove="onPinHover(m, $event)"
        @mouseleave="hovered = null"
      >
        <!-- AI 추천(rec): 보라 링 + 도트(번호 없음) / 미탐색: 번호 핀 -->
        <template v-if="m.rec">
          <circle
            :cx="m.px"
            :cy="m.py"
            r="14"
            fill="none"
            stroke="#a884ff"
            stroke-width="2"
          />
          <circle
            :cx="m.px"
            :cy="m.py"
            r="4"
            fill="#cbb6ff"
          />
        </template>
        <template v-else>
          <circle
            :cx="m.px"
            :cy="m.py"
            r="13"
            :fill="m.fill"
            filter="url(#glow)"
          />
          <text
            :x="m.px"
            :y="m.py + 3.5"
            :fill="m.textColor"
            font-size="10.5"
            font-weight="700"
            text-anchor="middle"
            style="pointer-events: none"
          >#{{ m.num }}</text>
        </template>
      </g>

      <!-- safe 추천: 평소엔 가까운 별 주위를 공전, 호버하면 실제 좌표로 돌아가 정지(클릭=상세). -->
      <g
        v-for="sys in orbitSystems"
        :key="`orb${sys.id}`"
        class="orbitsys"
        @mouseenter="hoveredOrbit = sys.id"
        @mouseleave="hoveredOrbit = null"
      >
        <!-- 호버 진입 감지용 공전 띠(평소엔 중심 별 클릭 유지) -->
        <circle
          :cx="sys.cx"
          :cy="sys.cy"
          :r="sys.R"
          fill="none"
          stroke="transparent"
          stroke-width="30"
          style="pointer-events: stroke"
        />
        <!-- 호버 중에만 활성화되는 전체 원: 제자리로 모인 핀까지 덮어 호버 유지(교체 없이 토글) -->
        <circle
          :cx="sys.cx"
          :cy="sys.cy"
          :r="sys.hitR"
          fill="transparent"
          :style="{ pointerEvents: hoveredOrbit === sys.id ? 'fill' : 'none' }"
        />
        <g
          v-for="m in sys.pins"
          :key="`op${m.id}`"
          class="orbit"
          :style="{ transform: pinTransform(sys, m) }"
          @click.stop="onPinClick(m)"
          @mouseenter="onPinHover(m, $event)"
          @mousemove="onPinHover(m, $event)"
          @mouseleave="hovered = null"
        >
          <circle
            :cx="m.px"
            :cy="m.py"
            r="13"
            :fill="m.fill"
            filter="url(#glow)"
          />
          <text
            :x="m.px"
            :y="m.py + 3.5"
            :fill="m.textColor"
            font-size="10.5"
            font-weight="700"
            text-anchor="middle"
            style="pointer-events: none"
          >#{{ m.num }}</text>
        </g>
      </g>

      <!-- 선택 표시: 시안과 동일한 금빛 링(별 위에 한 번 더 그려 '앞으로' — 겹쳐 가려도 보이게).
           pointer-events:none → 밑의 원본 별이 그대로 클릭(재클릭=해제)을 받는다. 포스터는 테두리 강조. -->
      <g
        v-if="interactive && selected"
        style="pointer-events: none"
      >
        <circle
          :cx="selected.px"
          :cy="selected.py"
          :r="selected.haloR"
          :fill="selected.glow"
          opacity="0.22"
        />
        <circle
          :cx="selected.px"
          :cy="selected.py"
          :r="selected.r + 1"
          :fill="selected.color"
        />
        <circle
          :cx="selected.px"
          :cy="selected.py"
          :r="Math.max(selected.r + 7, 11)"
          fill="none"
          stroke="#E6B566"
          stroke-width="1.4"
          opacity="0.9"
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

    <!-- 커서 위쪽 호버 툴팁 (별점 10점 표기). 고정 카드가 떠 있는 별은 중복 표시 안 함 -->
    <div
      v-if="interactive && hovered && hovered.marker !== pinnedMarker"
      ref="tipEl"
      class="tip"
      :style="[tipStyle, { visibility: tipStyle ? 'visible' : 'hidden' }]"
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
          <template v-if="hovered.marker.kind === 'rec'">
            <b style="color: #cbb6ff">AI 추천</b> · 같이 볼 영화
          </template>
          <template v-else-if="hovered.pin">
            <b
              v-if="hovered.marker.kind === 'safe'"
              style="color: #5bc5ff"
            >가까운 취향 #{{ hovered.marker.num }}</b><b
              v-else-if="hovered.marker.kind === 'unexplored'"
              style="color: #ff9d2e"
            >새로운 취향 #{{ hovered.marker.num }}</b>
            · {{ hovered.marker.release_year || "" }} · ★ {{ hovered.marker.vote_average }} / 10
          </template>
          <template v-else-if="hovered.marker.owner === 'shared'">
            둘 다 봄 · 나 ★{{ hovered.marker.myRating * 2 }} / {{ friendName }} ★{{ hovered.marker.friendRating * 2 }} / 10
          </template>
          <template v-else-if="hovered.marker.owner === 'mine'">
            나만 봄 · ★{{ hovered.marker.myRating * 2 }} / 10
          </template>
          <template v-else-if="hovered.marker.owner === 'theirs'">
            {{ friendName }}만 봄 · ★{{ hovered.marker.friendRating * 2 }} / 10
          </template>
          <template v-else>
            {{ hovered.marker.release_year || "" }} · ★ {{ hovered.marker.rating * 2 }} / 10
          </template>
        </div>
      </div>
    </div>

    <!-- 선택/찾기한 영화 '고정 카드' — 별 위에 떠서 상세보기까지 바로(커서 이동 최소화).
         지도 밖으로 나가면 floatPos가 아래로 뒤집거나 좌우 클램프(예외처리). -->
    <div
      v-if="interactive && pinnedMarker"
      ref="cardEl"
      class="pincard"
      :style="[cardStyle, { visibility: cardStyle ? 'visible' : 'hidden' }]"
    >
      <div class="pincard__poster">
        <img
          v-if="poster(pinnedMarker.poster_path)"
          :src="poster(pinnedMarker.poster_path)"
          :alt="pinnedMarker.title"
        >
      </div>
      <div class="pincard__meta">
        <div class="pincard__title">
          {{ pinnedMarker.title }}
        </div>
        <div class="pincard__year">
          {{ pinnedMarker.release_year || "" }}
        </div>
        <div class="pincard__rating">
          <template v-if="pinnedMarker.owner === 'shared'">
            나 ★{{ pinnedMarker.myRating * 2 }} · {{ friendName }} ★{{ pinnedMarker.friendRating * 2 }}
          </template>
          <template v-else-if="pinnedMarker.owner === 'mine'">
            ★ {{ pinnedMarker.myRating * 2 }} / 10
          </template>
          <template v-else-if="pinnedMarker.owner === 'theirs'">
            ★ {{ pinnedMarker.friendRating * 2 }} / 10
          </template>
          <template v-else>
            ★ {{ pinnedMarker.rating * 2 }} / 10
          </template>
        </div>
        <button
          type="button"
          class="pincard__btn"
          @click="goDetail"
        >
          상세 보기
        </button>
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
.genrelabels {
  pointer-events: none;
}
.genrelabel {
  fill: rgba(236, 237, 241, 0.42);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-anchor: middle;
  font-family: var(--font);
}
.starlabel {
  fill: rgba(236, 237, 241, 0.55);
  font-size: 12px;
  font-family: "Pretendard", sans-serif;
  pointer-events: none;
}
.star--live {
  cursor: pointer;
  transition: fill-opacity 0.15s;
}
.pinmk {
  cursor: pointer;
}
.pinmk:hover circle {
  filter: brightness(1.25);
}
/* safe 추천 공전 — 위치는 JS(transform translate)가 매 프레임 갱신. transition 으로 부드럽게 따라가고,
   묶음에 호버하면 변위가 0이 되며 실제 좌표로 부드럽게 복귀해 정지. */
.orbitsys {
  cursor: pointer;
}
.orbit {
  transition: transform 0.3s ease-out;
}
.orbit:hover circle {
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

/* 선택/찾기한 영화 고정 카드 (상세보기 포함, 클릭 가능) */
.pincard {
  position: fixed;
  z-index: 50;
  display: flex;
  gap: 10px;
  padding: 10px;
  width: 232px;
  background: rgba(14, 16, 24, 0.97);
  border: 1px solid #2c3142;
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.55);
}
.pincard__poster {
  width: 54px;
  flex: none;
  aspect-ratio: 2 / 3;
  border-radius: 4px;
  overflow: hidden;
  background: #222838;
}
.pincard__poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.pincard__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.pincard__title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.3;
}
.pincard__year {
  margin-top: 2px;
  font-size: 11px;
  color: var(--text-muted);
}
.pincard__rating {
  margin-top: 4px;
  font-size: 12px;
  color: #e6b566;
}
.pincard__btn {
  margin-top: 8px;
  align-self: flex-start;
  padding: 5px 12px;
  border: 1px solid #2c3142;
  border-radius: 6px;
  background: none;
  color: var(--text);
  font-family: var(--font);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.pincard__btn:hover {
  border-color: #e6b566;
}
</style>
