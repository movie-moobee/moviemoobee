import { api } from "./client";

// 시청기록 API (F-WAT·온보딩 공용) → /api/watch-records/
export async function listWatchRecords() {
  const { data } = await api.get("/watch-records/");
  return data;
}

// 등록 (별점 필수, review·watched_on 선택)
export async function createWatchRecord({ movie, rating, review, watched_on }) {
  const { data } = await api.post("/watch-records/", { movie, rating, review, watched_on });
  return data;
}

// 별점·리뷰 수정 (인라인 수정)
export async function updateWatchRecord(id, payload) {
  const { data } = await api.patch(`/watch-records/${id}/`, payload);
  return data;
}

// 삭제
export async function deleteWatchRecord(id) {
  await api.delete(`/watch-records/${id}/`);
}
