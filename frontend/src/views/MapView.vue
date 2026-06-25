<script setup>
// 취향 지도 페이지 (F-MAP, 김호준) — 4개 내부 탭의 셸 + '취향 지도' 탭.
// 지도 렌더는 <TasteMapCanvas>(홈 프리뷰와 공유). 여기선 탭·게이트·범례·선택 패널 담당.
// (KDE 탐색도 영역·영역 클릭=4.4, 검색 반짝=3.4 → 해당 탭에서.)
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getMyMap, getExplore } from "@/api/taste";
import { searchMovies, browseMovies, getMovie } from "@/api/movies";
import TasteMapCanvas from "@/components/TasteMapCanvas.vue";
import WatchRecordModal from "@/components/WatchRecordModal.vue";
import WatchRecordsList from "@/components/WatchRecordsList.vue";

const router = useRouter();
const route = useRoute();
const TABS = [
  { key: "map", label: "취향 지도" },
  { key: "records", label: "시청 영화 목록" },
  { key: "search", label: "영화 검색·등록" },
  { key: "explore", label: "지도 탐색" },
];
const TAB_KEYS = TABS.map((t) => t.key);
// 탭 상태를 URL ?tab= 에 보존 → 새로고침·뒤로가기에도 유지
const activeTab = ref(TAB_KEYS.includes(route.query.tab) ? route.query.tab : "map");
function setTab(key) {
  activeTab.value = key;
  router.replace({ query: { ...route.query, tab: key } });
}

// 대륙(장르) 글자 표시 토글 (취향 지도 탭)
const showGenre = ref(false);

const loading = ref(true);
const error = ref("");
const data = ref(null);          // { enough, watched:[...] }
const IMG = "https://image.tmdb.org/t/p/w185";

// 지도 내 검색(반짝, 3.4): 본 영화 제목 매칭 → 그 별 반짝
const findQuery = ref("");
const highlightId = ref(null);

// 영화 검색·등록 탭(3.4)
const searchQuery = ref("");
const searchResults = ref([]);
const searched = ref(false);
const searching = ref(false);
const searchError = ref("");
const regMovie = ref(null);      // 등록 모달에 넘길 영화(있으면 모달 열림)
const regRecord = ref(null);     // 그 영화의 내 시청기록(있으면 수정 모드 + 기존 리뷰 채움)

