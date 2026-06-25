<script setup>
// 메인(홈) 페이지 (화면 04, 김호준) — ① 내 취향 지도 프리뷰(대형, 탭→지도 페이지)
// ② 최근 추가된 영화(우리 DB created_at 신규순, 가로 스크롤). 카드 클릭 → 영화 상세.
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getMyMap } from "@/api/taste";
import { getRecentMovies } from "@/api/movies";
import { getFriends } from "@/api/social";
import TasteMapCanvas from "@/components/TasteMapCanvas.vue";

const router = useRouter();
const map = ref(null);          // { enough, watched:[...], summary }
const recent = ref([]);
const friendCount = ref(0);     // 프리뷰 밑 통계용(실패 시 0)
const loading = ref(true);
const IMG = "https://image.tmdb.org/t/p/w300";

onMounted(async () => {
  try {
    [map.value, recent.value] = await Promise.all([getMyMap(), getRecentMovies(12)]);
    getFriends().then((f) => { friendCount.value = f.length; }).catch(() => {});  // 통계 보조(실패 무시)
  } finally {
    loading.value = false;
  }
});

// 프리뷰 밑 통계 — 모두 프론트 데이터로 계산. 별점은 10점 만점 표기(저장값 0.5~5 → ×2).
const avgRating = computed(() => {
  const ws = map.value?.watched || [];
  if (!ws.length) return "0.0";
  return (ws.reduce((a, w) => a + Number(w.rating), 0) / ws.length * 2).toFixed(1);
});
// 평균 별점(10점) 2점 구간별 호칭.
const ratingTitle = computed(() => {
  const r = Number(avgRating.value);
  if (r < 2) return "지독한 혹평가";
  if (r < 4) return "깐깐한 비평가";
  if (r < 6) return "균형 잡힌 관객";
  if (r < 8) return "너그러운 애호가";
  return "별점 인심 만렙";
});

function poster(p) {
  return p ? IMG + p : "";
}
function goMap() {
  router.push({ name: "map" });
}
function openMovie(id) {
  router.push({ name: "movie-detail", params: { id } });
}
function goRegister() {
  router.push({ name: "movies" });
}
</script>

