<script setup>
// 추천 페이지 (F-REC, 4.3, 김호준) — 오늘의 추천(미탐색 Top1) + 안전·미탐색 두 트랙.
// 안전 = 본 영화 kNN 근접(취향 강화) / 미탐색 = KDE 저밀도(필터버블 밖, "좋아하게 될").
// 백엔드 /api/taste/recommendations 가 각 10편을 MMR로 선별해 내려준다.
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getRecommendations } from "@/api/taste";

const router = useRouter();
const loading = ref(true);
const error = ref("");
const data = ref(null); // { enough, safe:[...], unexplored:[...] }

const POSTER = "https://image.tmdb.org/t/p/w342";
const HERO = "https://image.tmdb.org/t/p/w500";

// 오늘의 추천 = 안 본 영화 중 평점 7+ 에서 하루 한 편 랜덤(백엔드 daily_pick, 날짜 시드)
const today = computed(() => data.value?.today ?? null);
// 미탐색 그리드는 전체(히어로가 미탐색과 별개라 slice 불필요)
const unexploredList = computed(() => data.value?.unexplored ?? []);

onMounted(async () => {
  try {
    data.value = await getRecommendations();
  } catch {
    error.value = "추천을 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
});

function poster(p, base = POSTER) {
  return p ? base + p : "";
}
function openMovie(id) {
  router.push({ name: "movie-detail", params: { id } });
}
function goRegister() {
  router.push({ name: "movies" });
}

// 가로 드래그 스크롤 (rail). 4px 이상 끌면 '드래그'로 보고 카드 클릭(네비) 억제.
const dragMoved = ref(false);
let drag = null;
function railDown(e) {
  drag = { el: e.currentTarget, x: e.clientX, left: e.currentTarget.scrollLeft };
  dragMoved.value = false;
}
function railMove(e) {
  if (!drag) return;
  const dx = e.clientX - drag.x;
  if (Math.abs(dx) > 4) dragMoved.value = true;
  drag.el.scrollLeft = drag.left - dx;
}
function railUp() {
  drag = null;
}
function onCardClick(id) {
  if (dragMoved.value) return;   // 드래그 끝이면 상세 이동 안 함
  openMovie(id);
}
</script>

<template>
  <div class="reco">
    <p
      v-if="loading"
      class="msg"
    >
      오늘의 추천을 고르는 중…
    </p>
    <p
      v-else-if="error"
      class="msg msg--error"
    >
      {{ error }}
    </p>

    <!-- 5편 미만 게이트 -->
    <div
      v-else-if="!data.enough"
      class="gate"
    >
      <div class="gate__title">
        아직 추천을 만들 수 없어요
      </div>
      <p class="gate__desc">
        영화 <b>5편 이상</b>을 등록하면 취향을 분석해<br>
        안전한 선택과 새로운 발견을 추천해드려요.
      </p>
      <button
        class="gate__btn"
        type="button"
        @click="goRegister"
      >
        영화 등록하러 가기
      </button>
    </div>

    <template v-else>
      <!-- 오늘의 추천 (미탐색 Top1) -->
      <section
        v-if="today"
        class="hero"
      >
        <button
          class="hero__poster"
          type="button"
          @click="openMovie(today.id)"
        >
          <img
            v-if="poster(today.poster_path, HERO)"
            :src="poster(today.poster_path, HERO)"
            :alt="today.title"
          >
        </button>
        <div class="hero__body">
          <div class="hero__tag">
            오늘의 추천
          </div>
          <h1 class="hero__title">
            매일 한 편, <span class="accent">오늘의 발견</span>
          </h1>
          <div class="hero__movie">
            {{ today.title }}
            <span class="hero__year">{{ today.release_year || "" }}<span v-if="today.vote_average"> · ★ {{ today.vote_average }}</span></span>
          </div>
          <p class="hero__desc">
            아직 안 본 영화 중 평점 높은 한 편이에요. 매일 자정에 새로 골라드려요.
          </p>
          <button
            class="hero__btn"
            type="button"
            @click="openMovie(today.id)"
          >
            자세히 보기
          </button>
        </div>
      </section>

      <!-- 안전한 선택 -->
      <section class="track">
        <div class="track__head">
          <h2 class="track__title">
            🛡️ 내 취향 근처
          </h2>
          <span class="track__sub">내가 좋아했던 분위기의 영화들이에요</span>
        </div>
        <div
          class="rail"
          @pointerdown="railDown"
          @pointermove="railMove"
          @pointerup="railUp"
          @pointerleave="railUp"
        >
          <button
            v-for="m in data.safe"
            :key="m.id"
            class="card"
            type="button"
            @click="onCardClick(m.id)"
          >
            <div class="card__poster">
              <img
                v-if="poster(m.poster_path)"
                :src="poster(m.poster_path)"
                :alt="m.title"
              >
            </div>
            <div class="card__title">
              {{ m.title }}
            </div>
            <div class="card__meta">
              {{ m.release_year || "" }} · ★ {{ m.vote_average }}
            </div>
          </button>
        </div>
      </section>

      <!-- 미탐색 추천 -->
      <section class="track">
        <div class="track__head">
          <h2 class="track__title">
            🧭 미탐색 추천
          </h2>
          <span class="track__sub track__sub--accent">필터 버블 밖 — 안 가본 취향의 영역</span>
        </div>
        <div
          class="rail"
          @pointerdown="railDown"
          @pointermove="railMove"
          @pointerup="railUp"
          @pointerleave="railUp"
        >
          <button
            v-for="m in unexploredList"
            :key="m.id"
            class="card"
            type="button"
            @click="onCardClick(m.id)"
          >
            <div class="card__poster">
              <img
                v-if="poster(m.poster_path)"
                :src="poster(m.poster_path)"
                :alt="m.title"
              >
            </div>
            <div class="card__title">
              {{ m.title }}
            </div>
            <div class="card__meta">
              {{ m.release_year || "" }} · ★ {{ m.vote_average }}
            </div>
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.reco {
  width: 100%;
  max-width: var(--page-max-wide);
  margin: 0 auto;
  padding: 28px var(--page-pad) 60px;
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

/* hero (오늘의 추천) */
.hero {
  display: flex;
  gap: 24px;
  padding: 22px;
  background: linear-gradient(135deg, #1b1830, #14161f);
  border: 1px solid #2c3142;
  border-radius: 12px;
  margin-bottom: 40px;
}
.hero__poster {
  flex: none;
  width: 150px;
  aspect-ratio: 2 / 3;
  padding: 0;
  border: none;
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface-2);
  cursor: pointer;
}
.hero__poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}
.hero__poster:hover img {
  transform: scale(1.04);
}
.hero__body {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}
.hero__tag {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--gold);
  text-transform: uppercase;
}
.hero__title {
  margin: 8px 0 0;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--text);
}
.accent {
  color: var(--gold);
}
.hero__movie {
  margin-top: 14px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}
