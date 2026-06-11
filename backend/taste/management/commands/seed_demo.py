"""시연·테스트용 데모 시드 (Made By KHJ).
데모 유저 + 취향 편향 시청기록(별점) + 친구관계를 만든다.
시청기록을 개별 생성하므로 시그널이 발동해 각 유저 좌표(coord_x/y)가 자동 캐싱된다.
멱등성: 재실행 시 기존 데모 유저를 지우고 다시 만든다.
"""
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from django.utils import timezone

from movies.models import Genre, Movie, WatchRecord
from social.models import Friendship

User = get_user_model()

DEMO_USERS = [
    ("demo_a", "데모유저A"),
    ("demo_b", "데모유저B"),
    ("demo_c", "데모유저C"),
]
N_PRIMARY = 10   # 주 취향 영화 (높은 별점)
N_RANDOM = 5     # 그 외 영화 (낮은 별점)


def _rating(low, high):
    return round(random.uniform(low, high) * 2) / 2  # 0.5 단위


class Command(BaseCommand):
    help = "시연용 데모 계정/시청기록(별점)/친구 시드 (개발자 A)"

    def handle(self, *args, **opts):
        random.seed(42)
        if not Movie.objects.filter(umap_x__isnull=False).exists():
            raise CommandError("좌표 있는 영화가 없습니다. loaddata movies 또는 build_coords 먼저 실행하세요.")

        # 멱등성: 기존 데모 유저 삭제(시청기록·친구는 cascade)
        User.objects.filter(username__in=[u for u, _ in DEMO_USERS]).delete()

        # 영화가 가장 많은 상위 장르를 데모 유저별 주 취향으로 배정
        primary_genres = list(
            Genre.objects.annotate(
                n=Count("movies", filter=Q(movies__umap_x__isnull=False))
            ).order_by("-n")[:len(DEMO_USERS)]
        )

        users = []
        for (username, nickname), genre in zip(DEMO_USERS, primary_genres):
            user = User.objects.create(
                username=username,
                nickname=nickname,
                email=f"{username}@demo.local",
            )
            user.set_password("demo1234")
            user.save(update_fields=["password"])

            primary = list(
                Movie.objects.filter(genres=genre, umap_x__isnull=False).values_list("id", flat=True)
            )
            others = list(
                Movie.objects.filter(umap_x__isnull=False).exclude(genres=genre).values_list("id", flat=True)
            )
            pick_primary = random.sample(primary, min(N_PRIMARY, len(primary)))
            pick_others = random.sample(others, min(N_RANDOM, len(others)))

            for mid in pick_primary:
                WatchRecord.objects.create(user=user, movie_id=mid, rating=_rating(3.5, 5.0))
            for mid in pick_others:
                WatchRecord.objects.create(user=user, movie_id=mid, rating=_rating(1.5, 3.0))

            user.refresh_from_db()
            users.append(user)
            self.stdout.write(
                f"  {username}: 주취향 '{genre.name}' "
                f"{len(pick_primary)+len(pick_others)}편 시청 "
                f"→ 좌표 ({user.coord_x:.2f}, {user.coord_y:.2f})"
            )

        # 친구관계: A ↔ B 수락됨
        Friendship.objects.create(
            requester=users[0], addressee=users[1],
            status=Friendship.Status.ACCEPTED, responded_at=timezone.now(),
        )

        self.stdout.write(self.style.SUCCESS(
            f"[완료] 데모 유저 {len(users)}명 + 시청기록 + 친구 1쌍 (비밀번호 demo1234)"
        ))
