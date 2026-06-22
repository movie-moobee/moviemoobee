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
