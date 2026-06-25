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

// 취향 비교 지도 (F-FRD-05, 5.3) — 두 사람 본 영화를 같은 앵커 공간에 겹쳐 비교.
// → { anchors:[{name,x,y}], me:{watched:[...],main:[장르]}, friend:{nickname,watched,main}, shared_ids:[id] }
export async function getFriendCompare(id) {
  const { data } = await api.get(`/social/friends/${id}/compare/`);
  return data;
}

// '같이 볼 영화' 챗봇 추천을 지도에 표시할 때 매칭·좌표용 후보 (5.4)
// → [{ id, title, poster_path, x, y }]
export async function getCowatchCandidates(id) {
  const { data } = await api.get(`/social/friends/${id}/cowatch/candidates/`);
  return data;
}

// '같이 볼 영화' 챗봇 오늘 사용량(계정당 하루 한도) → { used, limit } (5.4)
export async function getCowatchUsage() {
  const { data } = await api.get("/social/cowatch/usage/");
  return data;
}

// 알림 (F-NTF-01) — 친구 요청·수락 알림. 실시간 push 없이 REST 조회 + 안읽음 배지.

// 내 알림 목록 (최신순) → [{ id, type, is_read, created_at, friendship_id, actor:{...} }]
// type: friend_request | friend_accept
export async function getNotifications() {
  const { data } = await api.get("/social/notifications/");
  return data;
}

// 헤더 🔔 배지용 안읽음 개수 (SSE 끊겼을 때 폴백) → { count }
export async function getUnreadCount() {
  const { data } = await api.get("/social/notifications/unread/");
  return data.count;
}

// 안읽음 개수 SSE 스트림 — 준실시간 배지(F-NTF-01). EventSource는 헤더를 못 보내므로
// chat 스트림처럼 fetch + ReadableStream + 토큰 헤더로 SSE를 직접 파싱한다.
// onMessage({ unread }) 로 갱신. signal(AbortController)로 종료. 연결 끊기면 throw → 호출측 재연결.
export async function streamUnread(onMessage, signal) {
  const token = localStorage.getItem("token");
  const res = await fetch("/api/social/notifications/stream/", {
    headers: { ...(token ? { Authorization: `Token ${token}` } : {}) },
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`notif-stream ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {     // SSE 이벤트 경계
      const ev = buf.slice(0, i).trim();
      buf = buf.slice(i + 2);
      if (!ev.startsWith("data:")) continue;     // ': ping' 하트비트 무시
      try {
        onMessage(JSON.parse(ev.slice(5).trim()));
      } catch {
        /* 깨진 청크 무시 */
      }
    }
  }
}

// 모두 읽음 처리 (드롭다운 열람 시 배지 클리어) → { updated }
export async function markNotificationsRead() {
  const { data } = await api.post("/social/notifications/");
  return data;
}