<template>
  <div class="mx-auto max-w-[1500px] px-6 pb-28 pt-10 lg:px-10">
    <!-- ───────── HERO HEADER ───────── -->
    <section class="mb-6 flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
      <div class="min-w-0 flex-1">
        <div class="mb-3 flex items-center gap-2.5 font-sans text-[11px] uppercase tracking-[0.14em] text-fg-muted">
          <span class="h-px w-7 bg-gold/60" />내 취향 지도 · Taste constellation
        </div>
        <h1 class="font-display text-[32px] font-semibold leading-[1.16] tracking-tightest sm:text-[42px]">
          당신이 본 영화가<br> <span class="text-fg-muted">하나의 별자리가</span><br> 됩니다
        </h1>
      </div>
      <p class="max-w-[300px] text-[13.5px] leading-relaxed text-fg-muted">
        평점과 감정을 좌표로, 본 영화가 밤하늘에 흩어졌어요.<br>가까운 별일수록 취향이 닮아 있습니다.
      </p>
    </section>

    <p
      v-if="loading"
      class="py-16 text-center text-[14px] text-fg-muted"
    >
      불러오는 중…
    </p>

    <template v-else>
      <!-- ───────── 지도 프리뷰 카드 ───────── -->
      <template v-if="map.enough">
      <button
        type="button"
        class="group relative block w-full overflow-hidden rounded-2xl border border-line bg-ink-800 text-left transition hover:border-lineHover"
        @click="goMap"
      >
        <div class="grid-tex pointer-events-none absolute inset-0 opacity-60" />
        <div
          class="pointer-events-none absolute inset-0"
          style="background:radial-gradient(120% 90% at 30% 20%, rgba(230,181,102,0.10), transparent 55%), radial-gradient(100% 120% at 90% 110%, rgba(93,202,165,0.07), transparent 50%);"
        />
        <TasteMapCanvas
          :watched="map.watched"
          :interactive="false"
          :show-star-labels="false"
          :width="1040"
          :height="376"
          class="mapwrap relative block"
        />
        <!-- bottom bar -->
        <div class="relative flex flex-wrap items-center justify-between gap-3 border-t border-line bg-ink-800/60 px-5 py-3.5 backdrop-blur">
          <div class="flex items-center gap-5 font-mono text-[11px] text-fg-muted">
            <span class="flex items-center gap-1.5"><span class="h-1.5 w-1.5 rounded-full bg-[#FFF0CD]" />인생작</span>
            <span class="flex items-center gap-1.5"><span class="h-1.5 w-1.5 rounded-full bg-[#5DCAA5]" />인상적</span>
            <span class="flex items-center gap-1.5"><span class="h-1.5 w-1.5 rounded-full bg-[#C9D0E0]" />무난함</span>
          </div>
          <span class="flex items-center gap-1.5 rounded-full border border-lineHover bg-white/[0.04] px-4 py-1.5 text-[12.5px] font-medium text-fg transition group-hover:bg-white/[0.08]">
            지도 자세히 보기
            <svg
              viewBox="0 0 24 24"
              class="h-3.5 w-3.5"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            ><path
              d="M5 12h14M13 6l6 6-6 6"
              stroke-linecap="round"
              stroke-linejoin="round"
            /></svg>
          </span>
        </div>
      </button>

      <!-- 프리뷰 밑 통계: 본 영화 · 평균 별점 · 친구 (모두 프론트 계산) -->
      <div class="mt-4 grid grid-cols-3 gap-3">
        <div class="rounded-xl border border-line bg-ink-800 px-4 py-3.5">
          <div class="font-sans text-[11px] tracking-[0.04em] text-fg-muted">
            본 영화
          </div>
          <div class="mt-1 font-display text-[22px] font-semibold text-fg">
            {{ map.watched.length }}<span class="ml-0.5 text-[14px] font-normal text-fg-muted">편</span>
          </div>
        </div>
        <div class="rounded-xl border border-line bg-ink-800 px-4 py-3.5">
          <div class="font-sans text-[11px] tracking-[0.04em] text-fg-muted">
            평균 별점
          </div>
          <div class="mt-1 font-display text-[22px] font-semibold text-fg">
            <span class="text-gold">★</span> {{ avgRating }}<span class="ml-0.5 text-[13px] font-normal text-fg-muted">/ 10</span>
          </div>
          <div class="mt-0.5 text-[11px] font-medium text-gold">
            {{ ratingTitle }}
          </div>
        </div>
        <div class="rounded-xl border border-line bg-ink-800 px-4 py-3.5">
          <div class="font-sans text-[11px] tracking-[0.04em] text-fg-muted">
            친구
          </div>
          <div class="mt-1 font-display text-[22px] font-semibold text-fg">
            {{ friendCount }}<span class="ml-0.5 text-[14px] font-normal text-fg-muted">명</span>
          </div>
        </div>
      </div>
      </template>

      <!-- 빈 상태(5편 미만) -->
      <div
        v-else
        class="flex min-h-[240px] flex-col items-center justify-center gap-4 rounded-2xl border border-line bg-ink-800 p-8 text-center"
      >
        <p class="text-[14px] text-fg-muted">
          아직 취향 지도가 없어요. 영화 <b class="text-fg">5편 이상</b>을 등록하면 별이 빛나기 시작해요.
        </p>
        <button
          type="button"
          class="rounded-lg bg-gold px-6 py-2.5 text-[14px] font-semibold text-ink transition hover:bg-gold-soft"
          @click="goRegister"
        >
          영화 등록하러 가기
        </button>
      </div>

      <!-- ───────── 최근 추가된 영화 ───────── -->
      <section class="mt-14">
        <div class="mb-5 flex items-end justify-between">
          <div>
            <div class="mb-2 flex items-center gap-2.5 font-mono text-[11px] uppercase tracking-[0.22em] text-fg-faint">
              <span class="h-px w-7 bg-gold/60" />Recently added
            </div>
            <h2 class="font-display text-[22px] font-semibold tracking-tightest">
              최근 추가된 영화
            </h2>
          </div>
        </div>

        <div
          v-if="recent.length"
          class="flex gap-4 overflow-x-auto pb-2"
        >
          <button
            v-for="m in recent"
            :key="m.id"
            type="button"
            class="group/c w-[150px] shrink-0 text-left"
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
                class="grid-tex absolute inset-0 opacity-30"
              />
              <div class="absolute inset-0 sheen opacity-0 transition-opacity duration-500 group-hover/c:opacity-100" />
              <div class="absolute right-3 top-3 rounded-full border border-line bg-ink/60 px-1.5 py-0.5 font-mono text-[9.5px] text-gold backdrop-blur">
                NEW
              </div>
            </div>
            <div class="mt-2.5 flex items-center justify-between gap-2">
              <span class="truncate text-[12.5px] text-fg">{{ m.title }}</span>
              <span class="shrink-0 font-mono text-[11px] text-fg-faint">{{ m.release_year || "" }}</span>
            </div>
          </button>
        </div>
        <p
          v-else
          class="py-10 text-center text-[14px] text-fg-muted"
        >
          아직 등록된 영화가 없습니다.
        </p>
      </section>
    </template>
  </div>
</template>

<style scoped>
/* 지도 프리뷰 SVG는 카드 폭에 맞춰 자연 비율로 채운다(레터박스 없음). */
.mapwrap :deep(.mapsvg) {
  width: 100%;
  height: auto;
  display: block;
}
</style>
