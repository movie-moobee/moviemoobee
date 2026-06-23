import { api } from "./client";

// 친구 API (F-FRD-01~03) → /api/social/
// 검색·요청·받은요청·수락·거절. 친구목록·삭제·프로필은 5.2, 알림은 5.5.

// 닉네임으로 검색 → [{ id, nickname, profile_image_url, watch_count, relation }]
// relation: none | friend | pending_sent | pending_received
export async function searchUsers(q) {
  const { data } = await api.get("/social/users/search/", { params: { q } });
  return data;
}

// 친구 요청 보내기 (중복/역방향은 400)
export async function sendFriendRequest(addresseeId) {
  const { data } = await api.post("/social/friendships/", { addressee: addresseeId });
  return data;
}

// 내가 받은 대기중 요청 → [{ id, created_at, requester:{...} }]
export async function getReceivedRequests() {
  const { data } = await api.get("/social/friendships/received/");
  return data;
}

// 받은 요청 수락 (양방향 친구 성립)
export async function acceptFriendRequest(id) {
  const { data } = await api.post(`/social/friendships/${id}/accept/`);
  return data;
}

// 받은 요청 거절 (요청 폐기)
export async function rejectFriendRequest(id) {
  await api.delete(`/social/friendships/${id}/`);
}

// 내 친구 목록 (F-FRD-04) → [{ id, nickname, profile_image_url, watch_count }]
export async function getFriends() {
  const { data } = await api.get("/social/friends/");
  return data;
}

// 친구 프로필 상세 (친구만) → { id, nickname, profile_image_url, watch_count, watched:[...] }
export async function getFriendProfile(id) {
  const { data } = await api.get(`/social/friends/${id}/`);
  return data;
}

// 친구 끊기 (양방향 관계 해제)
export async function unfriend(id) {
  await api.delete(`/social/friends/${id}/`);
}

// 알림 (F-NTF-01) — 친구 요청·수락 알림. 실시간 push 없이 REST 조회 + 안읽음 배지.

// 내 알림 목록 (최신순) → [{ id, type, is_read, created_at, friendship_id, actor:{...} }]
// type: friend_request | friend_accept
export async function getNotifications() {
  const { data } = await api.get("/social/notifications/");
  return data;
}

// 헤더 🔔 배지용 안읽음 개수 (가벼운 폴링) → { count }
export async function getUnreadCount() {
  const { data } = await api.get("/social/notifications/unread/");
  return data.count;
}

// 모두 읽음 처리 (드롭다운 열람 시 배지 클리어) → { updated }
export async function markNotificationsRead() {
  const { data } = await api.post("/social/notifications/");
  return data;
}
