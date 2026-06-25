<script setup>
// 영화 검색 (F-MOV-01). 제목 검색 + 필터(장르·평점·개봉년도·러닝타임·언어) → 그리드 → 상세.
// 진입 시 평점 높은순 기본 목록. 상세 갔다 와도 검색어·필터·결과 유지(useMovieSearch).
// 단, 네비바로 다른 탭(홈·지도 등)으로 이탈하면 초기화 — 상세는 검색 흐름의 연장이라 유지.
import { ref, computed, onMounted } from "vue";
import { useRouter, onBeforeRouteLeave } from "vue-router";
import { browseMovies, getGenres } from "@/api/movies";
import { useMovieSearch } from "@/composables/useMovieSearch";

const router = useRouter();
const { query, filters, results, searched, loaded, resetFilters, resetSearch } = useMovieSearch();

// 검색 화면을 떠날 때: 상세(movie-detail)로 가면 검색 보존, 그 외 이탈은 초기화.
onBeforeRouteLeave((to) => {
  if (to.name !== "movie-detail") resetSearch();
});
const loading = ref(false);
const error = ref("");
const IMG = "https://image.tmdb.org/t/p/w300";

// 필터 칩 정의 (rating은 직접 입력 범위, 나머지는 옵션 선택)
const FILTER_DEFS = [
  { key: "genre", label: "장르", type: "options" },
  { key: "rating", label: "평점", type: "range" },
  { key: "decade", label: "개봉년도", type: "options" },
  { key: "runtime", label: "러닝타임", type: "options" },
];
const STATIC_OPTIONS = {
  decade: [
    { value: "2020", label: "2020년대" },
    { value: "2010", label: "2010년대" },
    { value: "2000", label: "2000년대" },
  ],
  runtime: [
    { value: "short", label: "90분 미만" },
    { value: "medium", label: "90~120분" },
    { value: "long", label: "120분 이상" },
  ],
};
const genreNames = ref([]);
function optionsFor(key) {
  if (key === "genre") return genreNames.value.map((n) => ({ value: n, label: n }));
  return STATIC_OPTIONS[key] || [];
}
function isActive(def) {
  if (def.type === "range") return !!(filters.value.min_rating || filters.value.max_rating);
  if (def.key === "genre") return filters.value.genre.length > 0;
  return !!filters.value[def.key];
}
function labelFor(def) {
  if (def.type === "range") {
    const lo = filters.value.min_rating;
    const hi = filters.value.max_rating;
    if (!lo && !hi) return def.label;
    return `${lo || "0"}~${hi || "10"}점`;
  }
  const v = filters.value[def.key];
  if (def.key === "genre") {
    if (!v.length) return def.label;
    if (v.length === 1) return v[0];
    return `${def.label} ${v.length}개`;
  }
  if (!v) return def.label;
  const opt = optionsFor(def.key).find((o) => o.value === v);
  return opt ? opt.label : def.label;
}
// 평점 입력 임시값 (메뉴에서 입력 → 적용 시 filters 반영)
const ratingMin = ref("");
const ratingMax = ref("");
function openRating() {
  ratingMin.value = filters.value.min_rating;
  ratingMax.value = filters.value.max_rating;
  toggleMenu("rating");
}
function applyRating() {
  filters.value.min_rating = ratingMin.value !== "" ? String(ratingMin.value) : "";
  filters.value.max_rating = ratingMax.value !== "" ? String(ratingMax.value) : "";
  searched.value = true;
  closeMenu();
  fetchMovies();
}

const activeCount = computed(() => {
  const f = filters.value;
  return [f.decade, f.runtime, f.min_rating || f.max_rating].filter(Boolean).length + f.genre.length;
});

// 드롭다운(한 번에 하나만 열림)
const openKey = ref(null);
let genreFetchTimer = null;
function toggleMenu(key) {
  openKey.value = openKey.value === key ? null : key;
}
function closeMenu() {
  openKey.value = null;
}

