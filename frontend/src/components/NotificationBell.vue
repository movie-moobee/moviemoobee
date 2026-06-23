<script setup>
// 헤더 🔔 알림 드롭다운 (F-NTF-01, 와이어프레임 14).
// 배지 = 안읽음 개수(폴링). 드롭다운 열람 시 모두 읽음 처리(배지 클리어).
// 요청 알림은 수락/거절 버튼 포함 → 친구관계 성립/폐기.
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  getNotifications,
  getUnreadCount,
  markNotificationsRead,
  acceptFriendRequest,
  rejectFriendRequest,
} from "@/api/social";

const router = useRouter();
const open = ref(false);
const unread = ref(0);
const items = ref([]);
const loading = ref(false);
const respondingId = ref(null);
let timer = null;

async function refreshBadge() {
  try {
    unread.value = await getUnreadCount();
  } catch {
    /* 비로그인·네트워크 오류는 조용히 무시 (배지만) */
  }
}

async function toggle() {
  if (open.value) {
    open.value = false;
    return;
  }
  open.value = true;
  loading.value = true;
  try {
    items.value = await getNotifications();
    if (unread.value > 0) {
      await markNotificationsRead(); // 열람 = 읽음 → 배지 클리어 (목록의 강조는 유지)
      unread.value = 0;
    }
  } catch {
    items.value = [];
  } finally {
    loading.value = false;
  }
}

function close() {
  open.value = false;
}

async function onAccept(item) {
  if (respondingId.value) return;
  respondingId.value = item.id;
  try {
    await acceptFriendRequest(item.friendship_id);
    item.handled = "accepted";
  } catch {
    item.error = true;
  } finally {
    respondingId.value = null;
  }
}

async function onReject(item) {
  if (respondingId.value) return;
  respondingId.value = item.id;
  try {
    await rejectFriendRequest(item.friendship_id);
    item.handled = "rejected";
  } catch {
    item.error = true;
  } finally {
    respondingId.value = null;
  }
}

function onItemClick(item) {
  // 알림 클릭 → 관련 화면(친구 페이지)으로 이동. 요청 알림은 버튼으로 처리하므로 제외.
  if (item.type === "friend_request" && !item.handled) return;
  close();
  router.push({ name: "friends" });
}

function message(item) {
  return item.type === "friend_request"
    ? "님이 친구 요청을 보냈어요"
    : "님이 친구 요청을 수락했어요";
}

