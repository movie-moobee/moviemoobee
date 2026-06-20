<script setup>
// 시청 등록·별점·리뷰 모달 (와이어프레임 07 / F-WAT-01·02).
// 별점 필수(0.5단위), 한줄 리뷰·시청일 선택. 등록(POST)·수정(PATCH) 겸용.
// 온보딩의 RatingModal(별점만)과 별개 — 여기는 리뷰·시청일까지 받는 풀 모달.
import { ref } from "vue";
import RatingStars from "@/components/base/RatingStars.vue";
import { createWatchRecord, updateWatchRecord } from "@/api/watchRecords";

const props = defineProps({
  movie: { type: Object, required: true }, // { id, title, poster_path, release_year }
  initialRecord: { type: Object, default: null }, // { id, rating, review, watched_on } | null
});
const emit = defineEmits(["saved", "close"]);

const isEdit = !!props.initialRecord;
const rating = ref(Number(props.initialRecord?.rating) || 0);
const review = ref(props.initialRecord?.review || "");
const watchedOn = ref(props.initialRecord?.watched_on || "");
const saving = ref(false);
const error = ref("");

const IMG = "https://image.tmdb.org/t/p/w200";
const poster = props.movie.poster_path ? IMG + props.movie.poster_path : "";

async function save() {
  if (rating.value <= 0 || saving.value) return;
  saving.value = true;
  error.value = "";
  const payload = {
    rating: rating.value,
    review: review.value.trim(),
    watched_on: watchedOn.value || null,
  };
  try {
    const rec = isEdit
      ? await updateWatchRecord(props.initialRecord.id, payload)
      : await createWatchRecord({ movie: props.movie.id, ...payload });
    emit("saved", rec);
  } catch {
    error.value = "저장에 실패했습니다. 잠시 후 다시 시도해주세요.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div
    class="overlay"
    @click.self="emit('close')"
  >
    <div class="modal">
      <!-- 영화 헤더 -->
      <div class="movie">
        <img
          v-if="poster"
          :src="poster"
          :alt="movie.title"
          class="poster"
        >
        <div
          v-else
          class="poster poster--empty"
        >
          포스터 없음
        </div>
        <div class="meta">
          <div class="title">
            {{ movie.title }}
          </div>
          <div class="year">
            {{ movie.release_year || "" }}
          </div>
        </div>
        <button
          class="close"
          type="button"
          aria-label="닫기"
          @click="emit('close')"
        >
          ✕
        </button>
      </div>

      <!-- 별점 (필수) -->
      <div class="field">
        <div class="field__label">
          별점 <span class="req">(필수)</span>
        </div>
        <div class="rate">
          <RatingStars
            v-model="rating"
            :size="34"
          />
          <span class="rate__value">{{ rating > 0 ? `${rating * 2} / 10` : "별점을 매겨주세요" }}</span>
        </div>
      </div>

      <!-- 한줄 리뷰 (선택) -->
      <div class="field">
        <div class="field__label">
          한줄 리뷰 <span class="sub">(선택)</span>
        </div>
        <textarea
          v-model="review"
          class="review"
          rows="3"
          placeholder="리뷰를 입력하세요 (선택)"
        />
      </div>

      <!-- 시청일 (선택) -->
      <div class="field">
        <div class="field__label">
          시청일 <span class="sub">(선택)</span>
        </div>
        <input
          v-model="watchedOn"
          type="date"
          class="date"
        >
      </div>

      <p
        v-if="error"
        class="error"
      >
        {{ error }}
      </p>

      <!-- 액션 -->
      <div class="actions">
        <button
          class="btn btn--save"
          type="button"
          :disabled="rating === 0 || saving"
          @click="save"
        >
          {{ saving ? "저장 중…" : "저장" }}
        </button>
        <button
          class="btn btn--cancel"
          type="button"
          :disabled="saving"
          @click="emit('close')"
        >
          취소
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
}
.modal {
  width: 100%;
  max-width: 440px;
  background: #fff;
  border: 1px solid #eceef2;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
}
.movie {
  display: flex;
  gap: 14px;
  align-items: center;
}
.poster {
  width: 60px;
  height: 90px;
  object-fit: cover;
  border-radius: 3px;
  flex: none;
}
.poster--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eceef2;
  color: #b0b4bd;
  font-size: 11px;
  text-align: center;
}
.meta {
  flex: 1;
  min-width: 0;
}
.title {
  font-size: 16px;
  font-weight: 600;
  color: #2b2d33;
}
.year {
  font-size: 13px;
  color: #8b8f99;
  margin-top: 4px;
}
.close {
  align-self: flex-start;
  background: none;
  border: 0;
  color: #b0b4bd;
  font-size: 16px;
  cursor: pointer;
  padding: 2px 4px;
}
.field {
  margin-top: 20px;
}
.field__label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: #8b8f99;
  margin-bottom: 8px;
}
.req {
  color: #cf3a3a;
  text-transform: none;
}
.sub {
  font-weight: 400;
  text-transform: none;
  color: #b0b4bd;
}
.rate {
  display: flex;
  align-items: center;
  gap: 12px;
}
.rate__value {
  font-size: 13px;
  color: #2b2d33;
  font-weight: 600;
}
.review {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  font-family: var(--font);
  color: #2b2d33;
  resize: vertical;
}
.review:focus {
  outline: none;
  border-color: #b0b4bd;
}
.date {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 14px;
  font-family: var(--font);
  color: #2b2d33;
}
.date:focus {
  outline: none;
  border-color: #b0b4bd;
}
.error {
  color: #cf3a3a;
  font-size: 13px;
  margin: 14px 0 0;
}
.actions {
  display: flex;
  gap: 8px;
  margin-top: 22px;
}
.btn {
  flex: 1;
  padding: 13px;
  border: none;
  font-size: 14px;
  font-family: var(--font);
  cursor: pointer;
  border-radius: 8px;
}
.btn--save {
  background: #1a1a1a;
  color: #fff;
  font-weight: 600;
}
.btn--save:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn--cancel {
  background: transparent;
  color: #2b2d33;
  border: 1px solid #e5e7eb;
}
.btn--cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
