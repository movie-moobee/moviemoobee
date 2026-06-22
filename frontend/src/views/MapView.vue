<script setup>
// 취향 지도 페이지 (F-MAP, 김호준) — 4개 내부 탭의 셸 + '취향 지도' 탭.
// 지도 렌더는 <TasteMapCanvas>(홈 프리뷰와 공유). 여기선 탭·게이트·범례·선택 패널 담당.
// (KDE 탐색도 영역·영역 클릭=4.4, 검색 반짝=3.4 → 해당 탭에서.)
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getMyMap } from "@/api/taste";
import { searchMovies, getMovie } from "@/api/movies";
import { useMarkerMode } from "@/composables/useMarkerMode";
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

// 마커 모드(별/포스터) — 홈과 공유(localStorage). /map에선 ?view= 와도 동기화.
const markerMode = useMarkerMode();
const VIEWS = ["stars", "posters"];
if (VIEWS.includes(route.query.view)) markerMode.value = route.query.view;
function setView(v) {
  markerMode.value = v;
  router.replace({ query: { ...route.query, view: v } });
}

const loading = ref(true);
const error = ref("");
const data = ref(null);          // { enough, watched:[...] }
const selected = ref(null);      // 캔버스에서 클릭한 별
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
function openDetail() {
  if (selected.value) router.push({ name: "movie-detail", params: { id: selected.value.movie_id } });
}
function goRegister() {
  setTab("search");
}

