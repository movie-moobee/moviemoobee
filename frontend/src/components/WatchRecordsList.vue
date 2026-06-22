<script setup>
// 시청 영화 목록 (F-WAT-2.3) — MapView 'records' 탭에 삽입.
// 목록 조회·클라이언트 검색·정렬(최신/별점)·수정(WatchRecordModal)·삭제(ConfirmDialog).
import { computed, onMounted, ref } from "vue";
import { listWatchRecords, deleteWatchRecord } from "@/api/watchRecords";
import WatchRecordModal from "@/components/WatchRecordModal.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import RatingStars from "@/components/base/RatingStars.vue";

// 수정·삭제로 좌표가 바뀌면 부모(MapView)가 취향 지도를 다시 불러오도록 알림
const emit = defineEmits(["changed"]);

const IMG = "https://image.tmdb.org/t/p/w185";

const records = ref([]);
const loading = ref(true);
const loadError = ref("");
const query = ref("");
const sortBy = ref("latest"); // 'latest' | 'rating'

const editTarget = ref(null);  // { record, movie } — 수정 모달용
const deleteTarget = ref(null); // record — 삭제 확인용
const deleting = ref(false);

onMounted(async () => {
  try {
    records.value = await listWatchRecords();
  } catch {
    loadError.value = "목록을 불러오지 못했습니다.";
  } finally {
    loading.value = false;
  }
});

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  let list = q
    ? records.value.filter((r) => r.movie_detail?.title?.toLowerCase().includes(q))
    : [...records.value];

  if (sortBy.value === "rating") {
    list.sort((a, b) => b.rating - a.rating || new Date(b.created_at) - new Date(a.created_at));
  } else {
    list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }
  return list;
});

function openEdit(rec) {
  editTarget.value = {
    record: { id: rec.id, rating: rec.rating, review: rec.review, watched_on: rec.watched_on },
    movie: rec.movie_detail,
  };
}

function onSaved(updated) {
  const idx = records.value.findIndex((r) => r.id === updated.id);
  if (idx !== -1) records.value[idx] = updated;
  editTarget.value = null;
  emit("changed"); // 별점 변경 → 좌표 재계산됐을 수 있어 지도 갱신
}

async function confirmDelete() {
  if (!deleteTarget.value || deleting.value) return;
  deleting.value = true;
  try {
    await deleteWatchRecord(deleteTarget.value.id);
    records.value = records.value.filter((r) => r.id !== deleteTarget.value.id);
    deleteTarget.value = null;
    emit("changed"); // 삭제로 좌표 재계산 → 지도에서도 그 별 제거되도록 갱신
  } catch {
    // 실패해도 다이얼로그 닫지 않고 버튼 상태만 복원
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <div class="records-list">
    <!-- 검색·정렬 바 -->
    <div class="toolbar">
      <input
        v-model="query"
        class="search-input"
        type="text"
        placeholder="제목 검색…"
      >
      <div class="sort-btns">
        <button
          class="sort-btn"
          :class="{ 'sort-btn--on': sortBy === 'latest' }"
          type="button"
          @click="sortBy = 'latest'"
        >
          최신순
        </button>
        <button
          class="sort-btn"
          :class="{ 'sort-btn--on': sortBy === 'rating' }"
          type="button"
          @click="sortBy = 'rating'"
        >
          별점순
        </button>
      </div>
    </div>

    <!-- 로딩 / 에러 -->
    <p
      v-if="loading"
      class="msg"
    >
      불러오는 중…
    </p>
    <p
      v-else-if="loadError"
      class="msg msg--error"
    >
      {{ loadError }}
    </p>
    <p
      v-else-if="filtered.length === 0"
      class="msg"
    >
      {{ query ? '검색 결과가 없습니다.' : '아직 시청 기록이 없습니다.' }}
    </p>

    <!-- 목록 -->
    <ul
      v-else
      class="list"
    >
      <li
        v-for="rec in filtered"
        :key="rec.id"
        class="item"
      >
        <img
          v-if="rec.movie_detail?.poster_path"
          :src="IMG + rec.movie_detail.poster_path"
          :alt="rec.movie_detail.title"
          class="item__poster"
        >
        <div
          v-else
          class="item__poster item__poster--empty"
        />
        <div class="item__info">
          <p class="item__title">
            {{ rec.movie_detail?.title }}
          </p>
          <RatingStars
            :model-value="Number(rec.rating)"
            :size="18"
            readonly
          />
          <p
            class="item__review"
            :class="{ 'item__placeholder': !rec.review }"
          >
            {{ rec.review || "리뷰 미작성" }}
          </p>
          <p
            class="item__date"
            :class="{ 'item__placeholder': !rec.watched_on }"
          >
            {{ rec.watched_on || "시청일 미등록" }}
          </p>
        </div>
        <div class="item__actions">
          <button
            class="action-btn"
            type="button"
            @click="openEdit(rec)"
          >
            수정
          </button>
          <button
            class="action-btn action-btn--danger"
            type="button"
            @click="deleteTarget = rec"
          >
            삭제
          </button>
        </div>
      </li>
    </ul>

    <!-- 수정 모달 -->
    <WatchRecordModal
      v-if="editTarget"
      :movie="editTarget.movie"
      :initial-record="editTarget.record"
      @saved="onSaved"
      @close="editTarget = null"
    />

    <!-- 삭제 확인 -->
    <ConfirmDialog
      v-if="deleteTarget"
      title="시청 기록에서 제거할까요?"
      message="해당 영화가 시청 기록에서 제거됩니다."
      confirm-label="예"
      cancel-label="아니오"
      :danger="true"
      :busy="deleting"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.records-list {
  padding-top: 4px;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 160px;
  padding: 9px 14px;
  background: var(--surface-alt, var(--surface));
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-family: var(--font);
  font-size: 14px;
  outline: none;
}
.search-input:focus {
  border-color: var(--gold);
}

.sort-btns {
  display: flex;
  gap: 4px;
}
.sort-btn {
  padding: 8px 14px;
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.sort-btn--on {
  border-color: var(--gold);
  color: var(--gold);
  background: rgba(212, 175, 55, 0.08);
}

.msg {
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
  padding: 40px 0;
}
.msg--error {
  color: var(--danger);
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.item__poster {
  width: 56px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}
.item__poster--empty {
  background: var(--surface-alt, #2a2a2a);
}

.item__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item__review {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.item__date {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

/* 리뷰·시청일 미등록 시 흐린 안내 문구 */
.item__placeholder {
  color: var(--text-muted);
  opacity: 0.55;
  font-style: italic;
}

.item__actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.action-btn {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: none;
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.action-btn:hover {
  border-color: var(--border-hover, var(--border));
  color: var(--text);
}
.action-btn--danger:hover {
  border-color: var(--danger);
  color: var(--danger);
}
</style>
