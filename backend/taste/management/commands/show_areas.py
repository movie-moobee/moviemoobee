"""F-MAP-03 결과를 사람이 보기 좋게 출력 (김호준, 리뷰·시연용).

사용법:
    python manage.py show_areas            # 데모 3명 전부
    python manage.py show_areas demo_b     # 특정 유저만
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from taste.services.areas import detect_areas

User = get_user_model()
DEMO = ["demo_a", "demo_b", "demo_c"]


class Command(BaseCommand):
    help = "F-MAP-03 detect_areas 결과(안전/미탐색) 출력"

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="?", help="특정 유저명(생략 시 데모 3명)")

    def handle(self, *args, **opts):
        names = [opts["username"]] if opts["username"] else DEMO
        for name in names:
            user = User.objects.filter(username=name).first()
            if not user:
                self.stdout.write(f"[skip] {name} 없음 (seed_demo 먼저)")
                continue
            r = detect_areas(user)
            self.stdout.write("=" * 60)
            self.stdout.write(f"{user.username} ({user.nickname})  좌표={r['user_coord']}")
            if not r["enough"]:
                self.stdout.write("   (시청 5편 미만 — 지도·추천 비활성, 경고 오버레이 대상)\n")
                continue
            self.stdout.write("\n  [안전 추천] 내가 본 영화들과 가까운 영화 (kNN)")
            if not r["safe"]:
                self.stdout.write("   (좌표 없음 — 시청 0편)")
            for i, s in enumerate(r["safe"], 1):
                self.stdout.write(f"   {i:>2}. {s['title'][:34]:34} 거리={s['distance']:.3f}")
            self.stdout.write("\n  [미탐색 추천] 아직 안 가본 영역의 영화")
            if not r["unexplored"]:
                self.stdout.write("   (시청<5편 — KDE 불가)")
            for i, u in enumerate(r["unexplored"], 1):
                self.stdout.write(f"   {i:>2}. {u['title'][:34]:34} 밀도={u['density']:.3g}")
            self.stdout.write("")
