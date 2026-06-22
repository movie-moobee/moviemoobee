<script setup>
// 친구 페이지 (F-FRD-01~03, 와이어프레임 12) — 검색·요청·받은요청 수락/거절.
// 탭: 친구 목록(5.2 예정 placeholder) / 친구 검색 / 받은 요청(뱃지).
import { computed, onMounted, ref } from "vue";
import {
  searchUsers,
  sendFriendRequest,
  getReceivedRequests,
  acceptFriendRequest,
  rejectFriendRequest,
} from "@/api/social";

const TABS = [
  { key: "list", label: "친구 목록" },
  { key: "search", label: "친구 검색" },
  { key: "received", label: "받은 요청" },
];
const activeTab = ref("search"); // 친구 목록은 5.2라 검색을 기본 탭으로

// --- 친구 검색 ---
const query = ref("");
const results = ref([]);
const searching = ref(false);
const searched = ref(false);
const searchError = ref("");
const sendingId = ref(null); // 요청 전송 중인 대상 id

async function onSearch() {
  if (!query.value.trim()) return;
  searching.value = true;
  searchError.value = "";
  try {
    results.value = await searchUsers(query.value.trim());
    searched.value = true;
  } catch {
    searchError.value = "검색에 실패했습니다.";
  } finally {
    searching.value = false;
  }
}

async function onRequest(user) {
  if (sendingId.value) return;
  sendingId.value = user.id;
  try {
    await sendFriendRequest(user.id);
    user.relation = "pending_sent"; // 카드 즉시 '요청 대기'로
  } catch (e) {
    searchError.value = e?.response?.data?.detail || "요청에 실패했습니다.";
  } finally {
    sendingId.value = null;
  }
}

// --- 받은 요청 ---
const received = ref([]);
const receivedLoading = ref(true);
const respondingId = ref(null);
const receivedError = ref("");
const receivedCount = computed(() => received.value.length);

async function loadReceived() {
  receivedLoading.value = true;
  try {
    received.value = await getReceivedRequests();
  } catch {
    received.value = [];
  } finally {
    receivedLoading.value = false;
  }
}

async function onAccept(reqItem) {
  if (respondingId.value) return;
  respondingId.value = reqItem.id;
  receivedError.value = "";
  try {
    await acceptFriendRequest(reqItem.id);
    received.value = received.value.filter((r) => r.id !== reqItem.id);
    // 검색 결과에 그 사람이 떠 있으면 관계도 갱신
    const u = results.value.find((x) => x.id === reqItem.requester.id);
    if (u) u.relation = "friend";
  } catch {
    receivedError.value = "수락에 실패했습니다. 잠시 후 다시 시도해주세요.";
  } finally {
    respondingId.value = null;
  }
}

async function onReject(reqItem) {
  if (respondingId.value) return;
  respondingId.value = reqItem.id;
  receivedError.value = "";
  try {
    await rejectFriendRequest(reqItem.id);
    received.value = received.value.filter((r) => r.id !== reqItem.id);
    const u = results.value.find((x) => x.id === reqItem.requester.id);
    if (u) u.relation = "none";
  } catch {
    receivedError.value = "거절에 실패했습니다. 잠시 후 다시 시도해주세요.";
  } finally {
    respondingId.value = null;
  }
}

onMounted(loadReceived); // 뱃지 수가 어느 탭에서든 보이도록 미리 로드

function initial(nickname) {
  return (nickname || "?").trim().charAt(0).toUpperCase();
}
</script>

