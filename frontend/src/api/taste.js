import { api } from "./client";

// 취향 지도·추천 API (F-MAP·F-REC) → /api/taste/

// 취향 지도: 본 영화 마커(좌표·밝기=KDE)·내 좌표 (F-MAP-01)
export async function getMyMap() {
  const { data } = await api.get("/taste/me/map");
  return data; // { enough, user_coord, watched:[{movie_id,title,poster_path,x,y,rating,brightness}] }
}