// 본 영화 목록 자동완성(in-memory 필터 — 매우 가벼움) → 선택하면 그 별 반짝
const findMatches = computed(() => {
  const q = findQuery.value.trim().toLowerCase();
  if (!q) return [];
  return data.value.watched.filter((w) => w.title.toLowerCase().includes(q)).slice(0, 8);
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
  highlightId.value = m.movie_id;
  selected.value = m;
  findQuery.value = m.title;
  showFind.value = false;
}
function onFindEnter() {
  if (findMatches.value.length) onPickFind(findMatches.value[0]);   // 첫 매칭 선택
}

async function onSearch() {
  if (!searchQuery.value.trim()) return;
  searching.value = true;
  searchError.value = "";
  try {
    searchResults.value = await searchMovies(searchQuery.value.trim());
    searched.value = true;
  } catch {
    searchError.value = "검색에 실패했습니다.";
  } finally {
    searching.value = false;
  }
}

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
</script>

<template>
  <div class="map-page">
    <!-- 내부 탭 -->
    <div class="tabbar">
      <button
        v-for="t in TABS"
        :key="t.key"
        class="tab"
        :class="{ 'tab--on': activeTab === t.key }"
        type="button"
        @click="setTab(t.key)"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- 취향 지도 탭 -->
    <template v-if="activeTab === 'map'">
      <p
        v-if="loading"
        class="msg"
      >
        지도를 그리는 중…
      </p>
      <p
        v-else-if="error"
        class="msg msg--error"
      >
        {{ error }}
      </p>

      <!-- 5편 미만 게이트(삭제로 내려간 경우 포함) -->
      <div
        v-else-if="!data.enough"
        class="gate"
      >
        <div class="gate__title">
          아직 취향 지도를 그릴 수 없어요
        </div>
        <p class="gate__desc">
          영화 <b>5편 이상</b>을 등록하면 나만의 취향 지도가 만들어집니다.<br>
          별점을 높게 준 영화일수록 더 밝게 빛나요.
        </p>
        <button
          class="gate__btn"
          type="button"
          @click="goRegister"
        >
          영화 등록하러 가기
        </button>
      </div>

      <!-- 지도 -->
      <div
        v-else
        class="map-layout"
      >
        <div class="mapframe">
          <!-- 마커 모드 토글 (별 / 포스터) -->
          <div class="modetoggle">
            <button
              type="button"
              class="modetoggle__btn"
              :class="{ 'modetoggle__btn--on': markerMode === 'stars' }"
              @click="setView('stars')"
            >
              별
            </button>
            <button
              type="button"
              class="modetoggle__btn"
              :class="{ 'modetoggle__btn--on': markerMode === 'posters' }"
              @click="setView('posters')"
            >
              포스터
            </button>
          </div>
          <TasteMapCanvas
            :watched="data.watched"
            :width="980"
            :height="560"
            :highlight-id="highlightId"
            :mode="markerMode"
            @select="selected = $event"
          />
          <div class="legend">
            <template v-if="markerMode === 'stars'">
              <span><i class="dot dot--high" /> 크고 밝은 별 = 고평점</span>
              <span><i class="dot dot--low" /> 작고 흐린 별 = 저평점</span>
            </template>
            <template v-else>
              <span><i class="sw sw--poster" /> 포스터 = 내가 본 영화</span>
              <span><i class="sw sw--bar" /> 금색 바 = 별점</span>
            </template>
            <span>모여 있을수록 = 비슷한 취향</span>
          </div>
        </div>

        <!-- 사이드 -->
        <aside class="side">
          <!-- 내가 본 영화 찾기 → 자동완성 목록에서 선택 → 지도에서 반짝 -->
          <div class="card card--count">
            내가 본 영화 <b>{{ data.watched.length }}</b>편
          </div>
          <div class="card find-card">
            <div class="card__tag">
              내가 본 영화 찾기
            </div>
            <input
              v-model="findQuery"
              class="find"
              type="text"
              placeholder="제목을 입력하세요."
              @input="onFindInput"
              @focus="showFind = true"
              @blur="onFindBlur"
              @keyup.enter="onFindEnter"
            >
            <ul
              v-if="showFind && findMatches.length"
              class="findlist"
            >
              <li
                v-for="m in findMatches"
                :key="m.movie_id"
              >
                <button
                  class="finditem"
                  type="button"
                  @mousedown.prevent
                  @click="onPickFind(m)"
                >
                  <img
                    v-if="poster(m.poster_path)"
                    :src="poster(m.poster_path)"
                    :alt="m.title"
                    class="finditem__poster"
                  >
                  <span class="finditem__title">{{ m.title }}</span>
                  <span class="finditem__year">{{ m.release_year || "" }}</span>
                </button>
              </li>
            </ul>
            <p
              v-else-if="findQuery && !findMatches.length"
              class="find__none"
            >
              그 제목으로 본 영화가 없어요.
            </p>
          </div>

          <div class="card">
            <div class="card__tag">
              선택한 영화 
            </div>
            <div
              v-if="selected"
              class="sel"
            >
              <div class="sel__poster">
                <img
                  v-if="poster(selected.poster_path)"
                  :src="poster(selected.poster_path)"
                  :alt="selected.title"
                >
              </div>
              <div class="sel__meta">
                <div class="sel__title">
                  {{ selected.title }}
                </div>
                <div class="sel__sub">
                  {{ selected.release_year || "" }}
                </div>
                <div class="sel__rating">
                  ★ {{ selected.rating * 2 }} / 10
                </div>
                <button
                  class="sel__btn"
                  type="button"
                  @click="openDetail"
                >
                  상세 보기
                </button>
              </div>
            </div>
            <p
              v-else
              class="card__empty"
            >
              지도에서 영화를 클릭해보세요.
            </p>
          </div>

          <!-- 내 취향 요약 (주=좋아요 별점가중 장르 / 미탐색=KDE 안 가본 장르) -->
          <div
            v-if="data.summary"
            class="card"
          >
            <div class="card__tag">
              내 취향 요약
            </div>
            <div class="summary">
              <span class="summary__label">내 선호 장르</span>
              <span class="summary__val">{{ data.summary.main.join(" · ") || "—" }}</span>
            </div>
            <div class="summary">
              <span class="summary__label">미탐색 장르</span>
              <span class="summary__val summary__val--unexp">{{ data.summary.unexplored.join(" · ") || "—" }}</span>
            </div>
          </div>
        </aside>
      </div>
    </template>

    <!-- 영화 검색·등록 탭 (3.4) -->
    <div
      v-else-if="activeTab === 'search'"
      class="reg"
    >
      <div class="bar">
        <input
          v-model="searchQuery"
          class="bar__input"
          type="text"
          placeholder="등록할 영화 제목 검색"
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
      <p
        v-if="searchError"
        class="msg msg--error"
      >
        {{ searchError }}
      </p>
      <p
        v-else-if="searching"
        class="msg"
      >
        검색 중…
      </p>
      <div
        v-else-if="searchResults.length"
        class="grid"
      >
        <button
          v-for="m in searchResults"
          :key="m.id"
          class="rcard"
          type="button"
          @click="onPickRegister(m)"
        >
          <div class="rcard__poster">
            <img
              v-if="poster(m.poster_path)"
              :src="poster(m.poster_path)"
              :alt="m.title"
            >
          </div>
          <div class="rcard__title">
            {{ m.title }}
          </div>
          <div class="rcard__meta">
            {{ m.release_year || "" }} · ＋ 등록
          </div>
        </button>
      </div>
      <p
        v-else-if="searched"
        class="msg"
      >
        결과가 없습니다.
      </p>
      <p
        v-else
        class="msg"
      >
        지도에 더할 영화를 검색해보세요.
      </p>
    </div>

    <!-- 시청 영화 목록 탭 (2.3) -->
    <WatchRecordsList
      v-else-if="activeTab === 'records'"
      @changed="onRecordsChanged"
    />

    <!-- 지도 탐색 탭(4.4) -->
    <div
      v-else
      class="msg placeholder"
    >
      지도 탐색(미탐색·안전 추천) 탭 — 4.4에서 구현됩니다.
    </div>

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
.map-page {
  max-width: 1320px;
  margin: 0 auto;
  padding: 28px 24px 60px;
}

/* tabs */
.tabbar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 22px;
}
.tab {
  padding: 10px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
}
.tab--on {
  color: var(--text);
  border-bottom-color: var(--gold);
}