.hero__year {
  font-size: 13px;
  font-weight: 400;
  color: var(--text-muted);
  margin-left: 6px;
}
.hero__desc {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-muted);
  max-width: 520px;
}
.hero__btn {
  align-self: flex-start;
  margin-top: 16px;
  padding: 9px 20px;
  background: var(--gold);
  color: #1a1206;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

/* track sections */
.track {
  margin-top: 36px;
}
.track__head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}
.track__title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
}
.track__sub {
  font-size: 12.5px;
  color: var(--text-muted);
}
.track__sub--accent {
  color: var(--gold);
}

/* card rail (가로 한 줄 · 드래그 스크롤) */
.rail {
  display: flex;
  gap: 18px;
  overflow-x: auto;
  padding-bottom: 12px;
  cursor: grab;
}
.rail:active {
  cursor: grabbing;
}
.card {
  width: 184px;
  flex: none;
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  font-family: var(--font);
}
/* 드래그 중 이미지/텍스트 선택·고스트 방지 */
.rail img {
  user-select: none;
  -webkit-user-drag: none;
  pointer-events: none;
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
.card__title {
  font-size: 13.5px;
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

@media (max-width: 720px) {
  .hero {
    flex-direction: column;
  }
  .hero__poster {
    width: min(180px, 54vw);
  }
  .track__head {
    flex-direction: column;
    gap: 4px;
  }
}

@media (max-width: 520px) {
  .card {
    width: 150px;
  }
}
</style>
