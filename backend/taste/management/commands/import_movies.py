"""TMDB 인기 영화 수집 → movies/genres/keywords 적재 (By 인간 대동여지도, 0.5 데이터 파이프라인).

PoC-A(1_fetch_movies.py) 로직을 Django DB 적재로 이식.
- 인증: .env 의 TMDB_API_KEY 는 v4 Read Access Token(JWT) → Authorization: Bearer 헤더 사용.
- 멱등성: tmdb_id 기준 update_or_create 라 재실행해도 중복 안 생김.
- 좌표(umap_x/y)는 여기서 안 건드림 → build_coords 가 채움(전역 고정 좌표 불변식).
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from movies.models import Genre, Keyword, Movie
from movies.services.tmdb import TMDBClient


def _discover_ids(client, target, min_votes, sort_by="vote_count.desc"):
    """대중성 필터(vote_count 하한)를 건 영화 ID 수집. /discover/movie.

    TMDBClient(B 도메인)는 안 건드리고 공개 get()만 사용 — 페이지네이션은 여기(A)서 처리.
    min_votes: 평점 투표 수 하한(대중성 척도) — 저득표 잡영화 제외.
    sort_by: 기본 vote_count.desc(역대 다득표 = 대중적·안정).
    """
    ids, page, seen = [], 1, set()
    while len(ids) < target and page <= 500:
        results = client.get("/discover/movie", {
            "sort_by": sort_by,
            "vote_count.gte": min_votes,
            "include_adult": "false",
            "page": page,
        }).get("results", [])
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


class Command(BaseCommand):
    help = "TMDB에서 인기 영화 수집 → movies 적재 (김호준)"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=5000)
        parser.add_argument("--min-votes", type=int, default=300,
                            help="vote_count 하한(대중성 필터). 저득표 잡영화 제외")
        parser.add_argument("--fresh", action="store_true",
                            help="적재 전 기존 영화 전부 삭제(깨끗한 카탈로그 재구축; 시청기록도 cascade 삭제)")

    # python manage.py import_movies 의 진입점
    def handle(self, *args, **opts):
        if not settings.TMDB_API_KEY:
            raise CommandError("TMDB_API_KEY가 .env에 없습니다.")

        client = TMDBClient()
        target = opts["count"]
        min_votes = opts["min_votes"]

        if opts["fresh"]:
            n = Movie.objects.count()
            Movie.objects.all().delete()
            self.stdout.write(f"[초기화] 기존 영화 {n}편 삭제(--fresh)")

        self.stdout.write(f"[수집] TMDB 대중성 필터 영화 {target}편 시작 "
                          f"(vote_count>={min_votes}, 언어: ko-KR)")

        ids = _discover_ids(client, target, min_votes)
        self.stdout.write(f"[수집] 영화 ID {len(ids)}개")

        saved = 0
        for i, movie_id in enumerate(ids, 1):
            detail = client.fetch_detail(movie_id)
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

    # ---------- DB ----------

    def _save(self, d):
        # 멱.등.성 (Idempotency) : 재실행해도 문제없어.
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
                "cast": d.get("cast", ""),   # 배우 상위 5명(콤마 구분) — fetch_detail에서 추출(B)
            },
        )

        # 장르, 키워드도 (객체, 생성여부) 반환해서 0번 인덱스만 사용
        genres = [
            Genre.objects.get_or_create(name=name, defaults={"tmdb_genre_id": gid})[0]
            for gid, name in d["genres"]
        ]
        keywords = [
            Keyword.objects.get_or_create(name=name)[0] for name in d["keywords"]
        ]

        # movie 데이터와 장르 리스트를 다대다(Many-to-Many) 관계로 연결
        movie.genres.set(genres)
        movie.keywords.set(keywords)
