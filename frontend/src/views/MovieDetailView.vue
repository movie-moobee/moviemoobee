<script setup>
// 영화 상세 (F-MOV-02 메타 / F-MOV-03 OTT / 예고편 / F-WAT-01 시청 등록 / F-MOV-04 이용자 리뷰).
import { ref, reactive, onMounted, computed, watch } from "vue";
import { useRoute } from "vue-router";
import {
  getMovie,
  getMovieExtras,
  getMovieReviews,
  setReviewReaction,
  removeReviewReaction,
  getReviewComments,
  addReviewComment,
  deleteReviewComment,
} from "@/api/movies";
import { updateWatchRecord, deleteWatchRecord } from "@/api/watchRecords";
import RatingStars from "@/components/base/RatingStars.vue";
import WatchRecordModal from "@/components/WatchRecordModal.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";

const route = useRoute();
const movie = ref(null);
const extras = ref({ ott: [] });
const reviews = ref([]); // 전 유저 이용자 리뷰
const myRecord = ref(null); // 내 시청기록(있으면 수정, 없으면 등록). 상세 응답 my_record에서.
const showModal = ref(false);
const loading = ref(true); // 영화 메타(DB, 예고편 포함) — 이게 끝나면 화면을 그림
const extrasLoading = ref(true); // OTT(TMDB 실시간) — 본문을 막지 않고 따로 채움
const reviewsLoading = ref(true); // 이용자 리뷰 — 본문을 막지 않고 따로 채움
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

