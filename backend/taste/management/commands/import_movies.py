"""TMDB 인기 영화 수집 → movies/genres/keywords 적재 (개발자 A, 0.5 데이터 파이프라인).

PoC-A(1_fetch_movies.py) 로직을 Django DB 적재로 이식.
- 인증: .env 의 TMDB_API_KEY 는 v4 Read Access Token(JWT) → Authorization: Bearer 헤더 사용.
- 멱등성: tmdb_id 기준 update_or_create 라 재실행해도 중복 안 생김.
- 좌표(umap_x/y)는 여기서 안 건드림 → build_coords 가 채움(전역 고정 좌표 불변식).
"""
import time
from datetime import datetime

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from movies.models import Genre, Keyword, Movie

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


class Command(BaseCommand):
    help = "TMDB에서 인기 영화 수집 → movies 적재 (개발자 A)"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=2000)

    def handle(self, *args, **opts):
        api_key = settings.TMDB_API_KEY
        if not api_key:
            raise CommandError("TMDB_API_KEY가 .env에 없습니다.")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

        target = opts["count"]
        self.stdout.write(f"[수집] TMDB 인기 영화 {target}편 시작 (언어: {LANGUAGE})")

        ids = self._fetch_popular_ids(target)
        self.stdout.write(f"[수집] 영화 ID {len(ids)}개")

        saved = 0
        for i, movie_id in enumerate(ids, 1):
            detail = self._fetch_detail(movie_id)
            if detail and detail["genres"]:  # 장르 없는 건 제외(PoC와 동일)
                self._save(detail)
                saved += 1
            if i % 50 == 0:
                self.stdout.write(f"  ...{i}/{len(ids)} 처리 (적재 {saved})")
            time.sleep(0.05)  # rate limit 보호

        self.stdout.write(self.style.SUCCESS(
            f"[완료] {saved}편 적재 "
            f"(genres={Genre.objects.count()}, keywords={Keyword.objects.count()}, "
            f"movies={Movie.objects.count()})"
        ))

    # ---------- TMDB ----------
    def _get(self, path, params=None):
        for attempt in range(3):
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

    def _fetch_popular_ids(self, target):
        ids, page = [], 1
        seen = set()
        while len(ids) < target and page <= 500:
            results = self._get("/movie/popular", {"page": page}).get("results", [])
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

    def _fetch_detail(self, movie_id):
        try:
            data = self._get(
                f"/movie/{movie_id}",
                {"append_to_response": "credits,keywords"},
            )
        except requests.RequestException:
            return None
        if not data.get("id"):
            return None
        crew = data.get("credits", {}).get("crew", [])
        directors = [c["name"] for c in crew if c.get("job") == "Director"]
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
            "genres": [(g["id"], g["name"]) for g in data.get("genres", [])],
            "keywords": [k["name"] for k in data.get("keywords", {}).get("keywords", [])],
        }

    # ---------- DB ----------
    def _save(self, d):
        movie, _ = Movie.objects.update_or_create(
            tmdb_id=d["tmdb_id"],
            defaults={
                "title": d["title"],
                "original_title": d["original_title"],
                "overview": d["overview"],
                "release_date": d["release_date"],
                "release_year": d["release_year"],
                "runtime": d["runtime"],
                "vote_average": d["vote_average"],
                "vote_count": d["vote_count"],
                "original_language": d["original_language"],
                "poster_path": d["poster_path"],
                "director": d["director"],
            },
        )
        genres = [
            Genre.objects.get_or_create(name=name, defaults={"tmdb_genre_id": gid})[0]
            for gid, name in d["genres"]
        ]
        keywords = [
            Keyword.objects.get_or_create(name=name)[0] for name in d["keywords"]
        ]
        movie.genres.set(genres)
        movie.keywords.set(keywords)
