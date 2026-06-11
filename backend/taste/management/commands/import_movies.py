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


class Command(BaseCommand):
    help = "TMDB에서 인기 영화 수집 → movies 적재 (김호준)"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=2000)

    # python manage.py import_movies 의 진입점
    def handle(self, *args, **opts):
        if not settings.TMDB_API_KEY:
            raise CommandError("TMDB_API_KEY가 .env에 없습니다.")

        client = TMDBClient()
        target = opts["count"]
        self.stdout.write(f"[수집] TMDB 인기 영화 {target}편 시작 (언어: ko-KR)")

        ids = client.fetch_popular_ids(target)
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
