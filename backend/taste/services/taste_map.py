"""취향 지도 데이터 (F-MAP-01, 김호준).

지도에 뜨는 점은 오직 '내가 본 영화'(★) — 그 외 영화는 안 띄운다(불변식).
별 자체의 밝기·크기 = 내가 준 별점(높을수록 밝게 반짝). 와이어프레임 기준.
※ KDE 탐색도(밝은 안전영역/어두운 미탐색영역 '배경')는 영역 클릭=지도탐색이라 4.4에서 함께 넣는다.
※ 사용자 단일 좌표(무게중심)는 폐기됨 — 모든 로직이 본 영화 '집합' 기반(A-08/A-15). 지도엔 안 띄운다.
※ 취향 요약(와이어프레임 10 우측 박스):
  - 주 클러스터 = 내가 '좋아한' 영화 장르의 별점 가중 빈도(개인화).
  - 미탐색 = 실제 KDE 미탐색 추천 영화의 장르(좌표공간 기반). '안 본 큰 장르' 단순빈도로 내면
    카탈로그 쏠림(인기수집 → 범죄·스릴러)이 누구에게나 반복돼 편향 → 추천 엔진과 같은
    KDE 미탐색을 장르로 역집계해 편향 제거(라벨=엔진 일관). KDE 실패 시 카탈로그 폴백.
"""
import json
from pathlib import Path

from django.db.models import Count, FloatField, Q, Sum, Value
from django.db.models.functions import Cast, Greatest

from movies.models import Genre

LIKE_NEUTRAL = 3.0   # 좋아요 기준점(별점>3=좋아함). 안전추천(areas)과 동일. weight = max(rating-3, 0).

# 앵커(장르 대륙) 위치 — build_coords가 생성·커밋(anchors.json). 지도가 대륙 라벨/배경을 그린다(A-14).
_ANCHORS_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "anchors.json"
_anchors_cache = None