// ISO → "YYYY.MM.DD"
function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}.${p(d.getMonth() + 1)}.${p(d.getDate())}`;
}

async function loadExtras(id) {
  extrasLoading.value = true;
  try {
    extras.value = await getMovieExtras(id);
  } catch {
    // OTT 실패는 치명적이지 않음 — 빈 상태로 둠
  } finally {
    extrasLoading.value = false;
  }
}

async function loadReviews(id) {
  reviewsLoading.value = true;
  try {
    reviews.value = await getMovieReviews(id);
  } catch {
    // 리뷰 실패는 치명적이지 않음 — 빈 상태로 둠
  } finally {
    reviewsLoading.value = false;
  }
}

// 리뷰 좋아요/싫어요 (F-REV). 같은 버튼 재클릭=취소, 다른 버튼=교체.
const reactingId = ref(null);
async function onReact(r, value) {
  if (r.is_mine || reactingId.value) return; // 자기 리뷰엔 반응 불가, 중복요청 방지
  reactingId.value = r.id;
  try {
    const res = r.my_reaction === value
      ? await removeReviewReaction(r.id)
      : await setReviewReaction(r.id, value);
    r.like_count = res.like_count;
    r.dislike_count = res.dislike_count;
    r.my_reaction = res.my_reaction;
  } catch {
    // 실패 시 조용히 무시(서버 상태가 정답) — 다음 조회/클릭 때 정정
  } finally {
    reactingId.value = null;
  }
}

// 리뷰 댓글 (F-REV, 평탄). 리뷰별 스레드 상태: open·list·loading·input·posting
const threads = reactive({}); // { [reviewId]: {...} }
function thread(r) {
  if (!threads[r.id]) {
    threads[r.id] = { open: false, list: [], loaded: false, loading: false, input: "", posting: false };
  }
  return threads[r.id];
}
async function toggleComments(r) {
  const t = thread(r);
  t.open = !t.open;
  if (t.open && !t.loaded) {
    t.loading = true;
    try {
      t.list = await getReviewComments(r.id);
      t.loaded = true;
    } catch {
      /* 빈 상태로 둠 */
    } finally {
      t.loading = false;
    }
  }
}
async function submitComment(r) {
  const t = thread(r);
  const body = t.input.trim();
  if (!body || t.posting) return;
  t.posting = true;
  try {
    const c = await addReviewComment(r.id, body);
    t.list.push(c);
    t.input = "";
    r.comment_count = (r.comment_count || 0) + 1;
  } catch {
    /* 무시 */
  } finally {
    t.posting = false;
  }
}
// 댓글 삭제는 경고창 확인 후 — { r, comment } 보관
const commentToDelete = ref(null);
const deletingComment = ref(false);
function askRemoveComment(r, comment) {
  commentToDelete.value = { r, comment };
}
async function confirmRemoveComment() {
  if (!commentToDelete.value || deletingComment.value) return;
  const { r, comment } = commentToDelete.value;
  deletingComment.value = true;
  try {
    await deleteReviewComment(comment.id);
    const t = thread(r);
    t.list = t.list.filter((c) => c.id !== comment.id);
    r.comment_count = Math.max(0, (r.comment_count || 1) - 1);
    commentToDelete.value = null;
  } catch {
    /* 무시 — 서버 상태가 정답 */
  } finally {
    deletingComment.value = false;
  }
}

// 내 리뷰 수정(텍스트만 인라인)·삭제(시청기록 통째). 둘 다 본인 리뷰(is_mine)에서만.
const editing = reactive({}); // { [reviewId]: { active, text, saving } }
function startEditReview(r) {
  editing[r.id] = { active: true, text: r.review || "", saving: false };
}
function cancelEditReview(r) {
  if (editing[r.id]) editing[r.id].active = false;
}
async function saveEditReview(r) {
  const e = editing[r.id];
  const text = e.text.trim();
  if (!text || e.saving) return;
  e.saving = true;
  try {
    await updateWatchRecord(r.id, { review: text }); // 별점은 그대로, 리뷰 텍스트만
    r.review = text;
    if (myRecord.value && myRecord.value.id === r.id) myRecord.value.review = text;
    e.active = false;
  } catch {
    /* 무시 */
  } finally {
    e.saving = false;
  }
}

// 삭제 = 시청기록 통째(별점 포함, 취향 지도 영향) → 강한 경고
const reviewToDelete = ref(null);
const deletingReview = ref(false);
function askDeleteReview(r) {
  reviewToDelete.value = r;
}
async function confirmDeleteReview() {
  if (!reviewToDelete.value || deletingReview.value) return;
  const r = reviewToDelete.value;
  deletingReview.value = true;
  try {
    await deleteWatchRecord(r.id);
    reviews.value = reviews.value.filter((x) => x.id !== r.id);
    if (myRecord.value && myRecord.value.id === r.id) myRecord.value = null; // 상단 '등록' 버튼 복귀
    reviewToDelete.value = null;
  } catch {
    /* 무시 */
  } finally {
    deletingReview.value = false;
  }
}


async function load(id) {
  // 상태 초기화 — 상세→상세 이동(:id 변경) 시 이전 영화 데이터 잔상 방지
  loading.value = true;
  error.value = "";
  movie.value = null;
  myRecord.value = null;
  reviews.value = [];
  extras.value = { ott: [] };

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

  // 2) OTT·이용자 리뷰는 본문을 막지 않고 서로 독립적으로(병렬) 로드.
  //    리뷰가 느린 OTT를 기다리지 않도록 await 없이 동시에 띄운다.
  loadExtras(id);
  loadReviews(id);
}

// 최초 진입 + 상세→상세(:id 변경) 모두 처리. (RouterView가 컴포넌트를 재사용해도 재로드)
onMounted(() => load(route.params.id));
watch(() => route.params.id, (id) => {
  if (id) load(id);
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
  loadReviews(route.params.id); // 내 리뷰가 목록에 반영되도록 재조회
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

      <!-- 이용자 리뷰 (F-MOV-04) -->
      <section class="block">
        <h2 class="block__title">
          이용자 리뷰
        </h2>
        <p
          v-if="reviewsLoading"
          class="msg msg--left"
        >
          불러오는 중…
        </p>
        <div
          v-else-if="reviews.length"
          class="reviews"
        >
          <div
            v-for="r in reviews"
            :key="r.id"
            class="review"
          >
            <div class="review__head">
              <img
                v-if="r.profile_image_url"
                :src="r.profile_image_url"
                :alt="r.nickname"
                class="review__avatar"
              >
              <div
                v-else
                class="review__avatar review__avatar--empty"
              >
                {{ (r.nickname || "?").charAt(0) }}
              </div>
              <div class="review__who">
                <span class="review__nick">{{ r.nickname }}</span>
                <RatingStars
                  :model-value="Number(r.rating)"
                  readonly
                  :size="14"
                />
              </div>
              <span class="review__date">{{ fmtDate(r.created_at) }}</span>
            </div>
            <!-- 내 리뷰 인라인 수정 (리뷰 텍스트만, 별점 제외) -->
            <div
              v-if="r.is_mine && editing[r.id]?.active"
              class="review__edit"
            >
              <textarea
                v-model="editing[r.id].text"
                class="review__edit-area"
                rows="3"
                placeholder="리뷰를 입력하세요"
              />
              <div class="review__edit-actions">
                <button
                  type="button"
                  class="owner-btn"
                  @click="cancelEditReview(r)"
                >
                  취소
                </button>
                <button
                  type="button"
                  class="owner-btn owner-btn--primary"
                  :disabled="!editing[r.id].text.trim() || editing[r.id].saving"
                  @click="saveEditReview(r)"
                >
                  {{ editing[r.id].saving ? "저장 중…" : "저장" }}
                </button>
              </div>
            </div>

            <template v-else>
              <!-- 본문 + 좋아요/싫어요 (F-REV): 같은 행, 버튼은 오른쪽 끝 가로 배치 -->
              <div class="review__content">
                <p
                  v-if="r.review"
                  class="review__body"
                >
                  {{ r.review }}
                </p>
                <!-- 본인 리뷰엔 버튼 숨김, 반응 수만 표시 -->
                <div
                  v-if="!r.is_mine"
                  class="react"
                >
                  <button
                    type="button"
                    class="react__btn"
                    :class="{ 'react__btn--on': r.my_reaction === 1 }"
                    :disabled="reactingId === r.id"
                    @click="onReact(r, 1)"
                  >
                    👍 <span class="react__num">{{ r.like_count }}</span>
                  </button>
                  <button
                    type="button"
                    class="react__btn"
                    :class="{ 'react__btn--on react__btn--down': r.my_reaction === -1 }"
                    :disabled="reactingId === r.id"
                    @click="onReact(r, -1)"
                  >
                    👎 <span class="react__num">{{ r.dislike_count }}</span>
                  </button>
                </div>
                <div
                  v-else
                  class="react react--readonly"
                >
                  <span>👍 {{ r.like_count }}</span>
                  <span>👎 {{ r.dislike_count }}</span>
                </div>
              </div>
              <!-- 내 리뷰: 좋아요/싫어요 아래 수정/삭제 -->
              <div
                v-if="r.is_mine"
                class="review__owner"
              >
                <button
                  type="button"
                  class="owner-btn"
                  @click="startEditReview(r)"
                >
                  수정
                </button>
                <button
                  type="button"
                  class="owner-btn owner-btn--danger"
                  @click="askDeleteReview(r)"
                >
                  삭제
                </button>
              </div>
            </template>

            <!-- 댓글 (F-REV, 평탄 구조) -->
            <button
              type="button"
              class="cmt-toggle"
              @click="toggleComments(r)"
            >
              댓글 {{ r.comment_count || 0 }}
              <span class="cmt-toggle__caret">{{ threads[r.id]?.open ? "▴" : "▾" }}</span>
            </button>
            <div
              v-if="threads[r.id]?.open"
              class="cmts"
            >
              <p
                v-if="threads[r.id].loading"
                class="cmts__msg"
              >
                불러오는 중…
              </p>
              <ul
                v-else-if="threads[r.id].list.length"
                class="cmts__list"
              >
                <li
                  v-for="c in threads[r.id].list"
                  :key="c.id"
                  class="cmt"
                >
                  <div
                    v-if="c.profile_image_url"
                    class="cmt__avatar"
                  >
                    <img
                      :src="c.profile_image_url"
                      :alt="c.nickname"
                    >
                  </div>
                  <div
                    v-else
                    class="cmt__avatar cmt__avatar--empty"
                  >
                    {{ (c.nickname || "?").charAt(0) }}
                  </div>
                  <div class="cmt__main">
                    <div class="cmt__top">
                      <span class="cmt__nick">{{ c.nickname }}</span>
                      <span class="cmt__date">{{ fmtDate(c.created_at) }}</span>
                      <button
                        v-if="c.is_mine"
                        type="button"
                        class="cmt__del"
                        @click="askRemoveComment(r, c)"
                      >
                        삭제
                      </button>
                    </div>
                    <p class="cmt__body">
                      {{ c.body }}
                    </p>
                  </div>
                </li>
              </ul>
              <p
                v-else
                class="cmts__msg"
              >
                아직 댓글이 없습니다.
              </p>
              <!-- 댓글 입력 -->
              <div class="cmt-form">
                <input
                  v-model="threads[r.id].input"
                  class="cmt-form__input"
                  type="text"
                  placeholder="댓글을 입력하세요"
                  @keyup.enter="submitComment(r)"
                >
                <button
                  type="button"
                  class="cmt-form__btn"
                  :disabled="threads[r.id].posting || !threads[r.id].input.trim()"
                  @click="submitComment(r)"
                >
                  등록
                </button>
              </div>
            </div>
          </div>
        </div>
        <p
          v-else
          class="msg msg--left"
        >
          아직 리뷰가 없습니다. 첫 리뷰를 남겨보세요!
        </p>
      </section>
    </template>

    <!-- 시청 등록·별점·리뷰 모달 (등록=POST / 수정=PATCH, 모달이 자체 처리) -->
    <WatchRecordModal
      v-if="showModal && movie"
      :movie="movie"
      :initial-record="myRecord"
      @saved="onSaved"
      @close="showModal = false"
    />

    <!-- 댓글 삭제 확인 -->
    <ConfirmDialog
      v-if="commentToDelete"
      title="댓글을 삭제할까요?"
      message="삭제한 댓글은 복구할 수 없습니다."
      confirm-label="삭제"
      cancel-label="취소"
      :danger="true"
      :busy="deletingComment"
      @confirm="confirmRemoveComment"
      @cancel="commentToDelete = null"
    />

    <!-- 리뷰(시청기록) 삭제 확인 — 별점까지 함께 삭제 경고 -->
    <ConfirmDialog
      v-if="reviewToDelete"
      title="이 리뷰를 삭제할까요?"
      message="이 영화의 시청기록(별점 포함)이 함께 삭제되며 취향 지도에서도 사라집니다. 복구할 수 없습니다."
      confirm-label="삭제"
      cancel-label="취소"
      :danger="true"
      :busy="deletingReview"
      @confirm="confirmDeleteReview"
      @cancel="reviewToDelete = null"
    />
  </div>
</template>

<style scoped>
.detail {
  width: 100%;
  max-width: 1180px;
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
/* 이용자 리뷰 */
.reviews {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.review {
  padding: 14px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
.review__head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.review__avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  object-fit: cover;
  flex: none;
}
.review__avatar--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 600;
}
.review__who {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.review__nick {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.review__date {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
}
/* 본문 + 반응을 같은 행으로: 본문 왼쪽 채움, 버튼 오른쪽 끝 */
.review__content {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 11px;
}
.review__body {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--text);
  margin: 0;
}
/* 좋아요/싫어요 (F-REV) */
.react {
  flex: none;
  display: flex;
  gap: 8px;
}
.react__btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-muted);
  font-size: 13px;
  font-family: var(--font);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.react__btn:hover:not(:disabled) {
  border-color: var(--border-hover);
  color: var(--text);
}
.react__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.react__btn--on {
  border-color: var(--gold);
  color: var(--gold);
}
.react__btn--down.react__btn--on {
  border-color: var(--danger);
  color: var(--danger);
}
.react__num {
  font-weight: 600;
}
.react--readonly {
  gap: 8px;
}
.react--readonly span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 12.5px;
  color: var(--text-muted);
}
/* 내 리뷰 수정/삭제 (F-REV) — 좋아요/싫어요 바로 아래(오른쪽 정렬) */
.review__owner {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}
.owner-btn {
  padding: 5px 14px;
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 12.5px;
  font-family: var(--font);
  cursor: pointer;
}
.owner-btn:hover:not(:disabled) {
  border-color: var(--border-hover);
  color: var(--text);
}
.owner-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.owner-btn--primary {
  background: var(--gold);
  color: #1a1206;
  border-color: var(--gold);
}
.owner-btn--danger:hover {
  border-color: var(--danger);
  color: var(--danger);
}
.review__edit {
  margin-top: 11px;
}
.review__edit-area {
  width: 100%;
  padding: 10px 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 14px;
  font-family: var(--font);
  line-height: 1.6;
  resize: vertical;
  box-sizing: border-box;
}
.review__edit-area:focus {
  outline: none;
  border-color: var(--gold);
}
.review__edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
/* 댓글 (F-REV) */
.cmt-toggle {
  margin-top: 10px;
  padding: 4px 0;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 12.5px;
  font-family: var(--font);
  cursor: pointer;
}
.cmt-toggle:hover {
  color: var(--text);
}
.cmt-toggle__caret {
  font-size: 10px;
}
.cmts {
  margin-top: 10px;
  padding: 12px 14px;
  background: var(--surface-2);
  border-radius: var(--radius-sm);
}
.cmts__msg {
  font-size: 12.5px;
  color: var(--text-muted);
  margin: 0 0 10px;
}
.cmts__list {
  list-style: none;
  margin: 0 0 12px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.cmt {
  display: flex;
  gap: 9px;
}
.cmt__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  flex: none;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
}
.cmt__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.cmt__main {
  flex: 1;
  min-width: 0;
}
.cmt__top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cmt__nick {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
}
.cmt__date {
  font-size: 11px;
  color: var(--text-muted);
}
.cmt__del {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 11.5px;
  cursor: pointer;
}
.cmt__del:hover {
  color: var(--danger);
}
.cmt__body {
  margin: 3px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text);
}
.cmt-form {
  display: flex;
  gap: 8px;
}
.cmt-form__input {
  flex: 1;
  min-width: 0;
  padding: 8px 11px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 13px;
  font-family: var(--font);
}
.cmt-form__input::placeholder {
  color: var(--text-faint);
}
.cmt-form__input:focus {
  outline: none;
  border-color: var(--gold);
}
.cmt-form__btn {
  flex: none;
  padding: 0 16px;
  background: var(--gold);
  color: #1a1206;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
}
.cmt-form__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
