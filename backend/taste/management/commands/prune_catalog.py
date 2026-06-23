"""카탈로그 정리: 2000년 이전 + 에로틱 로맨스 + 포스터 없는 유령 영화를 DB에서 삭제 (김호준, 큐레이션).

기본은 미리보기(dry-run) — 무엇이 지워지고 시청기록이 몇 건 사라지는지만 출력한다.
실제 삭제는 --execute 를 줘야 한다(Movie 삭제 시 WatchRecord가 CASCADE로 함께 삭제됨).

사용:
    python manage.py prune_catalog              # 미리보기만
    python manage.py prune_catalog --execute     # 실제 삭제
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from movies.models import Movie, WatchRecord

PRE_YEAR = 2000   # 이 연도 미만(< 2000) 삭제

# 정밀 에로틱 키워드만 (광범위한 'sex'는 정상 영화 오탐이라 제외)
EROTIC_KEYWORDS = ["erotic", "eroticism", "erotique", "bdsm", "softcore", "sexploitation", "spanking"]
# 키워드가 비어 키워드론 못 잡는 명백한 에로틱 로맨스 (제목 부분일치)
MANUAL_RACY_TITLES = ["가브리엘의 지옥", "365일", "그레이의 50가지"]

# 포스터 없는 영화 = 시각 추천에서 카드도 못 그리는 '유령'(정보 빈약·러닝타임 12분 등) → 영구 제외.
# ※ 줄거리(overview)·러닝타임은 기준으로 안 씀: 줄거리 빈값은 대부분 정상 외국영화의 한글번역 누락,
#    단편은 정상 픽사 단편이라 오배제된다(검증). 포스터 결측만이 깨끗한 유령 신호.


class Command(BaseCommand):
    help = "2000년 이전 + 에로틱 로맨스 영화를 DB에서 삭제 (기본 미리보기, --execute로 실삭제)"

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true", help="실제 삭제 수행(미지정 시 미리보기)")

    def handle(self, *args, **opts):
        pre = Q(release_year__lt=PRE_YEAR)

        racy_kw = Q(keywords__name__in=EROTIC_KEYWORDS)
        racy_title = Q()
        for t in MANUAL_RACY_TITLES:
            racy_title |= Q(title__icontains=t)
        racy = racy_kw | racy_title

        ghost = Q(poster_path="")   # 포스터 없는 유령

        target = Movie.objects.filter(pre | racy | ghost).distinct()
        target_ids = list(target.values_list("id", flat=True))

        n_pre = Movie.objects.filter(pre).count()
        n_racy = Movie.objects.filter(racy).distinct().count()
        n_ghost = Movie.objects.filter(ghost).count()
        n_total = len(target_ids)
        n_wr = WatchRecord.objects.filter(movie_id__in=target_ids).count()

        self.stdout.write(f"전체 {Movie.objects.count()}편")
        self.stdout.write(f"  - 2000년 이전: {n_pre}편")
        self.stdout.write(f"  - 에로틱(키워드+수동): {n_racy}편")
        self.stdout.write(f"  - 포스터 없는 유령: {n_ghost}편")
        self.stdout.write(f"  = 삭제 대상(중복 제거): {n_total}편  →  삭제 후 {Movie.objects.count() - n_total}편")
        self.stdout.write(f"  함께 삭제될 시청기록(CASCADE): {n_wr}건")

        # 에로틱 매칭은 양이 적으니 전부, 시청기록 걸린 영화도 전부 보여준다(검토용)
        self.stdout.write("\n[에로틱 매칭 영화]")
        for m in Movie.objects.filter(racy).distinct().order_by("title"):
            self.stdout.write(f"   {m.title} ({m.release_year}) 평점{m.vote_average}")
        self.stdout.write("\n[삭제로 사라지는 시청기록]")
        for u, t, y in (WatchRecord.objects.filter(movie_id__in=target_ids)
                        .values_list("user__username", "movie__title", "movie__release_year")):
            self.stdout.write(f"   {u}: {t} ({y})")

        if not opts["execute"]:
            self.stdout.write(self.style.WARNING("\n[미리보기] 실제 삭제하려면 --execute 를 붙이세요."))
            return

        deleted, _ = Movie.objects.filter(id__in=target_ids).delete()   # distinct() 큐셋은 delete 불가 → id로
        from taste.services.areas import clear_movies_cache
        clear_movies_cache()   # 좌표 캐시 무효화(삭제된 영화 빠지도록)
        self.stdout.write(self.style.SUCCESS(
            f"\n[완료] 영화 {n_total}편 + 관련 행 삭제. 남은 영화 {Movie.objects.count()}편."))