def _load_anchors():
    """앵커 [{name,x,y}] 로드(1회 캐시). 파일 없으면 [] — 좌표 미생성 시 지도는 대륙 없이 동작."""
    global _anchors_cache
    if _anchors_cache is None:
        try:
            _anchors_cache = json.loads(_ANCHORS_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            _anchors_cache = []
    return _anchors_cache


def genre_summary(user):
    """장르 빈도 기반 취향 요약 → {main:[장르2], unexplored:[장르2]}.

    - main(주 클러스터): 내가 '좋아한' 영화의 장르를 별점 가중 합으로 Top 2.
      weight = max(rating-3, 0) — 사용자 좌표·안전추천과 동일 철학(싫어한 장르는 취향 대표 아님).
      동률(정확히 같은 가중)은 id 순으로 결정적 처리(임의 동전던지기 제거).
      ※ 좋아한 영화가 0편(모든 별점 ≤3)이면 가중치가 전부 0 → 단순 시청 빈도로 폴백
        ('좋아한 게 없으면 본 것 전체로' — 안전추천의 liked 폴백과 같은 패턴).
    - unexplored(미탐색): 2칸. 1순위는 실제 KDE 미탐색 추천 영화 집합의 장르(좌표공간 기반·개인화,
      이미 본 장르 제외). KDE가 2칸을 못 채우면(후보 중 새 장르 0·1개) '안 본 큰 장르'(카탈로그
      크기순)로 남은 칸 보충 — 중복 제외. → 1칸은 개인화, 부족분만 카탈로그.
    호출부(get_map)가 5편 게이트 통과 후에만 부르므로 본 영화는 항상 ≥5편.
    ※ 쿼리당 집계는 1개만(Sum 또는 Count) — Sum/Count를 한 쿼리에 섞으면 다중 조인이
      행을 교차곱해 값이 부풀려진다(Django 알려진 함정). tiebreaker는 id 단독으로 충분.
    """
    uq = Q(movies__watch_records__user=user)   # 이 유저의 시청기록만 집계

    weighted = list(
        Genre.objects.filter(movies__watch_records__user=user)
        .annotate(w=Sum(Greatest(Cast("movies__watch_records__rating", FloatField()) - Value(LIKE_NEUTRAL),
                                 Value(0.0)), filter=uq, output_field=FloatField()))
        .order_by("-w", "id")   # 가중 desc → 동률 시 id(안정)
        .values_list("name", "w")[:2]
    )
    if weighted and float(weighted[0][1] or 0) >= 0.01:
        main = [name for name, _ in weighted]
    else:   # 좋아한 영화 0편 → 단순 시청 빈도로 폴백
        main = list(
            Genre.objects.filter(movies__watch_records__user=user)
            .annotate(c=Count("movies__watch_records", filter=uq))
            .order_by("-c", "id").values_list("name", flat=True)[:2]
        )

    # 미탐색 2칸: 1칸은 KDE 개인화 우선, 부족하면(0·1개) '안 본 큰 장르'로 보충.
    unexplored = _kde_unexplored_genres(user)
    if len(unexplored) < 2:
        for g in _catalog_unexplored_genres(user, uq, n=4):
            if g not in unexplored:        # KDE가 이미 올린 장르 중복 제외
                unexplored.append(g)
            if len(unexplored) >= 2:
                break
    return {"main": main, "unexplored": unexplored[:2]}


def _kde_unexplored_genres(user, pool=40, n=2):
    """실제 KDE 미탐색 추천 영화 집합의 장르 빈도 Top n.
    detect_areas(좌표공간 KDE 저밀도·도달밴드)로 미탐색 영화를 뽑아 그 장르를 역집계 →
    추천 엔진과 같은 신호라 카탈로그 쏠림 없이 개인화. KDE 실패(unexplored 빈) 시 [].

    ※ 이미 '보는' 장르는 제외한다 — KDE 미탐색 영화도 다장르라 드라마·액션 같은 큰 장르가
      섞여 들어오는데, 그러면 주 클러스터와 겹쳐 '미탐색=내가 보는 장르'라는 모순이 생긴다.
      미탐색은 '아직 안 가본 장르'여야 하므로 시청 장르를 빼고 진짜 새 장르만 남긴다."""
    from .areas import detect_areas   # 순환참조 방지(areas는 taste_map을 import 안 함)

    areas = detect_areas(user, safe_top=1, unexplored_top=pool)
    movie_ids = [it["movie_id"] for it in areas["unexplored"]]
    if not movie_ids:
        return []
    watched_genre_ids = (
        Genre.objects.filter(movies__watch_records__user=user)
        .values_list("id", flat=True).distinct()
    )
    return list(
        Genre.objects.filter(movies__id__in=movie_ids)
        .exclude(id__in=watched_genre_ids)   # 이미 보는 장르는 미탐색 아님(겹침·큰장르 누수 제거)
        .annotate(c=Count("movies", filter=Q(movies__id__in=movie_ids)))
        .order_by("-c", "id").values_list("name", flat=True)[:n]
    )


def _catalog_unexplored_genres(user, uq, n=2):
    """폴백: 안 본 장르 중 카탈로그 큰 것 Top n. 모든 장르를 본 헤비유저면 가장 적게 본 장르로."""
    watched_genre_ids = (
        Genre.objects.filter(movies__watch_records__user=user)
        .values_list("id", flat=True).distinct()
    )
    out = list(
        Genre.objects.exclude(id__in=watched_genre_ids)
        .annotate(c=Count("movies")).order_by("-c", "id")
        .values_list("name", flat=True)[:n]
    )
    if not out:   # 모든 장르를 본 헤비유저 → 가장 적게 본 장르
        out = list(
            Genre.objects.annotate(c=Count("movies__watch_records", filter=uq))
            .order_by("c", "id").values_list("name", flat=True)[:n]
        )
    return out


def get_map(user):
    """취향 지도 렌더 데이터. {enough, watched:[...]}.

    enough=False(시청<MAP_MIN_WATCHED)면 watched 는 빈 리스트 — 프론트가 경고 오버레이를
    띄운다(차단 403 아님). 별점(rating)은 별 밝기, 좌표(x,y)는 마커 위치.
    """
    from .areas import MAP_MIN_WATCHED  # 게이트 기준값(추천과 단일 출처)

    rows = list(user.watch_records.filter(
        movie__map_x__isnull=False, movie__map_y__isnull=False
    ).values_list(
        "movie_id", "movie__title", "movie__poster_path",
        "movie__release_year", "movie__map_x", "movie__map_y", "rating",
    ))

    if len(rows) < MAP_MIN_WATCHED:
        return {"enough": False, "watched": []}

    watched = [{
        "movie_id": r[0],
        "title": r[1],
        "poster_path": r[2] or "",
        "release_year": r[3],
        "x": float(r[4]),
        "y": float(r[5]),
        "rating": float(r[6]),
    } for r in rows]
    return {"enough": True, "watched": watched, "summary": genre_summary(user),
            "anchors": _load_anchors()}
