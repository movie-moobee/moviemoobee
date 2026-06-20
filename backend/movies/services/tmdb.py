"""TMDB API 공용 클라이언트.

import_movies 커맨드와 조회 API 양쪽에서 import해서 쓸 수 있도록
호출 로직을 Command 클래스 바깥으로 추출.
"""
import time
from datetime import datetime

import requests
from django.conf import settings

BASE_URL = "https://api.themoviedb.org/3"
LANGUAGE = "ko-KR"


def _parse_date(s):
    """'YYYY-MM-DD' → date, 빈 값/형식오류 → None."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _pick_trailer_key(videos):
    """videos 목록에서 YouTube Trailer 키 1개 선택(공식 우선). 없으면 ''."""
    trailers = [
        v for v in videos
        if v.get("site") == "YouTube" and v.get("type") == "Trailer"
    ]
    if not trailers:
        return ""
    official = [v for v in trailers if v.get("official")]
    return (official or trailers)[0]["key"]


class TMDBClient:
    """TMDB v4 Read Access Token 기반 클라이언트."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {settings.TMDB_API_KEY}"}
        )

    def get(self, path, params=None):
        """GET 요청 — 429 시 최대 3회 재시도."""
        for _ in range(3):
            res = self.session.get(
                f"{BASE_URL}{path}",
                params={**(params or {}), "language": LANGUAGE},
                timeout=10,
            )
            if res.status_code == 429:
                time.sleep(int(res.headers.get("Retry-After", 1)))
                continue
            res.raise_for_status()
            return res.json()
        return {}

    def fetch_popular_ids(self, target):
        """인기 영화 ID 목록을 target 개수만큼 수집."""
        ids, page = [], 1
        seen = set()
        while len(ids) < target and page <= 500:
            results = self.get("/movie/popular", {"page": page}).get("results", [])
            if not results:
                break
            for m in results:
                if m["id"] not in seen:
                    seen.add(m["id"])
                    ids.append(m["id"])
                if len(ids) >= target:
                    break
            page += 1
        return ids[:target]

    def fetch_watch_providers(self, tmdb_id):
        """KR flatrate OTT 목록 반환. 없으면 빈 리스트."""
        try:
            data = self.get(f"/movie/{tmdb_id}/watch/providers")
        except Exception:
            return []
        flatrate = data.get("results", {}).get("KR", {}).get("flatrate", [])
        return [{"name": p["provider_name"], "logo": p["logo_path"]} for p in flatrate]

    def fetch_detail(self, movie_id):
        """영화 상세 정보(장르·키워드·감독·예고편 포함) 조회.

        예고편(videos)도 append_to_response로 한 번에 받아 import 시 DB 적재
        → 상세 조회 때 TMDB 실시간 호출 없이 trailer_key로 즉시 노출.
        """
        try:
            data = self.get(
                f"/movie/{movie_id}",
                {"append_to_response": "credits,keywords,videos"},
            )
        except requests.RequestException:
            return None
        if not data.get("id"):
            return None
        crew = data.get("credits", {}).get("crew", [])
        directors = [c["name"] for c in crew if c.get("job") == "Director"]
        cast_list = data.get("credits", {}).get("cast", [])
        return {
            "tmdb_id": data["id"],
            "title": data.get("title", ""),
            "original_title": data.get("original_title", ""),
            "overview": data.get("overview", ""),
            "release_date": _parse_date(data.get("release_date")),
            "release_year": int((data.get("release_date") or "0")[:4] or 0) or None,
            "runtime": data.get("runtime") or None,
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "original_language": data.get("original_language", ""),
            "poster_path": data.get("poster_path") or "",
            "director": directors[0] if directors else "",
            "cast": ",".join([c["name"] for c in cast_list[:5]]),
            "genres": [(g["id"], g["name"]) for g in data.get("genres", [])],
            "keywords": [k["name"] for k in data.get("keywords", {}).get("keywords", [])],
            "trailer_key": _pick_trailer_key(data.get("videos", {}).get("results", [])),
        }
