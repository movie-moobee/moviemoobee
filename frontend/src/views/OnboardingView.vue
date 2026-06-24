<script setup>
// 온보딩 영화 등록 (F-ONB-01). 5편 이상 별점 매겨 등록 → 메인.
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/api/client";
import {
  listWatchRecords,
  createWatchRecord,
  updateWatchRecord,
  deleteWatchRecord,
} from "@/api/watchRecords";
import { completeOnboarding } from "@/api/auth";
import RatingModal from "@/components/RatingModal.vue";
import RatingStars from "@/components/base/RatingStars.vue";

const router = useRouter();
const REQUIRED = 5;
const IMG = "https://image.tmdb.org/t/p/w300";
const SUGGESTIONS = ["인셉션", "기생충", "인터스텔라", "라라랜드", "매트릭스", "어바웃 타임", "위플래쉬"];

const popular = ref([]);
const query = ref("");
const results = ref([]);
const records = ref([]);
const error = ref("");

// 모달 상태 (추가/수정 공용)
const modalMovie = ref(null); // 모달에 띄울 영화 정보
const modalRating = ref(0); // 초기 별점 (수정 시 현재값)
const modalEditId = ref(null); // 수정 중인 시청기록 id (추가면 null)

const count = computed(() => records.value.length);
const enough = computed(() => count.value >= REQUIRED);
const progress = computed(() => Math.min(100, (count.value / REQUIRED) * 100));
const remaining = computed(() => Math.max(0, REQUIRED - count.value));
const registeredIds = computed(() => new Set(records.value.map((r) => r.movie_detail.id)));
const browseList = computed(() => (query.value.trim() ? results.value : popular.value));

function poster(path) {
  return path ? IMG + path : "";
}

onMounted(async () => {
  const [pop, recs] = await Promise.all([
    api.get("/movies/?limit=12").then((r) => r.data),
    listWatchRecords(),
  ]);
  popular.value = pop;
  records.value = recs;
});

async function search() {
  error.value = "";
  if (!query.value.trim()) {
    results.value = [];
    return;
  }
  try {
    const { data } = await api.get("/movies/", { params: { search: query.value.trim() } });
    results.value = data;
  } catch {
    error.value = "검색에 실패했습니다.";
  }
}
function searchChip(term) {
  query.value = term;
  search();
}

// 검색/인기 카드의 ＋ → 추가 모달
function openAdd(movie) {
  if (registeredIds.value.has(movie.id)) return;
  modalMovie.value = movie;
  modalRating.value = 0;
  modalEditId.value = null;
}
// 등록한 영화 포스터 클릭 → 별점 수정 모달
function openEdit(rec) {
  modalMovie.value = rec.movie_detail;
  modalRating.value = Number(rec.rating);
  modalEditId.value = rec.id;
}
function closeModal() {
  modalMovie.value = null;
  modalEditId.value = null;
}

async function onSave(rating) {
  error.value = "";
  try {
    if (modalEditId.value) {
      const updated = await updateWatchRecord(modalEditId.value, { rating });
      const r = records.value.find((x) => x.id === modalEditId.value);
      if (r) r.rating = updated.rating;
    } else {
      const rec = await createWatchRecord({ movie: modalMovie.value.id, rating });
      records.value.unshift(rec);
    }
  } catch (e) {
    error.value = e.response?.data?.movie?.[0] || e.response?.data?.rating?.[0] || "처리에 실패했습니다.";
  } finally {
    closeModal();
  }
}

async function remove(rec) {
  error.value = "";
  try {
    await deleteWatchRecord(rec.id);
    records.value = records.value.filter((r) => r.id !== rec.id);
  } catch {
    error.value = "삭제에 실패했습니다.";
  }
}

async function next() {
  if (!enough.value) return;
  error.value = "";
  try {
    await completeOnboarding();
    router.push("/");
  } catch (e) {
    error.value = e.response?.data?.detail || "온보딩 완료 처리에 실패했습니다.";
  }
}
</script>

