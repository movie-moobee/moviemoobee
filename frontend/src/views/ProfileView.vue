<script setup>
// 내 프로필 (와이어프레임 08 / F-AUTH). 아바타·닉네임·통계 + 내가 본 영화 그리드.
// 프로필 수정·계정 삭제는 /me/edit(EditProfileView).
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { getMe, logout } from "@/api/auth";
import { listWatchRecords } from "@/api/watchRecords";
import { useCurrentUser } from "@/composables/useCurrentUser";
import RatingStars from "@/components/base/RatingStars.vue";

const router = useRouter();
const { clearUser } = useCurrentUser();
const me = ref(null);
const records = ref([]);
const loading = ref(true);
const loggingOut = ref(false);

const IMG = "https://image.tmdb.org/t/p/w300";

onMounted(async () => {
  try {
    const [profile, recs] = await Promise.all([getMe(), listWatchRecords()]);
    me.value = profile;
    records.value = Array.isArray(recs) ? recs : recs.results ?? [];
  } finally {
    loading.value = false;
  }
});

async function onLogout() {
  loggingOut.value = true;
  try {
    await logout();
    clearUser();
  } finally {
    router.push("/login");
  }
}
</script>

<template>
  <div class="profile">
    <p
      v-if="loading"
      class="msg"
    >
      불러오는 중…
    </p>

    <template v-else-if="me">
      <!-- 헤더 -->
      <header class="head">
        <img
          v-if="me.profile_image_url"
          :src="me.profile_image_url"
          :alt="me.nickname"
          class="avatar"
        >
        <div
          v-else
          class="avatar avatar--empty"
        >
          {{ (me.nickname || "?").charAt(0) }}
        </div>
        <h1 class="nick">
          {{ me.nickname }}
        </h1>
        <div class="actions">
          <button
            class="btn"
            type="button"
            @click="router.push({ name: 'profile-edit' })"
          >
            프로필 수정
          </button>
          <button
            class="btn"
            type="button"
            :disabled="loggingOut"
            @click="onLogout"
          >
            {{ loggingOut ? "로그아웃 중…" : "로그아웃" }}
          </button>
        </div>
        <div class="stats">
          <div class="stat">
            <div class="stat__num">
              {{ records.length }}
            </div>
            <div class="stat__label">
              본 영화
            </div>
          </div>
          <div class="stat">
            <div class="stat__num">
              {{ me.friend_count ?? 0 }}
            </div>
            <div class="stat__label">
              친구
            </div>
          </div>
        </div>
      </header>

      <!-- 내가 본 영화 -->
      <section class="watched">
        <div class="watched__title">
          내가 본 영화 <span class="hint">{{ records.length }}편 · 최신순</span>
        </div>
        <div
          v-if="records.length"
          class="grid"
        >
          <button
            v-for="r in records"
            :key="r.id"
            class="card"
            type="button"
            @click="router.push({ name: 'movie-detail', params: { id: r.movie_detail.id } })"
          >
            <img
              v-if="r.movie_detail.poster_path"
              :src="IMG + r.movie_detail.poster_path"
              :alt="r.movie_detail.title"
              class="card__poster"
            >
            <div
              v-else
              class="card__poster card__poster--empty"
            >
              {{ r.movie_detail.title }}
            </div>
            <div class="card__title">
              {{ r.movie_detail.title }}
            </div>
            <RatingStars
              :model-value="Number(r.rating)"
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
  </div>
</template>

<style scoped>
.profile {
  max-width: 860px;
  margin: 0 auto;
  padding: 28px 24px 60px;
}
.msg {
  color: var(--text-muted);
  font-size: 14px;
  padding: 60px 0;
  text-align: center;
}
.msg--left {
  text-align: left;
  padding: 8px 0;
}
/* 헤더 */
.head {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 10px 0 26px;
}
.avatar {
  width: 104px;
  height: 104px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--surface-2);
}
.avatar--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 38px;
  font-weight: 700;
  color: var(--text-muted);
}
.nick {
  font-size: 20px;
  font-weight: 700;
  margin: 16px 0 0;
}
.actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}
.btn {
  font-family: var(--font);
  font-size: 13px;
  color: var(--text);
  padding: 8px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border-hover);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.btn:hover:not(:disabled) {
  border-color: var(--text-muted);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.stats {
  display: flex;
  gap: 48px;
  margin-top: 20px;
}
.stat__num {
  font-size: 18px;
  font-weight: 700;
}
.stat__label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
/* 본 영화 */
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
  grid-template-columns: repeat(5, 1fr);
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
  background: var(--surface-2);
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
  color: var(--text);
  line-height: 1.35;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
@media (max-width: 680px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
