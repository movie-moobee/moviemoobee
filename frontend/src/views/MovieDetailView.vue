<script setup>
// 영화 상세 (F-MOV-02 메타 / F-MOV-03 OTT / 예고편 / F-WAT-01 시청 등록).
// 이용자 리뷰(F-MOV-04)는 2.4에서 추가.
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import { getMovie, getMovieExtras } from "@/api/movies";
import RatingStars from "@/components/base/RatingStars.vue";
import WatchRecordModal from "@/components/WatchRecordModal.vue";

const route = useRoute();
const movie = ref(null);
const extras = ref({ ott: [] });
const myRecord = ref(null); // 내 시청기록(있으면 수정, 없으면 등록). 상세 응답 my_record에서.
const showModal = ref(false);
const loading = ref(true); // 영화 메타(DB, 예고편 포함) — 이게 끝나면 화면을 그림
const extrasLoading = ref(true); // OTT(TMDB 실시간) — 본문을 막지 않고 따로 채움
const error = ref("");

const IMG = "https://image.tmdb.org/t/p/w500";
const LOGO = "https://image.tmdb.org/t/p/w92";

const meta = computed(() => {
  if (!movie.value) return "";
  const m = movie.value;
  return [
    m.release_year,
    m.genres?.join("/"),
    m.runtime ? `${m.runtime}분` : null,
    m.director,
  ].filter(Boolean).join(" · ");
});

onMounted(async () => {
  const { id } = route.params;

  // 1) 영화 메타 먼저 — DB라 즉시. 끝나는 즉시 화면을 그린다.
  try {
    movie.value = await getMovie(id);
    myRecord.value = movie.value.my_record; // null이면 미등록
  } catch {
    error.value = "영화 정보를 불러오지 못했습니다.";
    return;
  } finally {
    loading.value = false;
  }

  // 2) OTT는 화면을 막지 않고 따로 — 실패해도 본문은 유지.
  try {
    extras.value = await getMovieExtras(id);
  } catch {
    // OTT 실패는 치명적이지 않음 — 빈 상태로 둠
  } finally {
    extrasLoading.value = false;
  }
});

// 등록/수정 저장 완료 — 모달이 API 처리 후 record를 넘겨줌. 상세 UI 즉시 갱신.
function onSaved(rec) {
  myRecord.value = {
    id: rec.id,
    rating: rec.rating,
    review: rec.review,
    watched_on: rec.watched_on,
  };
  showModal.value = false;
}
</script>