function relTime(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "방금";
  if (diff < 3600) return `${Math.floor(diff / 60)}분`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간`;
  if (diff < 172800) return "어제";
  return new Date(iso).toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
}

function initial(nickname) {
  return (nickname || "?").trim().charAt(0).toUpperCase();
}

onMounted(() => {
  refreshBadge();
  timer = setInterval(refreshBadge, 45000); // 가벼운 폴링(45초) — 실시간 push 없음(F-NTF-01)
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <div class="bell-wrap">
    <button
      class="bell"
      type="button"
      aria-label="알림"
      @click="toggle"
    >
      🔔
      <span
        v-if="unread > 0"
        class="badge"
      >{{ unread > 99 ? "99+" : unread }}</span>
    </button>

    <template v-if="open">
      <div
        class="backdrop"
        @click="close"
      />
      <div class="dropdown">
        <div class="dropdown__head">
          <span class="dropdown__title">알림</span>
          <button
            class="dropdown__close"
            type="button"
            @click="close"
          >
            닫기
          </button>
        </div>

        <p
          v-if="loading"
          class="empty"
        >
          불러오는 중…
        </p>
        <p
          v-else-if="items.length === 0"
          class="empty"
        >
          새 알림이 없습니다.
        </p>
        <ul
          v-else
          class="list"
        >
          <li
            v-for="n in items"
            :key="n.id"
            class="item"
            :class="{ 'item--unread': !n.is_read, 'item--click': n.type === 'friend_accept' }"
            @click="onItemClick(n)"
          >
            <div class="avatar">
              <img
                v-if="n.actor.profile_image_url"
                :src="n.actor.profile_image_url"
                :alt="n.actor.nickname"
              >
              <span v-else>{{ initial(n.actor.nickname) }}</span>
            </div>
            <div class="item__body">
              <p class="item__text">
                <b>{{ n.actor.nickname }}</b> {{ message(n) }}
              </p>
              <!-- 요청 알림: 아직 대기중이면 수락/거절, 이미 처리됐으면 상태 -->
              <div
                v-if="n.type === 'friend_request' && !n.handled && n.friendship_status === 'pending'"
                class="item__actions"
                @click.stop
              >
                <button
                  class="act act--primary"
                  type="button"
                  :disabled="respondingId === n.id"
                  @click="onAccept(n)"
                >
                  수락
                </button>
                <button
                  class="act"
                  type="button"
                  :disabled="respondingId === n.id"
                  @click="onReject(n)"
                >
                  거절
                </button>
              </div>
              <p
                v-else-if="n.handled === 'accepted' || (n.type === 'friend_request' && n.friendship_status === 'accepted')"
                class="item__done"
              >
                친구가 되었어요
              </p>
              <p
                v-else-if="n.handled === 'rejected'"
                class="item__done"
              >
                요청을 거절했어요
              </p>
              <p
                v-if="n.error"
                class="item__err"
              >
                처리에 실패했어요. 다시 시도해주세요.
              </p>
            </div>
            <span class="item__time">{{ relTime(n.created_at) }}</span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<style scoped>
.bell-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.bell {
  position: relative;
  width: 30px;
  height: 30px;
  border: 0;
  background: none;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.badge {
  position: absolute;
  top: -3px;
  right: -3px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 9px;
  background: var(--danger, #e23b3b);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  border: 1.5px solid var(--surface-2, #1a1a1a);
}

.backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
}
.dropdown {
  position: absolute;
  top: 38px;
  right: 0;
  width: 360px;
  max-height: 70vh;
  overflow-y: auto;
  background: var(--surface, #1c1c1c);
  border: 1px solid var(--border);
  border-radius: var(--radius, 10px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
  z-index: 41;
}
.dropdown__head {
  display: flex;
  align-items: center;
  padding: 13px 15px;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--surface, #1c1c1c);
}
.dropdown__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}
.dropdown__close {
  margin-left: auto;
  background: none;
  border: 0;
  color: var(--text-muted);
  font-size: 12.5px;
  cursor: pointer;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.item {
  display: flex;
  gap: 11px;
  padding: 12px 15px;
  border-bottom: 1px solid var(--border);
  align-items: flex-start;
}
.item:last-child {
  border-bottom: 0;
}
.item--unread {
  background: rgba(212, 175, 55, 0.08);
}
.item--click {
  cursor: pointer;
}
.item--click:hover {
  background: var(--surface-alt, rgba(255, 255, 255, 0.03));
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  flex: none;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-alt, #2a2a2a);
  color: var(--text-muted);
  font-size: 15px;
  font-weight: 700;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item__body {
  flex: 1;
  min-width: 0;
}
.item__text {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--text);
}
.item__text b {
  font-weight: 700;
}
.item__actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
.item__done {
  margin: 7px 0 0;
  font-size: 11.5px;
  color: var(--text-muted);
}
.item__err {
  margin: 6px 0 0;
  font-size: 11.5px;
  color: var(--danger);
}

.act {
  padding: 5px 12px;
  border: 1px solid var(--border-hover, var(--border));
  border-radius: var(--radius-sm, 6px);
  background: none;
  color: var(--text);
  font-family: var(--font);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
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

.item__time {
  flex: none;
  font-size: 10.5px;
  color: var(--text-muted);
}

.empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 36px 0;
  margin: 0;
}
</style>