.msg {
  color: var(--text-muted);
  font-size: 14px;
  padding: 60px 0;
  text-align: center;
}
.msg--error {
  color: var(--danger);
}
.placeholder {
  color: var(--text-faint);
}

/* gate */
.gate {
  max-width: 460px;
  margin: 80px auto;
  text-align: center;
}
.gate__title {
  font-size: 19px;
  font-weight: 700;
  color: var(--text);
}
.gate__desc {
  margin-top: 12px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-muted);
}
.gate__btn {
  margin-top: 22px;
  padding: 11px 24px;
  background: var(--gold);
  color: #1a1206;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

/* layout */
.map-layout {
  display: grid;
  grid-template-columns: 1fr 268px;
  gap: 20px;
}
.mapframe {
  position: relative;
  border: 1px solid #262a36;
  border-radius: 8px;
  overflow: hidden;
  background: #0e1018;
}
.modetoggle {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
  display: flex;
  gap: 2px;
  padding: 2px;
  background: rgba(14, 16, 24, 0.7);
  border: 1px solid #2c3142;
  border-radius: 999px;
}
.modetoggle__btn {
  padding: 5px 14px;
  background: none;
  border: none;
  border-radius: 999px;
  color: #aeb4c4;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
}
.modetoggle__btn--on {
  background: var(--gold);
  color: #1a1206;
}
.sw {
  display: inline-block;
}
.sw--poster {
  width: 9px;
  height: 13px;
  border-radius: 2px;
  background: #2a3142;
  border: 1px solid #3a4358;
}
.sw--bar {
  width: 14px;
  height: 3px;
  background: #f4b860;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 10px 14px;
  border-top: 1px solid #262a36;
  background: #161922;
  font-size: 11.5px;
  color: #aeb4c4;
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.dot {
  border-radius: 50%;
  display: inline-block;
}
.dot--high {
  width: 13px;
  height: 13px;
  background: #fff0cd;
  box-shadow: 0 0 7px #ffe6a8;
}
.dot--low {
  width: 7px;
  height: 7px;
  background: #96a4c4;
  opacity: 0.6;
}

/* side */
.side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px;
}
.card__tag {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.card__hint {
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
}
.card__empty {
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-faint);
  line-height: 1.6;
}
.sel {
  display: flex;
  gap: 12px;
  margin-top: 10px;
}
.sel__poster {
  width: 60px;
  aspect-ratio: 2 / 3;
  flex: none;
  border-radius: 4px;
  overflow: hidden;
  background: var(--surface);
}
.sel__poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.sel__meta {
  min-width: 0;
}
.sel__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.4;
}
.sel__sub {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-muted);
}
.sel__rating {
  margin-top: 4px;
  font-size: 13px;
  color: var(--gold);
}
.sel__btn {
  margin-top: 10px;
  padding: 6px 14px;
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
}
.sel__btn:hover {
  border-color: var(--gold);
}
.card--count {
  font-size: 13px;
  color: var(--text-muted);
}
.card--count b {
  color: var(--text);
}

/* 내 취향 요약 */
.summary {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 8px;
  font-size: 13px;
}
.summary__label {
  flex: none;
  color: var(--text-muted);
}
.summary__val {
  font-weight: 600;
  color: var(--text);
}
.summary__val--unexp {
  color: var(--gold);
}

/* 내가 본 영화 찾기 (반짝) */
.find {
  width: 100%;
  margin-top: 8px;
  padding: 9px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 13px;
  font-family: var(--font);
}
.find::placeholder {
  color: var(--text-faint);
}
.find:focus {
  outline: none;
  border-color: var(--gold);
}
.find__none {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-faint);
}
.find-card {
  position: relative;
}
.findlist {
  position: absolute;
  left: 14px;
  right: 14px;
  top: calc(100% - 6px);
  z-index: 20;
  margin: 0;
  padding: 4px;
  list-style: none;
  max-height: 280px;
  overflow-y: auto;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}
.finditem {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 8px;
  background: none;
  border: none;
  border-radius: 4px;
  text-align: left;
  cursor: pointer;
  font-family: var(--font);
}
.finditem:hover {
  background: var(--surface);
}
.finditem__poster {
  width: 24px;
  height: 36px;
  object-fit: cover;
  border-radius: 2px;
  flex: none;
  background: var(--surface);
}
.finditem__title {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.finditem__year {
  font-size: 11.5px;
  color: var(--text-muted);
  flex: none;
}

/* 영화 검색·등록 탭 */
.reg {
  padding-top: 4px;
}
.bar {
  display: flex;
  gap: 10px;
  margin-bottom: 22px;
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
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 18px;
}
.rcard {
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  font-family: var(--font);
}
.rcard__poster {
  aspect-ratio: 2 / 3;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--surface-2);
}
.rcard__poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}
.rcard:hover .rcard__poster img {
  transform: scale(1.04);
}
.rcard__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-top: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rcard__meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
</style>
