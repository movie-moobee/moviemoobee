<script setup>
// 친구 프로필 상세 (F-FRD-04, 와이어프레임 13) — 프로필·취향 비교 지도(5.3)·같이 볼 영화 챗봇(5.4)·시청작.
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getCowatchCandidates, getFriendCompare, getFriendProfile, unfriend } from "@/api/social";
import { streamChat } from "@/api/chat";
import RatingStars from "@/components/base/RatingStars.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import FriendCompareMap from "@/components/FriendCompareMap.vue";
import ChatPanel from "@/components/ChatPanel.vue";

const route = useRoute();
const router = useRouter();

const profile = ref(null);
const compare = ref(null);   // 취향 비교 지도 데이터(5.3) — 프로필과 별도 로드
const cowatchCands = ref([]);    // 챗봇 추천 매칭용 후보(좌표 포함, 5.4)
const mappedRecs = ref([]);      // 챗봇이 추천 → '지도에 표시'한 영화들 (비교 지도에 오버레이)
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
  <div class="friend-profile">
    <p
      v-if="loading"
      class="msg"
    >
      불러오는 중…
    </p>
    <p
      v-else-if="error"
      class="msg msg--error"
    >
      {{ error }}
    </p>

    <template v-else-if="profile">
      <!-- 헤더 -->
      <header class="head">
        <div class="avatar">
          <img
            v-if="profile.profile_image_url"
            :src="profile.profile_image_url"
            :alt="profile.nickname"
          >
          <span v-else>{{ initial(profile.nickname) }}</span>
        </div>
        <div class="head__info">
          <h1 class="nick">
            {{ profile.nickname }}
          </h1>
          <p class="meta">
            본 영화 {{ profile.watch_count }}편<template v-if="compare && compare.friend.main.length">
              · 주취향 {{ compare.friend.main.join(" · ") }}
            </template>
          </p>
        </div>
        <button
          class="btn btn--danger"
          type="button"
          @click="confirming = true"
        >
          친구 삭제
        </button>
      </header>

      <!-- 취향 비교 지도 (5.3) -->
      <section
        v-if="compare"
        class="compare"
      >
        <div class="compare__head">
          <h2 class="compare__title">
            취향 비교 지도 <span class="compare__vs">— 나 vs {{ profile.nickname }}</span>
          </h2>
          <p class="compare__sub">
            같은 지도 위에 두 사람이 본 영화를 겹쳐 봤어요.
            <template v-if="compare.shared_ids.length">
              <b>둘 다 본 영화 {{ compare.shared_ids.length }}편</b>
            </template>
            <template v-else>
              아직 둘 다 본 영화는 없네요
            </template>
            <template v-if="commonGenres.length">
              · 공통 취향 <b>{{ commonGenres.join(" · ") }}</b>
            </template>
          </p>
        </div>
        <div class="compare__grid">
          <FriendCompareMap
            :anchors="compare.anchors"
            :mine="compare.me.watched"
            :theirs="compare.friend.watched"
            :shared-ids="compare.shared_ids"
            :friend-name="profile.nickname"
            :recommended="mappedRecs"
          />
          <ChatPanel
            title="같이 볼 영화 AI"
            subtitle="두 분 취향을 분석해 추천해요"
            :intro="`${profile.nickname}님과 같이 볼 영화가 궁금하면 물어봐! 두 사람 취향이 만나는 작품으로 골라줄게.`"
            placeholder="예) 가볍게 볼 만한 거 추천해줘"
            :stream-fn="cowatchStream"
            :resolve-fn="resolveRecommendation"
            :mapped-ids="mappedIds"
            @show-on-map="showOnMap"
          />
        </div>
      </section>

      <!-- 친구의 시청작 -->
      <section class="watched">
        <div class="watched__title">
          {{ profile.nickname }} 님이 본 영화
          <span class="hint">{{ profile.watched.length }}편 · 최신순</span>
        </div>
        <div
          v-if="profile.watched.length"
          class="grid"
        >
          <button
            v-for="m in profile.watched"
            :key="m.id"
            class="card"
            type="button"
            @click="router.push({ name: 'movie-detail', params: { id: m.id } })"
          >
            <img
              v-if="poster(m.poster_path)"
              :src="poster(m.poster_path)"
              :alt="m.title"
              class="card__poster"
            >
            <div
              v-else
              class="card__poster card__poster--empty"
            >
              {{ m.title }}
            </div>
            <p class="card__title">
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
          class="msg msg--left"
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
.friend-profile {
  width: 100%;
  max-width: var(--page-max);
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
.msg--left {
  text-align: left;
  padding: 8px 0;
}

/* 헤더 */
.head {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 6px 0 22px;
}
.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-alt, #2a2a2a);
  color: var(--text-muted);
  font-size: 24px;
  font-weight: 700;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.head__info {
  flex: 1;
  min-width: 0;
}
.nick {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}
.meta {
  font-size: 13px;
  color: var(--text-muted);
  margin: 6px 0 0;
}
.btn {
  font-family: var(--font);
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: none;
  color: var(--text);
  cursor: pointer;
}
.btn--danger {
  color: var(--danger);
}
.btn--danger:hover {
  border-color: var(--danger);
}

/* 비교 지도 (5.3) */
.compare {
  margin-bottom: 26px;
}
.compare__head {
  margin-bottom: 12px;
}
.compare__grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 18px;
  align-items: start;
  /* 비교 지도는 640×430 디자인 — 지도 컬럼이 native 크기 근처에 머물도록 블록 폭 제한 */
  max-width: 1500px;
}
@media (max-width: 820px) {
  .compare__grid {
    grid-template-columns: 1fr;
  }
}
.compare__title {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
}
.compare__vs {
  font-size: 13px;
  font-weight: 400;
  color: var(--text-muted);
}
.compare__sub {
  font-size: 13px;
  color: var(--text-muted);
  margin: 6px 0 0;
}
.compare__sub b {
  color: var(--text);
  font-weight: 600;
}

/* 시청작 */
.watched__title {
  font-size: 15px;
  font-weight: 700;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}
.hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
}
.grid {
  display: grid;
  /* 고정 5칸이면 컨테이너가 넓을 때 포스터가 과하게 커진다 → 칸 크기 고정, 칸 수 자동 */
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 14px;
}
.card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0;
  background: none;
  border: 0;
  cursor: pointer;
  text-align: left;
}
.card__poster {
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  border-radius: var(--radius-sm);
  background: var(--surface-alt, #2a2a2a);
}
.card__poster--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--text-muted);
  padding: 6px;
}
.card__title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