onMounted(async () => {
  try {
    data.value = await getMyMap();
  } catch {
    error.value = "지도를 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
});

function poster(p) {
  return p ? IMG + p : "";
}
// 지도 위 고정 카드의 '상세 보기' → 그 별의 영화 상세로 (캔버스가 open-detail emit)
function goDetail(m) {
  router.push({ name: "movie-detail", params: { id: m.movie_id } });
}
function goRegister() {
  setTab("search");
}

// 본 영화 목록 자동완성(in-memory 필터 — 매우 가벼움) → 선택하면 그 별 반짝
// 제목순 정렬(localeCompare, numeric: '아이언맨 2' < '아이언맨 10' 자연정렬). filter가 새 배열이라 sort 안전.
const findMatches = computed(() => {
  const q = findQuery.value.trim().toLowerCase();
  if (!q) return [];
  return data.value.watched
    .filter((w) => w.title.toLowerCase().includes(q))
    .sort((a, b) => a.title.localeCompare(b.title, "ko", { numeric: true }))
    .slice(0, 8);
});
const showFind = ref(false);
function onFindInput() {
  showFind.value = findQuery.value.trim().length > 0;
  if (!findQuery.value.trim()) highlightId.value = null;
}
function onFindBlur() {
  setTimeout(() => { showFind.value = false; }, 120);   // 항목 클릭이 먼저 처리되도록 약간 지연
}
function onPickFind(m) {
  highlightId.value = m.movie_id;   // 그 별 반짝 + 지도 위 고정 카드 표시(canvas)
  findQuery.value = m.title;
  showFind.value = false;
}
function onFindEnter() {
  if (findMatches.value.length) onPickFind(findMatches.value[0]);   // 첫 매칭 선택
}
// 지도 빈 곳 클릭(캔버스 emit) → 찾기 하이라이트·고정 카드 해제
function onFindClear() {
  highlightId.value = null;
}

// 검색·등록 탭: 검색어 없으면 전체 목록(평점순)을, 있으면 제목 검색을 보여준다.
// → 영화 검색 페이지처럼 검색하지 않아도 전체 영화를 스크롤하며 등록 가능 (item 3).
async function onSearch() {
  searching.value = true;
  searchError.value = "";
  try {
    const q = searchQuery.value.trim();
    searchResults.value = q ? await searchMovies(q) : await browseMovies({});
    searched.value = true;
  } catch {
    searchError.value = "검색에 실패했습니다.";
  } finally {
    searching.value = false;
  }
}
// 탭을 처음 열 때 전체 목록을 1회 미리 로드(검색 없이 바로 보이게).
const searchLoaded = ref(false);
watch(activeTab, async (tab) => {
  if (tab !== "search" || searchLoaded.value) return;
  searchLoaded.value = true;
  await onSearch();
}, { immediate: true });

// 검색 결과 클릭 → 상세를 조회해 내 시청기록(my_record)을 받고 모달을 연다.
// 이미 본 영화면 수정 모달(기존 별점·리뷰 채움), 안 본 영화면 등록 모달.
// ※ 모달은 setup에서 initialRecord를 1회만 읽으므로 record 확정 후에 마운트해야 한다.
async function onPickRegister(m) {
  try {
    const detail = await getMovie(m.id);
    regRecord.value = detail.my_record;   // null=신규 등록 / 있으면 수정
  } catch {
    regRecord.value = null;               // 조회 실패 시 등록 모드로 진행
  }
  regMovie.value = m;
}

// 등록 모달 저장 완료 → 닫고 지도 갱신(새 별·좌표·편수 반영)
async function onRegistered() {
  regMovie.value = null;
  regRecord.value = null;
  data.value = await getMyMap();
}

// 시청 목록 탭에서 수정·삭제 → 좌표/별 재계산 반영(탭 전환 시 stale 방지)
async function onRecordsChanged() {
  data.value = await getMyMap();
}

// ── 지도 탐색 탭(4.4, 와이어프레임 10·d/10·e) ──────────────────────
const exploreData = ref(null);     // { grid, watched, safe:[+x,y], unexplored:[+x,y] }
const exploreLoading = ref(false);
const exploreSub = ref("unexplored");     // 서브탭: 'unexplored' | 'safe'
const pinned = ref(new Set());            // [지도] 토글 켠 영화 id (둘 다 기본 ON)

// 탐색 탭을 처음 열 때만 로드(지연). data(취향 지도)와 분리 — getExplore가 자체 enough를 반환하므로
// data 로드를 기다릴 필요 없다. (data에 묶으면 ?tab=explore로 새로고침 시 data 도착 전 watch가
// 헛돌고 재실행 안 돼 무한 로딩됐다.) 게이트(5편 미만)는 exploreData.enough로 판단.
watch(activeTab, async (tab) => {
  if (tab !== "explore" || exploreData.value || exploreLoading.value) return;
  exploreLoading.value = true;
  try {
    const d = await getExplore();
    exploreData.value = d;
    if (d.enough) pinned.value = new Set([...d.safe, ...d.unexplored].map((m) => m.id));  // 기본 전부 핀
  } finally {
    exploreLoading.value = false;
  }
}, { immediate: true });

// 활성 서브탭의 추천 리스트(번호 매김 + 핀 색 kind) + 토글 켠 것만 핀
const exploreList = computed(() =>
  (exploreData.value?.[exploreSub.value] || []).map((m, i) => ({ ...m, num: i + 1, kind: exploreSub.value })));
const explorePins = computed(() => exploreList.value.filter((m) => pinned.value.has(m.id)));

function togglePin(id) {
  const s = new Set(pinned.value);
  s.has(id) ? s.delete(id) : s.add(id);
  pinned.value = s;
}
function exploreLabel(m) {
  return exploreSub.value === "safe"
    ? `가까운 취향 · 유사도 ${Math.max(0, 1 - m.distance).toFixed(2)}`
    : `새로운 취향 · ${m.continent || "새 취향"}`;
}
function onPickExploreMovie(m) {
  router.push({ name: "movie-detail", params: { id: m.id } });
}
</script>

<template>
  <div class="mx-auto max-w-[1500px] px-6 pb-28 pt-10 lg:px-10">
    <!-- ───────── PAGE HEADER ───────── -->
    <section class="mb-6 flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
      <div class="min-w-0 flex-1">
        <div class="mb-3 flex items-center gap-2.5 font-sans text-[11px] uppercase tracking-[0.14em] text-fg-muted">
          <span class="h-px w-7 bg-gold/60" />내 취향 지도 · Taste atlas
        </div>
        <h1 class="font-display text-[30px] font-semibold leading-[1.12] tracking-tightest sm:text-[40px]">
          별자리를 거닐며<br> <span class="text-fg-muted">취향의 좌표를</span> 읽어보세요
        </h1>
      </div>
      <p class="max-w-[300px] text-[13.5px] leading-relaxed text-fg-muted">
        밝을수록 높은 별점, 가까울수록 닮은 결.<br> 별을 누르면 그 영화의 좌표가 펼쳐집니다.
      </p>
    </section>

    <!-- ───────── INTERNAL TABS ───────── -->
    <div class="no-bar mb-6 flex items-center gap-1 overflow-x-auto border-b border-line">
      <button
        v-for="t in TABS"
        :key="t.key"
        type="button"
        class="relative shrink-0 px-4 py-2.5 text-[13.5px] font-medium transition"
        :class="activeTab === t.key ? 'text-fg' : 'text-fg-muted hover:text-fg'"
        @click="setTab(t.key)"
      >
        {{ t.label }}
        <span
          class="absolute inset-x-3 -bottom-px h-[2px] rounded-full bg-gold"
          :class="{ hidden: activeTab !== t.key }"
        />
      </button>
    </div>

    <!-- ═══════════════ PANEL: 취향 지도 ═══════════════ -->
    <template v-if="activeTab === 'map'">
      <p
        v-if="loading"
        class="py-16 text-center text-[14px] text-fg-muted"
      >
        지도를 그리는 중…
      </p>
      <p
        v-else-if="error"
        class="py-16 text-center text-[14px] text-danger"
      >
        {{ error }}
      </p>

      <!-- 5편 미만 게이트 -->
      <div
        v-else-if="!data.enough"
        class="mx-auto my-20 max-w-[460px] text-center"
      >
        <div class="font-display text-[19px] font-semibold tracking-tightest text-fg">
          아직 취향 지도를 그릴 수 없어요
        </div>
        <p class="mt-3 text-[14px] leading-[1.7] text-fg-muted">
          영화 <b class="text-fg">5편 이상</b>을 등록하면 나만의 취향 지도가 만들어집니다.<br>
          별점을 높게 준 영화일수록 더 밝게 빛나요.
        </p>
        <button
          type="button"
          class="mt-6 rounded-lg bg-gold px-6 py-2.5 text-[14px] font-semibold text-ink transition hover:bg-gold-soft"
          @click="goRegister"
        >
          영화 등록하러 가기
        </button>
      </div>

      <!-- 지도 -->
      <div
        v-else
        class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]"
      >
        <!-- map frame -->
        <div class="relative overflow-hidden rounded-2xl border border-line bg-ink-800">
          <div class="grid-tex pointer-events-none absolute inset-0 opacity-60" />
          <div
            class="pointer-events-none absolute inset-0"
            style="background:radial-gradient(110% 80% at 35% 25%, rgba(230,181,102,0.10), transparent 55%), radial-gradient(100% 110% at 85% 105%, rgba(93,202,165,0.07), transparent 50%);"
          />

          <!-- 대륙(장르) 글자 토글 -->
          <button
            type="button"
            class="absolute right-4 top-4 z-10 rounded-full border bg-ink-700/90 px-3.5 py-1.5 text-[12px] font-medium shadow-[0_2px_10px_rgba(0,0,0,0.5)] backdrop-blur transition"
            :class="showGenre ? 'border-gold/50 text-gold' : 'border-lineHover text-fg-muted hover:text-fg'"
            @click="showGenre = !showGenre"
          >
            장르 {{ showGenre ? "끄기" : "보기" }}
          </button>

          <TasteMapCanvas
            :watched="data.watched"
            :anchors="data.anchors"
            :width="980"
            :height="560"
            :highlight-id="highlightId"
            :show-genre-labels="showGenre"
            class="mapwrap relative block"
            @open-detail="goDetail"
            @clear-highlight="onFindClear"
          />

          <!-- legend -->
          <div class="relative flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line bg-ink-800/60 px-5 py-3.5 font-mono text-[11px] text-fg-muted backdrop-blur">
            <span class="flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-full bg-[#FFF0CD] shadow-[0_0_7px_#FFE6A8]" />인생작</span>
            <span class="flex items-center gap-1.5"><span class="h-1.5 w-1.5 rounded-full bg-[#5DCAA5]" />인상적</span>
            <span class="flex items-center gap-1.5"><span class="h-1.5 w-1.5 rounded-full bg-[#C9D0E0]" />무난함</span>
            <span class="hidden sm:inline text-fg-faint">·</span>
            <span class="text-fg-faint">모여 있을수록 비슷한 취향</span>
          </div>
        </div>

        <!-- sidebar -->
        <aside class="flex flex-col gap-3">
          <!-- count -->
          <div class="rounded-xl border border-line bg-ink-800 px-4 py-3.5 text-[13px] text-fg-muted">
            내가 본 영화 <b class="font-display text-fg">{{ data.watched.length }}</b>편 · 별자리에 흩어져 있어요
          </div>

          <!-- find -->
          <div class="relative rounded-xl border border-line bg-ink-800 p-4">
            <div class="font-sans text-[13px] font-semibold tracking-[0.02em] text-fg">
              내가 본 영화 찾기
            </div>
            <div class="mt-2.5 flex items-center gap-2 rounded-lg border border-line bg-ink-700 px-3 py-2 focus-within:border-lineHover">
              <svg
                viewBox="0 0 24 24"
                class="h-4 w-4 text-fg-faint"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
              ><circle
                cx="11"
                cy="11"
                r="7"
              /><path
                d="m20 20-3.2-3.2"
                stroke-linecap="round"
              /></svg>
              <input
                v-model="findQuery"
                type="text"
                placeholder="제목을 입력하세요."
                class="w-full bg-transparent text-[13px] text-fg placeholder:text-fg-faint focus:outline-none"
                @input="onFindInput"
                @focus="showFind = true"
                @blur="onFindBlur"
                @keyup.enter="onFindEnter"
              >
            </div>
            <ul
              v-if="showFind && findMatches.length"
              class="absolute inset-x-4 top-[calc(100%-6px)] z-20 max-h-[280px] overflow-y-auto rounded-lg border border-line bg-ink-800 p-1 shadow-[0_8px_24px_rgba(0,0,0,0.5)]"
            >
              <li
                v-for="m in findMatches"
                :key="m.movie_id"
              >
                <button
                  type="button"
                  class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition hover:bg-white/[0.05]"
                  @mousedown.prevent
                  @click="onPickFind(m)"
                >
                  <img
                    v-if="poster(m.poster_path)"
                    :src="poster(m.poster_path)"
                    :alt="m.title"
                    class="h-9 w-6 flex-none rounded-[2px] object-cover"
                  >
                  <span class="min-w-0 flex-1 truncate text-[13px] text-fg">{{ m.title }}</span>
                  <span class="flex-none text-[11.5px] text-fg-muted">{{ m.release_year || "" }}</span>
                </button>
              </li>
            </ul>
            <p
              v-else-if="findQuery && !findMatches.length"
              class="mt-2 text-[12px] text-fg-faint"
            >
              그 제목으로 본 영화가 없어요.
            </p>
          </div>

          <!-- taste summary -->
          <div
            v-if="data.summary"
            class="rounded-xl border border-line bg-ink-800 p-4"
          >
            <div class="font-sans text-[13px] font-semibold tracking-[0.02em] text-fg">
              내 취향 요약
            </div>
            <div class="mt-3 flex items-baseline justify-between gap-3 text-[13px]">
              <span class="text-fg-muted">내 선호 장르</span>
              <span class="font-medium text-fg">{{ data.summary.main.join(" · ") || "—" }}</span>
            </div>
            <div class="mt-2.5 flex items-baseline justify-between gap-3 text-[13px]">
              <span class="text-fg-muted">새로운 취향 장르</span>
              <span class="font-medium text-gold">{{ data.summary.unexplored.join(" · ") || "—" }}</span>
            </div>
          </div>
        </aside>
      </div>
    </template>

    <!-- ═══════════════ PANEL: 시청 영화 목록 ═══════════════ -->
    <WatchRecordsList
      v-else-if="activeTab === 'records'"
      @changed="onRecordsChanged"
    />

    <!-- ═══════════════ PANEL: 영화 검색·등록 ═══════════════ -->
    <!-- 기존(master) 구조: 검색 전 전체 포스터가 적응형 그리드로 우르르 → 클릭 시 등록 모달 -->
    <div v-else-if="activeTab === 'search'">
      <!-- search bar (full width) -->
      <div class="mb-4 flex gap-2.5">
        <div class="flex flex-1 items-center gap-2.5 rounded-xl border border-line bg-ink-800 px-4 py-3 transition focus-within:border-gold">
          <svg
            viewBox="0 0 24 24"
            class="h-[18px] w-[18px] text-fg-faint"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
          ><circle
            cx="11"
            cy="11"
            r="7"
          /><path
            d="m20 20-3.2-3.2"
            stroke-linecap="round"
          /></svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="영화 제목으로 검색해 별자리에 추가하세요"
            class="w-full bg-transparent text-[14px] text-fg placeholder:text-fg-faint focus:outline-none"
            @keyup.enter="onSearch"
          >
        </div>
        <button
          type="button"
          class="shrink-0 rounded-xl bg-gold px-6 text-[14px] font-semibold text-ink transition hover:bg-gold-soft"
          @click="onSearch"
        >
          검색
        </button>
      </div>

      <p
        v-if="searchError"
        class="py-10 text-center text-[14px] text-danger"
      >
        {{ searchError }}
      </p>
      <p
        v-else-if="searching"
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        검색 중…
      </p>
      <div
        v-else-if="searchResults.length"
        class="grid gap-[18px]"
        style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr))"
      >
        <button
          v-for="m in searchResults"
          :key="m.id"
          type="button"
          class="group/c text-left"
          @click="onPickRegister(m)"
        >
          <div class="relative aspect-[2/3] overflow-hidden rounded-xl border border-line bg-ink-700 transition group-hover/c:border-lineHover">
            <img
              v-if="poster(m.poster_path)"
              :src="poster(m.poster_path)"
              :alt="m.title"
              class="h-full w-full object-cover transition-transform duration-300 group-hover/c:scale-[1.04]"
            >
            <div
              v-else
              class="flex h-full w-full items-center justify-center text-[12px] text-fg-muted"
            >
              포스터 없음
            </div>
            <div class="absolute inset-0 sheen opacity-0 transition-opacity duration-500 group-hover/c:opacity-100" />
            <div class="absolute right-2.5 top-2.5 rounded-full bg-gold px-2 py-0.5 text-[10.5px] font-semibold text-ink opacity-0 transition-opacity group-hover/c:opacity-100">
              등록
            </div>
          </div>
          <div class="mt-2 truncate text-[14px] font-semibold text-fg">
            {{ m.title }}
          </div>
          <div class="mt-0.5 text-[12px] text-fg-muted">
            {{ m.release_year || "" }}<span v-if="m.vote_average"> · <span class="text-gold">★</span> {{ m.vote_average }}</span>
          </div>
        </button>
      </div>
      <p
        v-else-if="searched"
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        결과가 없습니다.
      </p>
      <p
        v-else
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        지도에 더할 영화를 검색해보세요.
      </p>
    </div>

    <!-- ═══════════════ PANEL: 지도 탐색 (4.4, 우리 실기능) ═══════════════ -->
    <template v-else>
      <p
        v-if="exploreLoading || !exploreData"
        class="py-16 text-center text-[14px] text-fg-muted"
      >
        탐색도를 그리는 중…
      </p>
      <div
        v-else-if="!exploreData.enough"
        class="mx-auto my-20 max-w-[460px] text-center"
      >
        <div class="font-display text-[19px] font-semibold tracking-tightest text-fg">
          아직 지도를 탐색할 수 없어요
        </div>
        <p class="mt-3 text-[14px] leading-[1.7] text-fg-muted">
          영화 <b class="text-fg">5편 이상</b>을 등록하면 탐색도가 만들어집니다.
        </p>
        <button
          type="button"
          class="mt-6 rounded-lg bg-gold px-6 py-2.5 text-[14px] font-semibold text-ink transition hover:bg-gold-soft"
          @click="goRegister"
        >
          영화 등록하러 가기
        </button>
      </div>
      <template v-else>
        <div class="mb-4 font-display text-[17px] font-semibold tracking-tightest text-fg">
          {{ exploreSub === "safe" ? "가까운 취향 추천" : "새로운 취향 추천" }}
        </div>
        <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
          <!-- map frame -->
          <div class="relative overflow-hidden rounded-2xl border border-line bg-ink-800">
            <div class="grid-tex pointer-events-none absolute inset-0 opacity-60" />
            <div
              class="pointer-events-none absolute inset-0"
              style="background:radial-gradient(110% 80% at 35% 25%, rgba(230,181,102,0.10), transparent 55%), radial-gradient(100% 110% at 85% 105%, rgba(93,202,165,0.07), transparent 50%);"
            />
            <TasteMapCanvas
              :watched="exploreData.watched"
              :anchors="exploreData.anchors"
              :pins="explorePins"
              :width="980"
              :height="560"
              class="mapwrap relative block"
              @pin-click="onPickExploreMovie"
              @open-detail="goDetail"
            />
          </div>

          <!-- sidebar -->
          <aside class="flex flex-col">
            <!-- 서브탭: 미탐색 / 안전 -->
            <div class="mb-3.5 flex gap-1 border-b border-line">
              <button
                type="button"
                class="relative shrink-0 px-4 py-2.5 text-[13px] font-semibold transition"
                :class="exploreSub === 'unexplored' ? 'text-fg' : 'text-fg-muted hover:text-fg'"
                @click="exploreSub = 'unexplored'"
              >
                새로운 취향
                <span
                  class="absolute inset-x-3 -bottom-px h-[2px] rounded-full bg-gold"
                  :class="{ hidden: exploreSub !== 'unexplored' }"
                />
              </button>
              <button
                type="button"
                class="relative shrink-0 px-4 py-2.5 text-[13px] font-semibold transition"
                :class="exploreSub === 'safe' ? 'text-fg' : 'text-fg-muted hover:text-fg'"
                @click="exploreSub = 'safe'"
              >
                가까운 취향
                <span
                  class="absolute inset-x-3 -bottom-px h-[2px] rounded-full bg-gold"
                  :class="{ hidden: exploreSub !== 'safe' }"
                />
              </button>
            </div>

            <!-- 추천 1~N 목록: 지도 높이를 넘으면 이 영역만 스크롤 -->
            <div class="max-h-[520px] overflow-y-auto pr-1">
              <div
                v-for="m in exploreList"
                :key="m.id"
                class="flex items-start gap-2.5 border-t border-line py-3 first:border-t-0"
              >
                <span
                  class="mt-5 grid h-5 min-w-[26px] flex-none place-items-center rounded-md px-1 text-[11px] font-bold"
                  :class="!pinned.has(m.id)
                    ? 'bg-ink-700 text-fg-faint'
                    : (exploreSub === 'safe' ? 'bg-[#1c4fbf] text-white' : 'bg-[#c06d00] text-white')"
                >#{{ m.num }}</span>
                <button
                  type="button"
                  class="h-[62px] w-[42px] flex-none overflow-hidden rounded-md border border-line bg-ink-700"
                  @click="onPickExploreMovie(m)"
                >
                  <img
                    v-if="poster(m.poster_path)"
                    :src="poster(m.poster_path)"
                    :alt="m.title"
                    class="h-full w-full object-cover"
                  >
                </button>
                <div class="min-w-0 flex-1">
                  <button
                    type="button"
                    class="block w-full truncate text-left text-[13.5px] font-semibold text-fg transition hover:text-gold"
                    @click="onPickExploreMovie(m)"
                  >
                    {{ m.title }}
                  </button>
                  <div
                    class="mt-1 text-[12px]"
                    :class="exploreSub === 'safe' ? 'text-[#4f86ff]' : 'text-[#c06d00]'"
                  >
                    {{ exploreLabel(m) }}
                  </div>
                  <button
                    type="button"
                    class="mt-2 inline-flex items-center gap-1.5 text-[11px] text-fg-muted"
                    @click="togglePin(m.id)"
                  >
                    지도
                    <span
                      class="relative h-[17px] w-[30px] rounded-[10px] transition-colors"
                      :class="!pinned.has(m.id)
                        ? 'bg-white/[0.12]'
                        : (exploreSub === 'safe' ? 'bg-[#1c4fbf]' : 'bg-[#c06d00]')"
                    >
                      <span
                        class="absolute top-0.5 h-[13px] w-[13px] rounded-full bg-white transition-all"
                        :class="pinned.has(m.id) ? 'left-[15px]' : 'left-0.5'"
                      />
                    </span>
                  </button>
                </div>
              </div>
              <p
                v-if="!exploreList.length"
                class="mt-3 text-[13px] text-fg-faint"
              >
                이 트랙의 추천이 아직 없어요.
              </p>
            </div>
          </aside>
        </div>
      </template>
    </template>

    <!-- 시청 등록 모달 (B 재사용). 저장되면 지도 갱신 -->
    <WatchRecordModal
      v-if="regMovie"
      :movie="regMovie"
      :initial-record="regRecord"
      @saved="onRegistered"
      @close="regMovie = null"
    />
  </div>
</template>

<style scoped>
/* 지도 SVG는 프레임 폭에 맞춰 자연 비율로 전체 노출(레터박스·잘림 없음). */
.mapwrap :deep(.mapsvg) {
  width: 100%;
  height: auto;
  display: block;
}
</style>
