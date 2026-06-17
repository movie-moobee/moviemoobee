"""장르별 '깨끗한' 데모 유저 시드 (김호준, 추천 검증용 — A-08).

각 유저가 한 장르의 인기 12편만 5점으로 시청 → 단일 장르 페르소나.
안전 추천(본 영화 kNN)이 그 장르를 제대로 잡는지 눈으로 확인하기 위한 데이터.
시청기록 개별 생성 → 시그널로 좌표 자동 캐싱(seed_demo와 동일).
멱등성: 재실행 시 기존 장르 데모 유저를 지우고 다시 만든다.

사용법:
    python manage.py seed_genre_demos
    python manage.py show_areas genre_horror   # 장르별 안전/미탐색 추천 확인
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from movies.models import Genre, Movie, WatchRecord

User = get_user_model()

# (username, nickname, 장르명) — 장르명은 TMDB ko-KR 기준
GENRE_DEMOS = [
    ("genre_horror", "장르_공포", "공포"),
    ("genre_romance", "장르_로맨스", "로맨스"),
    ("genre_action", "장르_액션", "액션"),
    ("genre_comedy", "장르_코미디", "코미디"),
    ("genre_crime", "장르_범죄", "범죄"),
    ("genre_anime", "장르_애니", "애니메이션"),
    ("genre_doc", "장르_다큐", "다큐멘터리"),
    ("genre_music", "장르_음악", "음악"),
]
N_WATCH = 12   # 장르당 시청 편수(인기순)


class Command(BaseCommand):
    help = "장르별 단일 취향 데모 유저 시드 (추천 검증용, 김호준)"

    def handle(self, *args, **opts):
        if not Movie.objects.filter(umap_x__isnull=False).exists():
            raise CommandError("좌표 있는 영화가 없습니다. loaddata movies 또는 build_coords 먼저 실행하세요.")

        # 멱등성: 기존 장르 데모 유저 삭제(시청기록 cascade)
        User.objects.filter(username__in=[u for u, _, _ in GENRE_DEMOS]).delete()

        made = 0
        for username, nickname, gname in GENRE_DEMOS:
            genre = Genre.objects.filter(name=gname).first()
            movies = list(
                Movie.objects.filter(genres=genre, umap_x__isnull=False)
                .order_by("-vote_count")[:N_WATCH]
            )
            if len(movies) < 5:
                self.stdout.write(f"[skip] '{gname}' 좌표 영화 {len(movies)}편(<5) — 건너뜀")
                continue

            user = User.objects.create(username=username, nickname=nickname,
                                       email=f"{username}@demo.local")
            user.set_password("demo1234")
            user.save(update_fields=["password"])
            for m in movies:
                WatchRecord.objects.create(user=user, movie=m, rating=5.0)  # 시그널이 좌표 캐싱

            user.refresh_from_db()
            made += 1
            self.stdout.write(
                f"  {username}: '{gname}' {len(movies)}편(5.0) "
                f"→ 좌표 ({user.coord_x:.2f}, {user.coord_y:.2f})"
            )

        self.stdout.write(self.style.SUCCESS(
            f"[완료] 장르 데모 {made}명 (비밀번호 demo1234). "
            f"확인: python manage.py show_areas genre_horror"
        ))
