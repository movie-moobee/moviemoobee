<script setup>
// 영화 검색 (F-MOV-01). 제목 검색 → 결과 그리드 → 상세로.
import { ref } from "vue";
import { useRouter } from "vue-router";
import { searchMovies } from "@/api/movies";

const router = useRouter();
const query = ref("");
const results = ref([]);
const searched = ref(false);
const loading = ref(false);
const error = ref("");
const IMG = "https://image.tmdb.org/t/p/w300";

function poster(p) {
  return p ? IMG + p : "";
}

async function onSearch() {
  if (!query.value.trim()) return;
  loading.value = true;
  error.value = "";
  try {
    results.value = await searchMovies(query.value.trim());
    searched.value = true;
  } catch {
    error.value = "검색에 실패했습니다.";
  } finally {
    loading.value = false;
  }
}
function openMovie(id) {
  router.push({ name: "movie-detail", params: { id } });
}
</script>

<template>
  <div class="search-page">
    <div class="bar">
      <input
        v-model="query"
        class="bar__input"
        placeholder="영화 제목으로 검색"
        @keyup.enter="onSearch"
      >
      <button
        class="bar__btn"
        type="button"
        @click="onSearch"
      >
        검색
      </button>
    </div>

    <p
      v-if="error"
      class="msg msg--error"
    >
      {{ error }}
    </p>
    <p
      v-else-if="loading"
      class="msg"
    >
      검색 중…
    </p>
    <template v-else-if="searched">
      <div class="count">
        검색 결과 <b>{{ results.length }}</b>편
      </div>
      <div
        v-if="results.length"
        class="grid"
      >
        <button
          v-for="m in results"
          :key="m.id"
          class="card"
          type="button"
          @click="openMovie(m.id)"
        >
          <div class="card__poster">
            <img
              v-if="poster(m.poster_path)"
              :src="poster(m.poster_path)"
              :alt="m.title"
            >
          </div>
          <div class="card__title">
            {{ m.title }}
          </div>
          <div class="card__meta">
            {{ m.release_year || "" }}<span v-if="m.vote_average"> · ⭐ {{ m.vote_average }}</span>
          </div>
        </button>
      </div>
      <p
        v-else
        class="msg"
      >
        결과가 없습니다.
      </p>
    </template>
    <p
      v-else
      class="msg"
    >
      보고 싶은 영화를 검색해보세요.
    </p>
  </div>
</template>

<style scoped>
.search-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 28px 24px 60px;
}
.bar {
  display: flex;
  gap: 10px;
  margin-bottom: 22px;
}
.bar__input {
  flex: 1;
  padding: 12px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 14px;
  font-family: var(--font);
}
.bar__input::placeholder {
  color: var(--text-faint);
}
.bar__input:focus {
  outline: none;
  border-color: var(--gold);
}
.bar__btn {
  padding: 0 22px;
  background: var(--gold);
  color: #1a1206;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.msg {
  color: var(--text-muted);
  font-size: 14px;
  padding: 40px 0;
  text-align: center;
}
.msg--error {
  color: var(--danger);
}
.count {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 16px;
}
.count b {
  color: var(--text);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 18px;
}
.card {
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  font-family: var(--font);
}
.card__poster {
  aspect-ratio: 2 / 3;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--surface-2);
}
.card__poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}
.card:hover .card__poster img {
  transform: scale(1.04);
}
.card__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-top: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card__meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}
</style>