async function fetchMovies({ keepResults = false } = {}) {
  if (!keepResults) loading.value = true;
  error.value = "";
  try {
    const q = query.value.trim();
    const data = await browseMovies({
      search: q,
      ...filters.value,
      genre: filters.value.genre.join(","),
    });
    // 제목 검색 시: 한글 자연정렬로 시리즈 묶기(아이언맨→2→3, 미션 임파서블 묶음).
    // PostgreSQL 한글 collation이 불안정해 정렬은 프론트에서 확정. 필터/랜딩은 평점순 유지.
    if (q) {
      data.sort((a, b) => a.title.localeCompare(b.title, "ko", { numeric: true }));
    }
    results.value = data;
  } catch {
    error.value = "영화를 불러오지 못했습니다.";
  } finally {
    if (!keepResults) loading.value = false;
  }
}
function scheduleGenreFetch() {
  clearTimeout(genreFetchTimer);
  genreFetchTimer = setTimeout(() => {
    fetchMovies({ keepResults: true });
  }, 160);
}

function onSearch() {
  searched.value = true;
  closeMenu();
  fetchMovies();
}
function pickOption(key, value) {
  if (key === "genre") {
    const selected = filters.value.genre;
    filters.value.genre = selected.includes(value)
      ? selected.filter((v) => v !== value)
      : [...selected, value];
    searched.value = true;
    scheduleGenreFetch();
    return;
  }
  filters.value[key] = filters.value[key] === value ? "" : value; // 같은 값 재선택 = 해제
  searched.value = true;
  closeMenu();
  fetchMovies();
}
function clearAll() {
  query.value = "";
  resetFilters();
  searched.value = false;
  closeMenu();
  fetchMovies(); // 기본 목록으로 복귀
}

function openMovie(id) {
  router.push({ name: "movie-detail", params: { id } });
}
function poster(p) {
  return p ? IMG + p : "";
}

onMounted(async () => {
  if (!genreNames.value.length) {
    try {
      genreNames.value = await getGenres();
    } catch {
      /* 장르 못 받아도 나머지 필터는 동작 */
    }
  }
  // 최초 진입만 기본 목록 로드 — 재진입(뒤로가기)은 보존된 결과 유지
  if (!loaded.value) {
    await fetchMovies();
    loaded.value = true;
  }
});
</script>

