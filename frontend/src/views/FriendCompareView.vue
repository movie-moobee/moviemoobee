<script setup>
// 친구 프로필 상세 (F-FRD-04, 와이어프레임 13) — 프로필·취향 비교 지도(5.3)·같이 볼 영화 챗봇(5.4)·시청작.
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getCowatchCandidates, getCowatchUsage, getFriendCompare, getFriendProfile, unfriend } from "@/api/social";
import { streamChat } from "@/api/chat";
import RatingStars from "@/components/base/RatingStars.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import TasteMapCanvas from "@/components/TasteMapCanvas.vue";
import ChatPanel from "@/components/ChatPanel.vue";

const route = useRoute();
const router = useRouter();

const profile = ref(null);
const compare = ref(null);   // 취향 비교 지도 데이터(5.3) — 프로필과 별도 로드
const cowatchCands = ref([]);    // 챗봇 추천 매칭용 후보(좌표 포함, 5.4)
const mappedRecs = ref([]);      // 챗봇이 추천 → '지도에 표시'한 영화들 (비교 지도에 오버레이)
const quota = ref(null);         // 챗봇 일일 사용량 { used, limit } (5.4)
function onUsage(u) { quota.value = u; }
const loading = ref(true);
const error = ref("");
const confirming = ref(false);
const unfriending = ref(false);

const IMG = "https://image.tmdb.org/t/p/w300";

// 두 사람 취향 장르 교집합(겹치는 장르) — 비교 요약 한 줄.
const commonGenres = computed(() => {
  if (!compare.value) return [];
  const f = new Set(compare.value.friend.main);
  return compare.value.me.main.filter((g) => f.has(g));
});

// 메인 취향 지도(TasteMapCanvas)에 두 사람 별을 함께 얹기 위한 병합 배열.
// movie_id 로 합쳐 주인(owner) 판정: 둘 다=shared / 나만=mine / 친구만=theirs. 양쪽 별점 보존.
const compareWatched = computed(() => {
  if (!compare.value) return [];
  const shared = new Set(compare.value.shared_ids);
  const byId = new Map();
  for (const m of compare.value.me.watched)
    byId.set(m.movie_id, { ...m, owner: shared.has(m.movie_id) ? "shared" : "mine", myRating: m.rating });
  for (const m of compare.value.friend.watched) {
    const ex = byId.get(m.movie_id);
    if (ex) ex.friendRating = m.rating;                 // 공통작 — 친구 별점 합치기
    else byId.set(m.movie_id, { ...m, owner: "theirs", friendRating: m.rating });
  }
  return [...byId.values()];
});
// 챗봇 '지도에 표시' 추천작 → TasteMapCanvas 핀(kind 'rec', 보라 오버레이).
const recPins = computed(() => mappedRecs.value.map((m) => ({ ...m, kind: "rec" })));

// 비교 지도 강조 토글 — 내 시청(mine)·친구 시청(theirs)·공통(shared) 별을 켜고 끄며 강조.
const twinkle = ref(new Set());
function toggleTwinkle(owner) {
  const s = new Set(twinkle.value);
  s.has(owner) ? s.delete(owner) : s.add(owner);
  twinkle.value = s;
}
const twinkleToggles = computed(() => [
  { owner: "mine", label: "나", color: "#ff9ecb" },
  { owner: "theirs", label: profile.value?.nickname || "친구", color: "#7fe0d6" },
  { owner: "shared", label: "공통", color: "#ffd21e" },
]);

// 같이 볼 영화 챗봇(5.4) — ChatPanel 에 주입할 SSE 스트림 함수.
function cowatchStream(history, onDelta) {
  return streamChat(`/social/friends/${route.params.id}/cowatch/`, history, onDelta);
}

// 봇 답변 텍스트에서 추천작 '여러 편' 찾기 — 후보(grounding 목록) 제목이 들어있는 영화 전부.
// 후보 안에서만 추천하므로 신뢰 가능. 다른 매칭 제목의 부분집합인 제목은 제거
// (예: '프레데터' ⊂ '프레데터: 죽음의 땅' → 짧은 쪽 버림).
function resolveRecommendation(text) {
  if (!text) return [];
  const hits = cowatchCands.value.filter((c) => c.title && text.includes(c.title));
  return hits.filter((c) => !hits.some((o) => o !== c && o.title.includes(c.title)));
}
// [지도에 표시하기] 클릭 → 토글(다시 누르면 지도에서 내림)
function showOnMap(m) {
  const has = mappedRecs.value.some((x) => x.id === m.id);
  mappedRecs.value = has
    ? mappedRecs.value.filter((x) => x.id !== m.id)
    : [...mappedRecs.value, m];
}
const mappedIds = computed(() => mappedRecs.value.map((x) => x.id));

