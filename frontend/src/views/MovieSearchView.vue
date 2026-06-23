<script setup>
// 영화 검색 (F-MOV-01). 제목 검색 + 필터(장르·평점·개봉년도·러닝타임·언어) → 그리드 → 상세.
// 진입 시 평점 높은순 기본 목록. 상세 갔다 와도 검색어·필터·결과 유지(useMovieSearch).
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { browseMovies, getGenres } from "@/api/movies";
import { useMovieSearch } from "@/composables/useMovieSearch";

const router = useRouter();
const { query, filters, results, searched, loaded, resetFilters } = useMovieSearch();
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
  return [f.genre, f.decade, f.runtime, f.min_rating || f.max_rating].filter(Boolean).length;
});

// 드롭다운(한 번에 하나만 열림)
const openKey = ref(null);
function toggleMenu(key) {
  openKey.value = openKey.value === key ? null : key;
}
function closeMenu() {
  openKey.value = null;
}

async function fetchMovies() {
  loading.value = true;
  error.value = "";
  try {
    const q = query.value.trim();
    const data = await browseMovies({ search: q, ...filters.value });
    // 제목 검색 시: 한글 자연정렬로 시리즈 묶기(아이언맨→2→3, 미션 임파서블 묶음).
    // PostgreSQL 한글 collation이 불안정해 정렬은 프론트에서 확정. 필터/랜딩은 평점순 유지.
    if (q) {
      data.sort((a, b) => a.title.localeCompare(b.title, "ko", { numeric: true }));
    }
    results.value = data;
  } catch {
    error.value = "영화를 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  searched.value = true;
  closeMenu();
  fetchMovies();
}
function pickOption(key, value) {
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
  <div class="search-page">
    <!-- 검색 -->
    <div class="bar">
      <input
        v-model="query"
        class="bar__input"
        placeholder="검색어 입력… (TMDB 영화 검색)"
        @keyup.enter="onSearch"
      >
      <button
        class="bar__btn"
        type="button"
        @click="onSearch"
      >
        검색
      </button>
    </div>

    <!-- 필터 칩 바 -->
    <div class="filters">
      <button
        class="chip"
        :class="{ 'chip--on': activeCount === 0 }"
        type="button"
        @click="clearAll"
      >
        전체
      </button>

      <div
        v-for="def in FILTER_DEFS"
        :key="def.key"
        class="chip-wrap"
      >
        <button
          class="chip chip--drop"
          :class="{ 'chip--on': isActive(def) }"
          type="button"
          @click="def.type === 'range' ? openRating() : toggleMenu(def.key)"
        >
          {{ labelFor(def) }}
          <span class="caret">▾</span>
        </button>

        <!-- 평점: 직접 입력 범위 -->
        <div
          v-if="def.type === 'range' && openKey === 'rating'"
          class="menu menu--rating"
        >
          <div class="rating-row">
            <input
              v-model="ratingMin"
              class="rating-input"
              type="number"
              min="0"
              max="10"
              step="0.1"
              placeholder="0"
            >
            <span>~</span>
            <input
              v-model="ratingMax"
              class="rating-input"
              type="number"
              min="0"
              max="10"
              step="0.1"
              placeholder="10"
            >
            <span class="rating-unit">점</span>
          </div>
          <button
            class="rating-apply"
            type="button"
            @click="applyRating"
          >
            적용
          </button>
        </div>

        <!-- 옵션형(장르·개봉년도·러닝타임) -->
        <div
          v-else-if="def.type === 'options' && openKey === def.key"
          class="menu"
        >
          <button
            v-for="opt in optionsFor(def.key)"
            :key="opt.value"
            class="menu__item"
            :class="{ 'menu__item--on': filters[def.key] === opt.value }"
            type="button"
            @click="pickOption(def.key, opt.value)"
          >
            {{ opt.label }}
          </button>
          <p
            v-if="!optionsFor(def.key).length"
            class="menu__empty"
          >
            불러오는 중… (백엔드 재시작 필요할 수 있어요)
          </p>
        </div>
      </div>

      <span
        v-if="activeCount"
        class="multi"
      >
        <b>{{ activeCount }}</b> 다중 필터
      </span>
    </div>

    <!-- 백드롭(바깥 클릭 시 메뉴 닫힘) -->
    <div
      v-if="openKey"
      class="backdrop"
      @click="closeMenu"
    />

    <!-- 결과 -->
    <p
      v-if="error"
      class="msg msg--error"
    >
      {{ error }}
    </p>
    <p
      v-else-if="loading"
      class="msg"
    >
      불러오는 중…
    </p>
    <template v-else>
      <div
        v-if="searched"
        class="count"
      >
        검색 결과 <b>{{ results.length }}</b>편
      </div>
      <div
        v-if="results.length"
        class="grid"
      >
        <button
          v-for="m in results"
          :key="m.id"
          class="card"
          type="button"
          @click="openMovie(m.id)"
        >
          <div class="card__poster">
            <img
              v-if="poster(m.poster_path)"
              :src="poster(m.poster_path)"
              :alt="m.title"
            >
            <div
              v-else
              class="card__poster--empty"
            >
              포스터 없음
            </div>
          </div>
          <div class="card__title">
            {{ m.title }}
          </div>
          <div class="card__meta">
            {{ m.release_year || "" }}<span v-if="m.vote_average"> · ⭐ {{ m.vote_average }}</span>
          </div>
        </button>
      </div>
      <p
        v-else
        class="msg"
      >
        조건에 맞는 영화가 없습니다.
      </p>
    </template>
  </div>
</template>

<style scoped>
.search-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 28px 24px 60px;
}
.bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.bar__input {
  flex: 1;
  padding: 12px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 14px;
  font-family: var(--font);
}
.bar__input::placeholder {
  color: var(--text-faint);
}
.bar__input:focus {
  outline: none;
  border-color: var(--gold);
}
.bar__btn {
  padding: 0 22px;
  background: var(--gold);
  color: #1a1206;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

/* 필터 칩 바 */
.filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 22px;
}
.chip-wrap {
  position: relative;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.chip--on {
  border-color: var(--gold);
  color: var(--gold);
  background: rgba(212, 175, 55, 0.08);
}
.caret {
  font-size: 10px;
}
.multi {
  margin-left: auto;
  font-size: 12.5px;
  color: var(--text-muted);
  padding: 5px 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
}
.multi b {
  color: var(--gold);
}

/* 드롭다운 메뉴 */
.menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 20;
  min-width: 140px;
  max-height: 280px;
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--border-hover);
  border-radius: var(--radius-sm);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45);
  padding: 6px;
}
.menu__item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  background: none;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--text);
  font-family: var(--font);
  font-size: 13px;
  cursor: pointer;
}
.menu__item:hover {
  background: var(--surface-2);
}
.menu__item--on {
  color: var(--gold);
  font-weight: 700;
}
.menu__empty {
  font-size: 12px;
  color: var(--text-muted);
  padding: 8px 10px;
  margin: 0;
}
/* 평점 범위 입력 */
.menu--rating {
  min-width: 200px;
  padding: 12px;
}
.rating-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.rating-input {
  width: 56px;
  padding: 7px 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-family: var(--font);
  font-size: 13px;
  text-align: center;
}
.rating-input:focus {
  outline: none;
  border-color: var(--gold);
}
.rating-unit {
  font-size: 13px;
  color: var(--text-muted);
}
.rating-apply {
  width: 100%;
  padding: 8px;
  background: var(--gold);
  color: #1a1206;
  border: 0;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 10;
}

.msg {
  color: var(--text-muted);
  font-size: 14px;
  padding: 40px 0;
  text-align: center;
}
.msg--error {
  color: var(--danger);
}
.count {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 16px;
}
.count b {
  color: var(--text);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 18px;
}
.card {
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  font-family: var(--font);
}
.card__poster {
  aspect-ratio: 2 / 3;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--surface-2);
}
.card__poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}
.card:hover .card__poster img {
  transform: scale(1.04);
}
.card__poster--empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--text-muted);
}
.card__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-top: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card__meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
</style>