<template>
  <div class="friends-page">
    <!-- 탭 -->
    <div class="tabbar">
      <button
        v-for="t in TABS"
        :key="t.key"
        class="tab"
        :class="{ 'tab--on': activeTab === t.key }"
        type="button"
        @click="activeTab = t.key"
      >
        {{ t.label }}
        <span
          v-if="t.key === 'received' && receivedCount"
          class="tab__badge"
        >{{ receivedCount }}</span>
      </button>
    </div>

    <!-- 친구 목록 탭 (5.2 예정) -->
    <div
      v-if="activeTab === 'list'"
      class="msg placeholder"
    >
      친구 목록 탭 — 5.2에서 구현됩니다.
    </div>

    <!-- 친구 검색 탭 -->
    <template v-else-if="activeTab === 'search'">
      <div class="bar">
        <input
          v-model="query"
          class="bar__input"
          type="text"
          placeholder="닉네임으로 친구 검색"
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
        v-if="searchError"
        class="msg msg--error"
      >
        {{ searchError }}
      </p>
      <p
        v-else-if="searching"
        class="msg"
      >
        검색 중…
      </p>
      <ul
        v-else-if="results.length"
        class="cards"
      >
        <li
          v-for="u in results"
          :key="u.id"
          class="card"
          :class="{ 'card--pending': u.relation === 'pending_sent' }"
        >
          <div class="avatar">
            <img
              v-if="u.profile_image_url"
              :src="u.profile_image_url"
              :alt="u.nickname"
            >
            <span v-else>{{ initial(u.nickname) }}</span>
          </div>
          <div class="card__info">
            <p class="card__name">
              {{ u.nickname }}
            </p>
            <p class="card__meta">
              본 영화 {{ u.watch_count }}편
            </p>
          </div>
          <!-- 관계상태별 액션 -->
          <button
            v-if="u.relation === 'none'"
            class="act act--primary"
            type="button"
            :disabled="sendingId === u.id"
            @click="onRequest(u)"
          >
            {{ sendingId === u.id ? "요청 중…" : "친구 요청" }}
          </button>
          <span
            v-else-if="u.relation === 'pending_sent'"
            class="act act--muted"
          >요청 대기 중</span>
          <button
            v-else-if="u.relation === 'pending_received'"
            class="act"
            type="button"
            @click="activeTab = 'received'"
          >
            받은 요청 확인
          </button>
          <span
            v-else
            class="act act--muted"
          >친구</span>
        </li>
      </ul>
      <p
        v-else-if="searched"
        class="msg"
      >
        검색 결과가 없습니다.
      </p>
      <p
        v-else
        class="msg"
      >
        닉네임으로 친구를 찾아 요청을 보내보세요.
      </p>
    </template>

    <!-- 받은 요청 탭 -->
    <template v-else>
      <p
        v-if="receivedError"
        class="msg msg--error"
      >
        {{ receivedError }}
      </p>
      <p
        v-if="receivedLoading"
        class="msg"
      >
        불러오는 중…
      </p>
      <p
        v-else-if="received.length === 0"
        class="msg"
      >
        받은 친구 요청이 없습니다.
      </p>
      <ul
        v-else
        class="cards"
      >
        <li
          v-for="r in received"
          :key="r.id"
          class="card"
        >
          <div class="avatar">
            <img
              v-if="r.requester.profile_image_url"
              :src="r.requester.profile_image_url"
              :alt="r.requester.nickname"
            >
            <span v-else>{{ initial(r.requester.nickname) }}</span>
          </div>
          <div class="card__info">
            <p class="card__name">
              {{ r.requester.nickname }}
            </p>
            <p class="card__meta">
              본 영화 {{ r.requester.watch_count }}편 · 친구 요청을 보냈어요
            </p>
          </div>
          <div class="card__actions">
            <button
              class="act act--primary"
              type="button"
              :disabled="respondingId === r.id"
              @click="onAccept(r)"
            >
              수락
            </button>
            <button
              class="act"
              type="button"
              :disabled="respondingId === r.id"
              @click="onReject(r)"
            >
              거절
            </button>
          </div>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.friends-page {
  max-width: 1320px;
  margin: 0 auto;
  padding: 28px 24px 60px;
}

/* tabs */
.tabbar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 22px;
}
.tab {
  position: relative;
  padding: 10px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 600;
  font-family: var(--font);
  cursor: pointer;
}
.tab--on {
  color: var(--text);
  border-bottom-color: var(--gold);
}
.tab__badge {
  display: inline-block;
  margin-left: 4px;
  min-width: 18px;
  padding: 1px 6px;
  border-radius: 10px;
  background: var(--danger);
  color: #fff;
  font-size: 11px;
  line-height: 16px;
  text-align: center;
}

/* search bar */
.bar {
  display: flex;
  gap: 10px;
  margin-bottom: 22px;
}
.bar__input {
  flex: 1;
  padding: 11px 14px;
  background: var(--surface-alt, var(--surface));
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-family: var(--font);
  font-size: 14px;
  outline: none;
}
.bar__input:focus {
  border-color: var(--gold);
}
.bar__btn {
  padding: 11px 22px;
  background: var(--gold);
  color: #1a1206;
  border: 0;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

/* cards */
.cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.card--pending {
  border-style: dashed;
}

.avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-alt, #2a2a2a);
  color: var(--text-muted);
  font-size: 20px;
  font-weight: 700;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card__info {
  flex: 1;
  min-width: 0;
}
.card__name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card__meta {
  font-size: 12.5px;
  color: var(--text-muted);
  margin: 0;
}

.card__actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.act {
  padding: 8px 14px;
  border: 1px solid var(--border-hover, var(--border));
  border-radius: var(--radius-sm);
  background: none;
  color: var(--text);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.act:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.act--primary {
  background: var(--gold);
  color: #1a1206;
  border-color: var(--gold);
}
.act--muted {
  color: var(--text-muted);
  border-color: var(--border);
  cursor: default;
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
</style>
