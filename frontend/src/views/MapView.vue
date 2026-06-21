<script setup>
// 취향 지도 페이지 (F-MAP, 김호준) — 4개 내부 탭의 셸 + '취향 지도' 탭.
// 지도 렌더는 <TasteMapCanvas>(홈 프리뷰와 공유). 여기선 탭·게이트·범례·선택 패널 담당.
// (KDE 탐색도 영역·영역 클릭=4.4, 검색 반짝=3.4 → 해당 탭에서.)
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getMyMap } from "@/api/taste";
import TasteMapCanvas from "@/components/TasteMapCanvas.vue";

const router = useRouter();
const TABS = [
  { key: "map", label: "취향 지도" },
  { key: "records", label: "시청 영화 목록" },
  { key: "search", label: "영화 검색·등록" },
  { key: "explore", label: "지도 탐색" },
];
const activeTab = ref("map");

const loading = ref(true);
const error = ref("");
const data = ref(null);          // { enough, watched:[...] }
const selected = ref(null);      // 캔버스에서 클릭한 별
const IMG = "https://image.tmdb.org/t/p/w185";

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
  router.push({ name: "movies" });
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
        @click="activeTab = t.key"
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
          <TasteMapCanvas
            :watched="data.watched"
            :width="980"
            :height="560"
            @select="selected = $event"
          />
          <div class="legend">
            <span><i class="dot dot--high" /> 크고 밝은 별 = 고평점</span>
            <span><i class="dot dot--low" /> 작고 흐린 별 = 저평점</span>
            <span>모여 있을수록 = 비슷한 취향</span>
          </div>
        </div>

        <!-- 사이드: 선택한 별 -->
        <aside class="side">
          <div class="card">
            <div class="card__tag">
              선택한 영화 <span
                v-if="!selected"
                class="card__hint"
              >— 별을 눌러보세요</span>
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
              지도의 빛나는 별이 내가 본 영화예요. 밝을수록 높게 준 별점.
            </p>
          </div>
          <div class="card card--count">
            내가 본 영화 <b>{{ data.watched.length }}</b>편
          </div>
        </aside>
      </div>
    </template>

    <!-- 나머지 탭(3.4·4.4에서 구현) -->
    <div
      v-else
      class="msg placeholder"
    >
      <template v-if="activeTab === 'records'">
        시청 영화 목록 탭 — 곧 연결됩니다.
      </template>
      <template v-else-if="activeTab === 'search'">
        영화 검색·등록 탭 — 3.4에서 구현됩니다.
      </template>
      <template v-else>
        지도 탐색(미탐색·안전 추천) 탭 — 4.4에서 구현됩니다.
      </template>
    </div>
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
  border: 1px solid #262a36;
  border-radius: 8px;
  overflow: hidden;
  background: #0e1018;
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
</style>