<template>
  <div class="detail">
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

    <template v-else-if="movie">
      <!-- 헤더: 포스터 + 메타 -->
      <div class="hero">
        <div class="hero__poster">
          <img
            v-if="movie.poster_path"
            :src="IMG + movie.poster_path"
            :alt="movie.title"
          >
        </div>
        <div class="hero__info">
          <h1>{{ movie.title }}</h1>
          <div class="meta">
            {{ meta }}
          </div>

          <div
            v-if="movie.genres?.length || movie.keywords?.length"
            class="chips"
          >
            <span
              v-for="g in movie.genres"
              :key="`g-${g}`"
              class="chip chip--genre"
            >{{ g }}</span>
            <span
              v-for="k in movie.keywords"
              :key="`k-${k}`"
              class="chip"
            >{{ k }}</span>
          </div>

          <div class="ratings">
            <div class="rating">
              <span class="rating__star">⭐</span>
              <span class="rating__num">{{ movie.vote_average ?? "-" }}</span>
              <span class="rating__den">/ 10 · TMDB</span>
            </div>
            <div
              v-if="myRecord"
              class="rating rating--mine"
            >
              <span class="rating__label">내 별점</span>
              <RatingStars
                :model-value="Number(myRecord.rating)"
                readonly
                :size="18"
              />
            </div>
          </div>

          <p
            v-if="movie.cast?.length"
            class="cast"
          >
            출연: {{ movie.cast.join(", ") }}
          </p>

          <!-- 시청 등록/수정 (F-WAT-01) -->
          <div class="watch">
            <template v-if="myRecord">
              <span class="watch__badge">✓ 시청영화로 등록됨</span>
              <button
                class="watch__btn"
                type="button"
                @click="showModal = true"
              >
                ★ 별점·리뷰 수정
              </button>
            </template>
            <button
              v-else
              class="watch__btn watch__btn--add"
              type="button"
              @click="showModal = true"
            >
              ＋ 시청영화 등록 · 별점 매기기
            </button>
          </div>
        </div>
      </div>

      <!-- 줄거리 -->
      <section
        v-if="movie.overview"
        class="block"
      >
        <h2 class="block__title">
          줄거리
        </h2>
        <p class="overview">
          {{ movie.overview }}
        </p>
      </section>

      <!-- OTT -->
      <section class="block">
        <h2 class="block__title">
          어디서 볼 수 있나요?
        </h2>
        <p
          v-if="extrasLoading"
          class="msg msg--left"
        >
          불러오는 중…
        </p>
        <div
          v-else-if="extras.ott.length"
          class="ott"
        >
          <div
            v-for="p in extras.ott"
            :key="p.name"
            class="ott__item"
          >
            <img
              v-if="p.logo"
              :src="LOGO + p.logo"
              :alt="p.name"
              class="ott__logo"
            >
            <span>{{ p.name }}</span>
          </div>
        </div>
        <p
          v-else
          class="msg msg--left"
        >
          제공 정보 없음
        </p>
      </section>

      <!-- 예고편 (DB의 trailer_key — 본문과 함께 즉시 표시, 없으면 섹션 숨김) -->
      <section
        v-if="movie.trailer_key"
        class="block"
      >
        <h2 class="block__title">
          예고편
        </h2>
        <div class="trailer">
          <iframe
            :src="`https://www.youtube.com/embed/${movie.trailer_key}`"
            title="trailer"
            frameborder="0"
            allowfullscreen
          />
        </div>
      </section>

      <!-- TODO(2.4): 이용자 리뷰 목록 (F-MOV-04) -->
    </template>

    <!-- 시청 등록·별점·리뷰 모달 (등록=POST / 수정=PATCH, 모달이 자체 처리) -->
    <WatchRecordModal
      v-if="showModal && movie"
      :movie="movie"
      :initial-record="myRecord"
      @saved="onSaved"
      @close="showModal = false"
    />
  </div>
</template>

<style scoped>
.detail {
  max-width: 1000px;
  margin: 0 auto;
  padding: 28px 24px 60px;
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
.hero {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 30px;
  margin-bottom: 36px;
}
.hero__poster {
  aspect-ratio: 2 / 3;
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--surface-2);
}
.hero__poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.hero__info h1 {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.01em;
  margin: 0 0 10px;
}
.meta {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 16px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 20px;
}
.chip {
  font-size: 12px;
  padding: 4px 11px;
  border-radius: 20px;
  border: 1px solid var(--border);
  color: var(--text-muted);
  background: var(--surface-2);
}
.chip--genre {
  color: var(--text);
  border-color: var(--border-hover);
}
.ratings {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.rating {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.rating--mine {
  align-items: center;
}
.rating__num {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
}
.rating__den {
  font-size: 13px;
  color: var(--text-muted);
}
.rating__label {
  font-size: 13px;
  color: var(--text-muted);
}
.cast {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.6;
}
/* 시청 등록/수정 */
.watch {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 22px;
}
.watch__badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #2bb24b;
  padding: 7px 12px;
  border: 1px solid rgba(43, 178, 75, 0.4);
  border-radius: var(--radius-sm);
  background: rgba(43, 178, 75, 0.08);
}
.watch__btn {
  font-size: 13px;
  font-family: var(--font);
  color: var(--text);
  padding: 8px 14px;
  border: 1px solid var(--border-hover);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  cursor: pointer;
}
.watch__btn:hover {
  border-color: var(--text-muted);
}
.watch__btn--add {
  font-weight: 600;
  color: #fff;
  background: var(--accent, #f0a020);
  border-color: transparent;
}
/* 블록 */
.block {
  margin-top: 30px;
}
.block__title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.overview {
  font-size: 14px;
  line-height: 1.75;
  color: var(--text);
  margin: 0;
}
/* OTT */
.ott {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.ott__item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 13px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
}
.ott__logo {
  width: 30px;
  height: 30px;
  border-radius: 7px;
  object-fit: cover;
}
/* 예고편 */
.trailer {
  position: relative;
  aspect-ratio: 16 / 9;
  max-width: 680px;
  border-radius: var(--radius);
  overflow: hidden;
}
.trailer iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
@media (max-width: 680px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .hero__poster {
    max-width: 220px;
  }
}
</style>
