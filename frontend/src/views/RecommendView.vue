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
  <div class="mx-auto max-w-[1100px] px-6 pb-28 pt-10 lg:px-8">
    <p
      v-if="loading"
      class="py-16 text-center text-[14px] text-fg-muted"
    >
      오늘의 추천을 고르는 중…
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
        아직 추천을 만들 수 없어요
      </div>
      <p class="mt-3 text-[14px] leading-[1.7] text-fg-muted">
        영화 <b class="text-fg">5편 이상</b>을 등록하면 취향을 분석해<br>
        가까운 취향과 새로운 취향을 추천해드려요.
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
      <!-- ───────── 오늘의 추천 (hero) ───────── -->
      <section
        v-if="today"
        class="relative mb-10 flex flex-col gap-6 overflow-hidden rounded-2xl border border-line bg-ink-800 p-6 sm:flex-row"
      >
        <div class="grid-tex pointer-events-none absolute inset-0 opacity-40" />
        <div class="pointer-events-none absolute -right-12 -top-12 h-48 w-48 rounded-full bg-gold/10 blur-3xl" />

        <button
          type="button"
          class="group/c relative aspect-[2/3] w-[150px] shrink-0 overflow-hidden rounded-xl border border-line bg-ink-700"
          @click="openMovie(today.id)"
        >
          <img
            v-if="poster(today.poster_path, HERO)"
            :src="poster(today.poster_path, HERO)"
            :alt="today.title"
            class="h-full w-full object-cover transition-transform duration-300 group-hover/c:scale-[1.04]"
          >
          <div
            v-else
            class="grid-tex absolute inset-0 opacity-30"
          />
        </button>

        <div class="relative flex min-w-0 flex-col justify-center">
          <div class="font-sans text-[12px] font-semibold tracking-[0.04em] text-gold">
            오늘의 추천
          </div>
          <h1 class="mt-2 font-display text-[26px] font-semibold tracking-tightest text-fg sm:text-[28px]">
            매일 한 편, <span class="text-gold">오늘의 발견</span>
          </h1>
          <div class="mt-3.5 text-[16px] font-semibold text-fg">
            {{ today.title }}<span class="ml-1.5 text-[13px] font-normal text-fg-muted">{{ today.release_year || "" }}<span v-if="today.vote_average"> · <span class="text-gold">★</span> {{ today.vote_average }}</span></span>
          </div>
          <p class="mt-2 max-w-[520px] text-[13px] leading-[1.6] text-fg-muted">
            아직 안 본 영화 중 평점 높은 한 편이에요. 매일 자정에 새로 골라드려요.
          </p>
          <button
            type="button"
            class="mt-4 inline-flex w-max items-center gap-1.5 rounded-lg bg-gold px-5 py-2.5 text-[13px] font-semibold text-ink transition hover:bg-gold-soft"
            @click="openMovie(today.id)"
          >
            자세히 보기
            <svg
              viewBox="0 0 24 24"
              class="h-3.5 w-3.5"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
            ><path
              d="M5 12h14M13 6l6 6-6 6"
              stroke-linecap="round"
              stroke-linejoin="round"
            /></svg>
          </button>
        </div>
      </section>

      <!-- ───────── 안전한 선택 ───────── -->
      <section class="mt-9">
        <div class="mb-4 flex items-baseline gap-3">
          <h2 class="flex items-center gap-2 font-display text-[17px] font-semibold tracking-tightest text-fg">
            🛡️ 가까운 취향
          </h2>
          <span class="text-[12.5px] text-fg-muted">내가 좋아했던 분위기의 영화들이에요</span>
        </div>
        <div
          class="rail flex gap-[18px] overflow-x-auto pb-3"
          @pointerdown="railDown"
          @pointermove="railMove"
          @pointerup="railUp"
          @pointerleave="railUp"
        >
          <button
            v-for="m in data.safe"
            :key="m.id"
            type="button"
            class="group/c w-[184px] shrink-0 text-left"
            @click="onCardClick(m.id)"
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
                class="grid-tex absolute inset-0 opacity-30"
              />
              <div class="absolute inset-0 sheen opacity-0 transition-opacity duration-500 group-hover/c:opacity-100" />
            </div>
            <div class="mt-2 truncate text-[13.5px] font-semibold text-fg">
              {{ m.title }}
            </div>
            <div class="mt-0.5 text-[12px] text-fg-muted">
              {{ m.release_year || "" }} · <span class="text-gold">★</span> {{ m.vote_average }}
            </div>
          </button>
        </div>
      </section>

      <!-- ───────── 미탐색 추천 ───────── -->
      <section class="mt-9">
        <div class="mb-4 flex items-baseline gap-3">
          <h2 class="flex items-center gap-2 font-display text-[17px] font-semibold tracking-tightest text-fg">
            🧭 새로운 취향
          </h2>
          <span class="text-[12.5px] text-gold">필터 버블 밖 — 안 가본 취향의 영역</span>
        </div>
        <div
          class="rail flex gap-[18px] overflow-x-auto pb-3"
          @pointerdown="railDown"
          @pointermove="railMove"
          @pointerup="railUp"
          @pointerleave="railUp"
        >
          <button
            v-for="m in unexploredList"
            :key="m.id"
            type="button"
            class="group/c w-[184px] shrink-0 text-left"
            @click="onCardClick(m.id)"
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
                class="grid-tex absolute inset-0 opacity-30"
              />
              <div class="absolute inset-0 sheen opacity-0 transition-opacity duration-500 group-hover/c:opacity-100" />
            </div>
            <div class="mt-2 truncate text-[13.5px] font-semibold text-fg">
              {{ m.title }}
            </div>
            <div class="mt-0.5 text-[12px] text-fg-muted">
              {{ m.release_year || "" }} · <span class="text-gold">★</span> {{ m.vote_average }}
            </div>
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.rail { cursor: grab; }
.rail:active { cursor: grabbing; }
/* 드래그 중 이미지 고스트/선택 방지 */
.rail img { user-select: none; -webkit-user-drag: none; pointer-events: none; }
</style>