<template>
  <div class="mx-auto max-w-[1500px] px-6 pb-28 pt-10 lg:px-10">
    <!-- ───────── PAGE HEADER ───────── -->
    <section class="mb-7">
      <div class="mb-3 flex items-center gap-2.5 font-sans text-[11px] uppercase tracking-[0.14em] text-fg-muted">
        <span class="h-px w-7 bg-gold/60" />영화 검색 · Browse the archive
      </div>
      <h1 class="font-display text-[30px] font-semibold leading-[1.12] tracking-tightest sm:text-[38px]">
        다음 별이 될 영화를<br> <span class="text-fg-muted">찾아보세요</span>
      </h1>
    </section>

    <!-- ───────── SEARCH BAR ───────── -->
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
          v-model="query"
          class="w-full bg-transparent text-[14px] text-fg placeholder:text-fg-faint focus:outline-none"
          placeholder="검색어 입력…"
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

    <!-- ───────── FILTER CHIP BAR ───────── -->
    <div class="relative mb-6 flex flex-wrap items-center gap-2">
      <button
        type="button"
        :class="activeCount === 0 ? 'chip chip-on' : 'chip chip-off'"
        @click="clearAll"
      >
        전체
      </button>

      <div
        v-for="def in FILTER_DEFS"
        :key="def.key"
        class="relative"
      >
        <button
          type="button"
          :class="isActive(def) ? 'chip chip-on' : 'chip chip-off'"
          :style="def.key === 'genre' ? { minWidth: '86px', justifyContent: 'center' } : null"
          @click="def.type === 'range' ? openRating() : toggleMenu(def.key)"
        >
          {{ labelFor(def) }}<span class="text-[10px] opacity-70">▾</span>
        </button>

        <!-- 평점: 직접 입력 범위 -->
        <div
          v-if="def.type === 'range' && openKey === 'rating'"
          class="absolute left-0 top-[calc(100%+6px)] z-20 w-[210px] rounded-xl border border-lineHover bg-ink-800 p-3 shadow-[0_12px_30px_rgba(0,0,0,0.45)]"
        >
          <div class="mb-2.5 flex items-center gap-1.5">
            <input
              v-model="ratingMin"
              type="number"
              min="0"
              max="10"
              step="0.1"
              placeholder="0"
              class="w-14 rounded-lg border border-line bg-ink-700 px-2 py-1.5 text-center text-[13px] text-fg focus:border-gold focus:outline-none"
            >
            <span class="text-fg-muted">~</span>
            <input
              v-model="ratingMax"
              type="number"
              min="0"
              max="10"
              step="0.1"
              placeholder="10"
              class="w-14 rounded-lg border border-line bg-ink-700 px-2 py-1.5 text-center text-[13px] text-fg focus:border-gold focus:outline-none"
            >
            <span class="text-[13px] text-fg-muted">점</span>
          </div>
          <button
            type="button"
            class="w-full rounded-lg bg-gold py-2 text-[13px] font-semibold text-ink transition hover:bg-gold-soft"
            @click="applyRating"
          >
            적용
          </button>
        </div>

        <!-- 옵션형(장르·개봉년도·러닝타임) -->
        <div
          v-else-if="def.type === 'options' && openKey === def.key"
          :class="def.key === 'genre'
            ? 'absolute left-0 top-[calc(100%+6px)] z-20 flex max-h-[320px] w-[270px] flex-wrap gap-2 overflow-y-auto rounded-xl border border-lineHover bg-ink-800 p-3 shadow-[0_12px_30px_rgba(0,0,0,0.45)]'
            : 'absolute left-0 top-[calc(100%+6px)] z-20 max-h-[280px] min-w-[150px] overflow-y-auto rounded-xl border border-lineHover bg-ink-800 p-1.5 shadow-[0_12px_30px_rgba(0,0,0,0.45)]'"
        >
          <button
            v-for="opt in optionsFor(def.key)"
            :key="opt.value"
            type="button"
            :class="def.key === 'genre'
              ? (filters.genre.includes(opt.value)
                ? 'rounded-full border border-gold bg-gold px-3 py-1.5 text-[13px] font-semibold text-ink shadow-[0_0_0_1px_rgba(230,181,102,0.18)] transition'
                : 'rounded-full border border-line bg-transparent px-3 py-1.5 text-[13px] font-semibold text-fg-muted transition hover:border-lineHover hover:text-fg')
              : ['block w-full rounded-lg px-2.5 py-2 text-left text-[13px] transition hover:bg-white/[0.05]', filters[def.key] === opt.value ? 'font-bold text-gold' : 'text-fg']"
            @click="pickOption(def.key, opt.value)"
          >
            {{ opt.label }}
          </button>
          <p
            v-if="!optionsFor(def.key).length"
            class="px-2.5 py-2 text-[12px] text-fg-muted"
          >
            불러오는 중… (백엔드 재시작 필요할 수 있어요)
          </p>
        </div>
      </div>

      <span
        v-if="activeCount"
        class="ml-auto rounded-full border border-line px-3 py-1.5 text-[12.5px] text-fg-muted"
      >
        <b class="text-gold">{{ activeCount }}</b> 다중 필터
      </span>
    </div>

    <!-- 백드롭(바깥 클릭 시 메뉴 닫힘) -->
    <div
      v-if="openKey"
      class="fixed inset-0 z-10"
      @click="closeMenu"
    />

    <!-- ───────── RESULTS ───────── -->
    <p
      v-if="error"
      class="py-10 text-center text-[14px] text-danger"
    >
      {{ error }}
    </p>
    <p
      v-else-if="loading"
      class="py-10 text-center text-[14px] text-fg-muted"
    >
      불러오는 중…
    </p>
    <template v-else>
      <div
        v-if="searched"
        class="mb-4 text-[13px] text-fg-muted"
      >
        검색 결과 <b class="text-fg">{{ results.length }}</b>편
      </div>
      <div
        v-if="results.length"
        class="grid gap-[18px]"
        style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr))"
      >
        <button
          v-for="m in results"
          :key="m.id"
          type="button"
          class="group/c text-left"
          @click="openMovie(m.id)"
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
        v-else
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        조건에 맞는 영화가 없습니다.
      </p>
    </template>
  </div>
</template>

<style scoped>
/* 필터 칩 (시안 Carbon chip 스타일) */
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
  transition: all 0.15s;
}
.chip-off {
  background: #0c0c0f;
  border: 1px solid rgba(255, 255, 255, 0.07);
  color: #8c8f99;
}
.chip-off:hover {
  border-color: rgba(255, 255, 255, 0.16);
  color: #ecedf1;
}
.chip-on {
  background: rgba(230, 181, 102, 0.1);
  border: 1px solid #e6b566;
  color: #e6b566;
}
/* number input 스피너 숨김 */
input[type="number"]::-webkit-outer-spin-button,
input[type="number"]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
input[type="number"] { -moz-appearance: textfield; }
</style>