<template>
  <div class="onb">
    <div class="onb__inner">
      <!-- 헤더 + 등록 현황 -->
      <div class="top">
        <div class="head">
          <div class="kicker">
            MOVIE MOOBEE
          </div>
          <h1>영화 등록하기</h1>
          <p>
            회원가입을 위해 {{ REQUIRED }}편 이상의 영화를 등록해주세요.<br>
            등록한 영화는 취향 분석과 추천에 활용됩니다.
          </p>
        </div>
        <div class="status">
          <div class="status__label">
            등록 현황
          </div>
          <div class="status__count">
            {{ count }} <span>/ {{ REQUIRED }}편</span>
          </div>
          <div class="bar">
            <div
              class="bar__fill"
              :style="{ width: progress + '%' }"
            />
          </div>
          <div class="status__hint">
            {{ enough ? "등록 완료! 다음 단계로 진행할 수 있어요." : `${remaining}편 더 등록하면 가입이 완료됩니다.` }}
          </div>
        </div>
      </div>

      <!-- 검색하기 -->
      <section class="box">
        <h2 class="box__title">
          영화 검색하기
        </h2>
        <div class="search">
          <span class="search__icon">🔍</span>
          <input
            v-model="query"
            class="search__input"
            placeholder="영화 제목을 입력하세요"
            @keyup.enter="search"
          >
        </div>
        <div class="suggest">
          <span class="suggest__label">추천 검색어</span>
          <button
            v-for="s in SUGGESTIONS"
            :key="s"
            class="chip"
            type="button"
            @click="searchChip(s)"
          >
            {{ s }}
          </button>
        </div>

        <div class="label">
          {{ query.trim() ? "검색 결과" : "인기 영화" }}
        </div>
        <p
          v-if="error"
          class="error"
        >
          {{ error }}
        </p>
        <div class="grid">
          <div
            v-for="m in browseList"
            :key="m.id"
            class="mcard"
          >
            <div
              class="mcard__poster"
              :class="{ 'mcard__poster--add': !registeredIds.has(m.id) }"
              :role="registeredIds.has(m.id) ? null : 'button'"
              :tabindex="registeredIds.has(m.id) ? null : 0"
              @click="openAdd(m)"
              @keyup.enter="openAdd(m)"
            >
              <img
                v-if="poster(m.poster_path)"
                :src="poster(m.poster_path)"
                :alt="m.title"
              >
              <button
                class="fab"
                :class="{ 'fab--done': registeredIds.has(m.id) }"
                type="button"
                :disabled="registeredIds.has(m.id)"
                @click.stop="openAdd(m)"
              >
                {{ registeredIds.has(m.id) ? "✓" : "＋" }}
              </button>
            </div>
            <div class="mcard__title">
              {{ m.title }}
            </div>
            <div class="mcard__meta">
              {{ m.release_year || "" }}<span v-if="m.vote_average"> · ★ {{ m.vote_average }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 내가 등록한 영화 -->
      <section class="box">
        <h2 class="box__title">
          내가 등록한 영화
        </h2>
        <div class="grid">
          <div
            v-for="rec in records"
            :key="rec.id"
            class="mcard"
          >
            <div
              class="mcard__poster mcard__poster--edit"
              role="button"
              tabindex="0"
              title="별점 수정"
              @click="openEdit(rec)"
              @keyup.enter="openEdit(rec)"
            >
              <img
                v-if="poster(rec.movie_detail.poster_path)"
                :src="poster(rec.movie_detail.poster_path)"
                :alt="rec.movie_detail.title"
              >
              <button
                class="fab fab--remove"
                type="button"
                aria-label="삭제"
                @click.stop="remove(rec)"
              >
                ✕
              </button>
            </div>
            <div class="mcard__title">
              {{ rec.movie_detail.title }}
            </div>
            <RatingStars
              :model-value="Number(rec.rating)"
              :size="15"
              readonly
            />
          </div>
          <!-- 남은 슬롯 -->
          <div
            v-for="i in remaining"
            :key="`slot-${i}`"
            class="slot"
          >
            <span class="slot__plus">＋</span>
            영화를 추가해주세요
          </div>
        </div>
        <div class="actions">
          <button
            class="next"
            type="button"
            :disabled="!enough"
            @click="next"
          >
            {{ enough ? "다음 단계로 ›" : `${remaining}편 더 등록해주세요` }}
          </button>
        </div>
      </section>

      <!-- 안내 -->
      <section class="info">
        <div class="info__title">
          ⓘ 안내
        </div>
        <ul>
          <li>{{ REQUIRED }}편 이상 등록해야 회원가입이 완료됩니다.</li>
          <li>직접 검색을 통해 등록하거나, 목록에서 추가할 수 있습니다.</li>
          <li>등록한 영화는 포스터를 눌러 별점을 수정하거나 ✕로 제거할 수 있습니다.</li>
        </ul>
      </section>
    </div>

    <RatingModal
      v-if="modalMovie"
      :movie="modalMovie"
      :initial-rating="modalRating"
      @save="onSave"
      @close="closeModal"
    />
  </div>
</template>

<style scoped>
.onb {
  min-height: 100vh;
  background: #f0eee9;
  color: #1a1a1a;
  padding: 40px var(--page-pad) 80px;
}
.onb__inner {
  width: 100%;
  max-width: var(--page-max);
  margin: 0 auto;
}
/* 헤더 + 현황 */
.top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 28px;
}
.kicker {
  font-size: 12px;
  letter-spacing: 0.14em;
  font-weight: 600;
  color: #1a1a1a;
}
.head h1 {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin: 8px 0 10px;
}
.head p {
  font-size: 14px;
  color: #6b6b6b;
  margin: 0;
  line-height: 1.6;
}
.status {
  flex: none;
  width: 260px;
  background: #fff;
  border: 1px solid #e0dcd3;
  border-radius: 12px;
  padding: 16px 18px;
}
.status__label {
  font-size: 12px;
  color: #8a857c;
}
.status__count {
  font-size: 26px;
  font-weight: 800;
  margin: 4px 0 10px;
}
.status__count span {
  font-size: 14px;
  font-weight: 400;
  color: #8a857c;
}
.bar {
  height: 8px;
  background: #e0dcd3;
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 8px;
}
.bar__fill {
  height: 100%;
  background: #1a1a1a;
  transition: width 0.25s;
}
.status__hint {
  font-size: 12px;
  color: #8a857c;
}
/* 박스 */
.box {
  background: #fff;
  border: 1px solid #e0dcd3;
  border-radius: 14px;
  padding: 24px;
  margin-bottom: 20px;
}
.box__title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 16px;
}
.search {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f5f3ef;
  border: 1px solid #d3cfc6;
  border-radius: 10px;
  padding: 12px 16px;
}
.search__icon {
  font-size: 14px;
  opacity: 0.6;
}
.search__input {
  flex: 1;
  border: none;
  background: none;
  font-size: 14px;
  font-family: var(--font);
  color: #1a1a1a;
  outline: none;
}
.search__input::placeholder {
  color: #a8a49c;
}
.suggest {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 14px 0 22px;
}
.suggest__label {
  font-size: 13px;
  color: #8a857c;
  margin-right: 4px;
}
.chip {
  border: 1px solid #d3cfc6;
  background: #fff;
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 13px;
  color: #5b5750;
  cursor: pointer;
  font-family: var(--font);
}
.chip:hover {
  border-color: #1a1a1a;
  color: #1a1a1a;
}
.label {
  font-size: 13px;
  font-weight: 600;
  color: #8a857c;
  margin-bottom: 14px;
}
.error {
  font-size: 13px;
  color: #b3261e;
  margin: 0 0 12px;
}
/* 카드 그리드 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
  gap: 16px;
}
.mcard__poster {
  position: relative;
  aspect-ratio: 2 / 3;
  border-radius: 8px;
  overflow: hidden;
  background: #ece8e1;
}
.mcard__poster--edit,
.mcard__poster--add {
  cursor: pointer;
}
.mcard__poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.fab {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.95);
  color: #1a1a1a;
  font-size: 15px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}
.fab--done {
  background: #1a1a1a;
  color: #fff;
  cursor: default;
}
.fab--remove {
  font-size: 12px;
}
.mcard__title {
  font-size: 13px;
  font-weight: 600;
  margin-top: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mcard__meta {
  font-size: 12px;
  color: #8a857c;
  margin-top: 2px;
}
/* 빈 슬롯 */
.slot {
  aspect-ratio: 2 / 3;
  border: 1.5px dashed #c9c5bd;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #a8a49c;
  font-size: 12px;
  text-align: center;
  padding: 8px;
}
.slot__plus {
  font-size: 22px;
}
/* 다음 */
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
.next {
  padding: 12px 22px;
  background: #1a1a1a;
  color: #f0eee9;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.next:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
/* 안내 */
.info {
  background: #f5f3ef;
  border: 1px solid #e0dcd3;
  border-radius: 12px;
  padding: 16px 20px;
}
.info__title {
  font-size: 13px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 8px;
}
.info ul {
  margin: 0;
  padding-left: 18px;
}
.info li {
  font-size: 13px;
  color: #6b6b6b;
  line-height: 1.9;
}
@media (max-width: 860px) {
  .top {
    flex-direction: column;
  }
  .status {
    width: 100%;
  }
}
</style>
