<script setup>
// 별점만 받는 모달 (온보딩 F-ONB-01). 영화 선택 시 별점 매겨 담기.
// 일반 등록(화면07)은 review·watched_on을 더 받지만, 여기선 별점만.
import { ref } from "vue";
import RatingStars from "@/components/base/RatingStars.vue";

const props = defineProps({
  movie: { type: Object, required: true }, // { title, poster_path, release_year }
  initialRating: { type: Number, default: 0 }, // 수정 시 현재 별점
});
const emit = defineEmits(["save", "close"]);

const rating = ref(props.initialRating);

const IMG = "https://image.tmdb.org/t/p/w200";
const poster = props.movie.poster_path ? IMG + props.movie.poster_path : "";

function save() {
  if (rating.value > 0) emit("save", rating.value);
}
</script>

<template>
  <div
    class="overlay"
    @click.self="emit('close')"
  >
    <div class="modal">
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
      </div>

      <div class="rate">
        <div class="rate__label">
          별점을 매겨주세요
        </div>
        <RatingStars
          v-model="rating"
          :size="38"
        />
        <div class="rate__value">
          {{ rating > 0 ? `${rating * 2} / 10` : "별점 필수" }}
        </div>
      </div>

      <div class="actions">
        <button
          class="btn btn--save"
          type="button"
          :disabled="rating === 0"
          @click="save"
        >
          담기
        </button>
        <button
          class="btn btn--cancel"
          type="button"
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
}
.modal {
  width: 100%;
  max-width: 380px;
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
  width: 64px;
  height: 96px;
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
.rate {
  text-align: center;
  margin: 26px 0 24px;
}
.rate__label {
  font-size: 13px;
  color: #8b8f99;
  margin-bottom: 12px;
}
.rate__value {
  margin-top: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #2b2d33;
}
.actions {
  display: flex;
  gap: 8px;
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
</style>
