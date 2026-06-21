<script setup>
// 메인(홈) 페이지 (화면 04, 김호준) — ① 내 취향 지도 프리뷰(대형, 탭→지도 페이지)
// ② 최근 추가된 영화(우리 DB created_at 신규순, 가로 스크롤). 카드 클릭 → 영화 상세.
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getMyMap } from "@/api/taste";
import { getRecentMovies } from "@/api/movies";
import TasteMapCanvas from "@/components/TasteMapCanvas.vue";

const router = useRouter();
const map = ref(null);          // { enough, watched:[...] }
const recent = ref([]);
const loading = ref(true);
const IMG = "https://image.tmdb.org/t/p/w300";

onMounted(async () => {
  try {
    [map.value, recent.value] = await Promise.all([getMyMap(), getRecentMovies(12)]);
  } finally {
    loading.value = false;
  }
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
  <div class="home">
    <!-- ① 내 취향 지도 프리뷰 -->
    <div class="sec-divider">
      내 취향 지도 <span class="hint">- 탭하면 지도 페이지로</span>
    </div>
    <p
      v-if="loading"
      class="msg"
    >
      불러오는 중…
    </p>
    <template v-else>
      <button
        v-if="map.enough"
        class="preview"
        type="button"
        @click="goMap"
      >
        <TasteMapCanvas
          :watched="map.watched"
          :interactive="false"
          :width="1040"
          :height="376"
        />
        <span class="preview__hint">지도 자세히 보기 →</span>
      </button>
      <div
        v-else
        class="preview preview--empty"
      >
        <p>아직 취향 지도가 없어요. 영화 <b>5편 이상</b>을 등록하면 별이 빛나기 시작해요.</p>
        <button
          class="empty__btn"
          type="button"
          @click="goRegister"
        >
          영화 등록하러 가기
        </button>
      </div>
    </template>

    <!-- ② 최근 추가된 영화 -->
    <div class="sec-divider sec-divider--gap">
      최근 추가된 영화 
    </div>
    <div
      v-if="recent.length"
      class="rail"
    >
      <button
        v-for="m in recent"
        :key="m.id"
        class="rcard"
        type="button"
        @click="openMovie(m.id)"
      >
        <div class="rcard__poster">
          <img
            v-if="poster(m.poster_path)"
            :src="poster(m.poster_path)"
            :alt="m.title"
          >
        </div>
        <div class="rcard__title">
          {{ m.title }}
        </div>
        <div class="rcard__meta">
          {{ m.release_year || "" }} · 신규
        </div>
      </button>
    </div>
    <p
      v-else-if="!loading"
      class="msg"
    >
      아직 등록된 영화가 없습니다.
    </p>
  </div>
</template>

<style scoped>
.home {
  max-width: 1100px;
  margin: 0 auto;
  padding: 28px 24px 60px;
}
.sec-divider {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 14px;
}
.sec-divider--gap {
  margin-top: 36px;
}
.hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
}
.msg {
  color: var(--text-muted);
  font-size: 14px;
  padding: 40px 0;
  text-align: center;
}

/* 지도 프리뷰 */
.preview {
  display: block;
  width: 100%;
  padding: 0;
  position: relative;
  border: 1px solid #262a36;
  border-radius: 10px;
  overflow: hidden;
  background: #0e1018;
  cursor: pointer;
}
.preview__hint {
  position: absolute;
  right: 14px;
  bottom: 12px;
  font-size: 12px;
  color: #cfd3da;
  background: rgba(14, 16, 24, 0.7);
  padding: 4px 10px;
  border-radius: 999px;
}
.preview--empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-height: 240px;
  cursor: default;
  color: var(--text-muted);
  font-size: 14px;
  text-align: center;
}
.empty__btn {
  padding: 10px 22px;
  background: var(--gold);
  color: #1a1206;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

/* 최근 영화 가로 스크롤 */
.rail {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 8px;
}
.rcard {
  width: 118px;
  flex: none;
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  font-family: var(--font);
}
.rcard__poster {
  aspect-ratio: 2 / 3;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--surface-2);
}
.rcard__poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}
.rcard:hover .rcard__poster img {
  transform: scale(1.04);
}
.rcard__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-top: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rcard__meta {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-top: 2px;
}
</style>