async function load(id) {
  loading.value = true;
  error.value = "";
  compare.value = null;
  cowatchCands.value = [];
  mappedRecs.value = [];
  try {
    profile.value = await getFriendProfile(id);
    compare.value = await getFriendCompare(id);   // 프로필 성공 후(친구확인됨) 비교 지도
    getCowatchCandidates(id).then((c) => { cowatchCands.value = c; }).catch(() => {});  // 챗봇 추천 매칭용(실패 무시)
    getCowatchUsage().then((u) => { quota.value = u; }).catch(() => {});  // 챗봇 일일 사용량 초기 표시(실패 무시)
  } catch (e) {
    error.value =
      e?.response?.status === 403
        ? "친구만 볼 수 있는 프로필입니다."
        : "프로필을 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
}

onMounted(() => load(route.params.id));
// /friends/:id 간 직접 이동 대비 id 변경 시 재로드
watch(() => route.params.id, (id) => id && load(id));

async function confirmUnfriend() {
  if (unfriending.value) return;
  unfriending.value = true;
  try {
    await unfriend(route.params.id);
    router.push({ name: "friends" });
  } catch {
    error.value = "친구 끊기에 실패했습니다.";
    confirming.value = false;
  } finally {
    unfriending.value = false;
  }
}

function initial(nickname) {
  return (nickname || "?").trim().charAt(0).toUpperCase();
}
function poster(p) {
  return p ? IMG + p : "";
}
</script>

<template>
  <div class="mx-auto max-w-[1500px] px-6 pb-28 pt-10 lg:px-10">
    <p
      v-if="loading"
      class="py-16 text-center text-[14px] text-fg-muted"
    >
      불러오는 중…
    </p>
    <p
      v-else-if="error"
      class="py-16 text-center text-[14px] text-danger"
    >
      {{ error }}
    </p>

    <template v-else-if="profile">
      <!-- 헤더 -->
      <header class="mb-6 flex items-center gap-4">
        <div class="grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-full border border-line bg-ink-700 text-[24px] font-bold text-fg-muted">
          <img
            v-if="profile.profile_image_url"
            :src="profile.profile_image_url"
            :alt="profile.nickname"
            class="h-full w-full object-cover"
          >
          <span v-else>{{ initial(profile.nickname) }}</span>
        </div>
        <div class="min-w-0 flex-1">
          <h1 class="font-display text-[24px] font-semibold tracking-tightest text-fg">
            {{ profile.nickname }}
          </h1>
          <p class="mt-1.5 text-[13px] text-fg-muted">
            본 영화 {{ profile.watch_count }}편<template v-if="compare && compare.friend.main.length">
              · 주취향 {{ compare.friend.main.join(" · ") }}
            </template>
          </p>
        </div>
        <button
          type="button"
          class="shrink-0 whitespace-nowrap rounded-lg border border-line px-4 py-2 text-[13px] font-semibold text-danger transition hover:border-danger"
          @click="confirming = true"
        >
          친구 삭제
        </button>
      </header>

      <!-- 취향 비교 지도 (5.3) -->
      <section
        v-if="compare"
        class="mb-10"
      >
        <div class="mb-3">
          <h2 class="font-display text-[17px] font-semibold tracking-tightest text-fg">
            취향 비교 지도 <span class="text-[13px] font-normal text-fg-muted">— 나 vs {{ profile.nickname }}</span>
          </h2>
          <p class="mt-1.5 text-[13px] text-fg-muted">
            같은 지도 위에 두 사람이 본 영화를 겹쳐 봤어요.
            <template v-if="compare.shared_ids.length">
              <b class="font-semibold text-fg">둘 다 본 영화 {{ compare.shared_ids.length }}편</b>
            </template>
            <template v-else>
              아직 둘 다 본 영화는 없네요
            </template>
            <template v-if="commonGenres.length">
              · 공통 취향 <b class="font-semibold text-fg">{{ commonGenres.join(" · ") }}</b>
            </template>
          </p>
        </div>
        <div class="grid max-w-[1500px] items-stretch gap-[18px] lg:grid-cols-[1fr_340px]">
          <div>
            <!-- 메인 취향 지도와 동일한 렌더러(TasteMapCanvas). 별 색만 주인별(owner 모드). -->
            <div class="relative overflow-hidden rounded-2xl border border-line bg-ink-800">
              <!-- 강조 토글(우측 상단): 누르면 해당 별을 크게·밝게 강조, 나머지는 흐리게 -->
              <div class="absolute right-4 top-4 z-10 flex flex-col items-end gap-1.5">
                <span class="font-sans text-[10px] tracking-[0.06em] text-fg-faint">별 강조</span>
                <div class="flex gap-1.5">
                  <button
                    v-for="t in twinkleToggles"
                    :key="t.owner"
                    type="button"
                    class="flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] font-medium shadow-[0_2px_10px_rgba(0,0,0,0.5)] backdrop-blur transition"
                    :class="twinkle.has(t.owner) ? 'border-lineHover bg-ink-600/90 text-fg' : 'border-line bg-ink-700/80 text-fg-muted hover:text-fg'"
                    @click="toggleTwinkle(t.owner)"
                  >
                    <span
                      class="h-2.5 w-2.5 rounded-full"
                      :style="{ background: t.color, boxShadow: twinkle.has(t.owner) ? `0 0 8px ${t.color}` : 'none' }"
                    />{{ t.label }}
                  </button>
                </div>
              </div>
              <TasteMapCanvas
                :watched="compareWatched"
                :anchors="compare.anchors"
                :pins="recPins"
                :width="980"
                :height="560"
                color-by="owner"
                :friend-name="profile.nickname"
                :twinkle-owners="[...twinkle]"
                class="mapwrap relative block"
                @pin-click="(m) => router.push({ name: 'movie-detail', params: { id: m.id } })"
                @open-detail="(m) => router.push({ name: 'movie-detail', params: { id: m.movie_id } })"
              />
            </div>
          </div>
          <ChatPanel
            title="같이 볼 영화 AI"
            subtitle="두 분 취향을 분석해 추천해요"
            :intro="`${profile.nickname}님과 같이 볼 영화가 궁금하면 물어봐! 두 사람 취향이 만나는 작품으로 골라줄게.`"
            placeholder="예) 가볍게 볼 만한 거 추천해줘"
            :stream-fn="cowatchStream"
            :resolve-fn="resolveRecommendation"
            :mapped-ids="mappedIds"
            :quota="quota"
            @show-on-map="showOnMap"
            @usage="onUsage"
          />
        </div>
      </section>

      <!-- 친구의 시청작 -->
      <section>
        <div class="mb-4 flex items-baseline gap-2.5 border-b border-line pb-2.5">
          <h2 class="font-display text-[15px] font-semibold tracking-tightest text-fg">
            {{ profile.nickname }} 님이 본 영화
          </h2>
          <span class="font-mono text-[11px] text-fg-faint">{{ profile.watched.length }}편 · 최신순</span>
        </div>
        <div
          v-if="profile.watched.length"
          class="grid gap-[14px]"
          style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr))"
        >
          <button
            v-for="m in profile.watched"
            :key="m.id"
            type="button"
            class="group/c flex flex-col gap-1.5 text-left"
            @click="router.push({ name: 'movie-detail', params: { id: m.id } })"
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
                class="flex h-full w-full items-center justify-center p-2 text-center text-[11px] text-fg-muted"
              >
                {{ m.title }}
              </div>
            </div>
            <p class="truncate text-[12.5px] font-semibold text-fg">
              {{ m.title }}
            </p>
            <RatingStars
              :model-value="Number(m.rating)"
              readonly
              :size="13"
            />
          </button>
        </div>
        <p
          v-else
          class="py-2 text-[14px] text-fg-muted"
        >
          아직 본 영화가 없습니다.
        </p>
      </section>
    </template>

    <!-- 친구 끊기 확인 -->
    <ConfirmDialog
      v-if="confirming"
      title="친구를 삭제할까요?"
      :message="`'${profile?.nickname}' 님과 친구를 끊습니다.`"
      confirm-label="친구 삭제"
      cancel-label="취소"
      :danger="true"
      :busy="unfriending"
      @confirm="confirmUnfriend"
      @cancel="confirming = false"
    />
  </div>
</template>

<style scoped>
/* 비교 지도 SVG는 프레임 폭에 맞춰 자연 비율로 채운다(메인 지도와 동일). */
.mapwrap :deep(.mapsvg) {
  width: 100%;
  height: auto;
  display: block;
}
</style>
