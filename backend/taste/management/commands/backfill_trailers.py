"""기존 영화에 예고편(유튜브) 키 backfill (김호준).

Movie.trailer_key 필드 추가 후, 이미 DB에 있는 영화들의 빈 trailer_key 를 채운다.
※ import_movies 재실행이 아니라 '기존 영화 순회'로 채운다 — discover 재조회가
  좌표 없는 잡영화를 유입시키는 드리프트(A-07)를 피하기 위함.
TMDB 호출은 영화당 1회(videos). 기본은 빈 것만(재실행=이어서 채움), --all 은 전체 재조회.

⚠ Movie.trailer_key 필드(마이그레이션, B)가 머지된 뒤에야 동작한다.
"""
import time

from django.core.management.base import BaseCommand

from movies.models import Movie
from movies.services.tmdb import TMDBClient


class Command(BaseCommand):
    help = "기존 영화의 빈 trailer_key 를 TMDB videos 로 채움 (김호준)"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true",
                            help="이미 채워진 것도 다시 조회(기본: 빈 것만 → 재실행 시 이어서)")

    def handle(self, *args, **opts):
        client = TMDBClient()
        qs = Movie.objects.all() if opts["all"] else Movie.objects.filter(trailer_key="")
        total = qs.count()
        self.stdout.write(f"[예고편] 대상 {total}편 (기존 영화 순회, discover 재조회 없음)")

        filled = 0
        for i, movie in enumerate(qs.iterator(), 1):
            detail = client.fetch_detail(movie.tmdb_id)   # fetch_detail이 videos까지 받아 trailer_key 반환(B)
            key = detail.get("trailer_key", "") if detail else ""
            if key:
                movie.trailer_key = key
                movie.save(update_fields=["trailer_key"])
                filled += 1
            if i % 100 == 0:
                self.stdout.write(f"  ...{i}/{total} (채움 {filled})")
            time.sleep(0.05)   # rate limit 보호

        self.stdout.write(self.style.SUCCESS(
            f"[완료] {filled}편 예고편 키 채움 (대상 {total}편 중)"
        ))
