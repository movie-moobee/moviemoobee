"""사용자 좌표 계산 (F-MAP-00).
user 좌표 = 시청한 '선호' 영화 좌표의 별점 가중 평균 (weight = max(rating - 3.0, 0)).
별점 추가/수정/삭제 시에만 호출하고 user.coord_x/y 에 캐싱한다(조회마다 재계산 금지).
"""
from django.db.models import Count, F, FloatField, Sum, Value
from django.db.models.functions import Cast, Greatest
from django.utils import timezone   # 서버 시간대 반영된 현재 시각

NEUTRAL_RATING = 3.0


def recompute_user_coord(user):
    """user 의 시청기록으로 좌표를 다시 계산해 캐싱한다.

    - weight = max(rating - 3.0, 0)  → 3.5점↑만 중심을 끌어당김. 비선호(≤3점)는 0(중심에 영향 없음).
      (비선호를 '반대로 밀어내기'는 UMAP 좌표계 원점이 임의값이라 의미가 없어 채택 안 함.
       싫어요 신호는 추천/지도 KDE 단계에서 처리.)
    - 좌표 = Σ(w·coord) / Σw.  선호 영화가 0편(Σw≈0)이면 '본 영화 단순평균'으로 fallback.
    - 좌표 있는 영화만 사용. 시청 0편이면 좌표를 비운다.
    - 집계는 DB(Aggregate)에서 끝내고 숫자만 받아온다(시청기록 행을 파이썬으로 로딩하지 않음).
    """
    w = Greatest(Cast("rating", FloatField()) - Value(NEUTRAL_RATING), Value(0.0),
                 output_field=FloatField())          # max(rating-3, 0)
    agg = user.watch_records.filter(
        movie__umap_x__isnull=False, movie__umap_y__isnull=False
    ).aggregate(
        n=Count("id"),
        sx=Sum("movie__umap_x"),                                    # 단순평균용 Σx
        sy=Sum("movie__umap_y"),
        wx=Sum(w * F("movie__umap_x"), output_field=FloatField()),  # Σ(w·x)
        wy=Sum(w * F("movie__umap_y"), output_field=FloatField()),  # Σ(w·y)
        wsum=Sum(w, output_field=FloatField()),                     # Σw (분모, 항상 ≥0)
    )

    n = agg["n"]
    if not n:                       # 좌표 있는 시청기록이 없는 경우
        coord_x = coord_y = None
    elif agg["wsum"] < 0.01:        # 선호(3점 초과) 영화 없음 → 본 영화 단순평균 # 생각해볼점 : 선호하는 영화 없다면 선호하는 영화를 최소한 몇개는 삽입해야한다고 안내를 해야할지 여부.
        coord_x = agg["sx"] / n
        coord_y = agg["sy"] / n
    else:                           # 메인 로직 : 선호 영화 별점 가중 무게중심
        coord_x = agg["wx"] / agg["wsum"]
        coord_y = agg["wy"] / agg["wsum"]

    # 파생 필드만 원자적 UPDATE (인스턴스 로드/다른 필드 간섭 없음)
    now = timezone.now()
    type(user).objects.filter(pk=user.pk).update(
        coord_x=coord_x, coord_y=coord_y, coord_updated_at=now
    )
    # .update()는 인메모리 인스턴스를 안 바꾸므로, 호출자가 같은 요청에서
    # user.coord_* 를 참조해도 최신값이 보이도록 직접 동기화한다.
    user.coord_x, user.coord_y, user.coord_updated_at = coord_x, coord_y, now


# --- 참고: DB Aggregate 도입 전의 파이썬 루프 버전 (가독성용 보존, 동작 동일) ---
# 시청기록이 아주 많은 헤비유저면 행을 전부 파이썬으로 올리므로 위 Aggregate 버전을 사용한다.
# def recompute_user_coord(user):
#     records = user.watch_records.filter(
#         movie__umap_x__isnull=False, movie__umap_y__isnull=False
#     ).select_related("movie")
#     xs, ys, ws = [], [], []
#     for r in records:
#         ws.append(max(float(r.rating) - NEUTRAL_RATING, 0.0))  # 비선호는 0 (중심 제외)
#         xs.append(r.movie.umap_x)
#         ys.append(r.movie.umap_y)
#     wsum = sum(ws)
#     if not xs:
#         coord_x = coord_y = None
#     elif wsum < 0.01:               # 선호 영화 없음 → 본 영화 단순평균
#         coord_x = sum(xs) / len(xs)
#         coord_y = sum(ys) / len(ys)
#     else:
#         coord_x = sum(w * x for w, x in zip(ws, xs)) / wsum
#         coord_y = sum(w * y for w, y in zip(ws, ys)) / wsum
#     type(user).objects.filter(pk=user.pk).update(
#         coord_x=coord_x, coord_y=coord_y, coord_updated_at=timezone.now())
