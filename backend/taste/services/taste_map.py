"""취향 지도 데이터 (F-MAP-01, 김호준).

지도에 뜨는 점은 오직 '내가 본 영화'(★) — 그 외 영화는 안 띄운다(불변식).
별 자체의 밝기·크기 = 내가 준 별점(높을수록 밝게 반짝). 와이어프레임 기준.
※ KDE 탐색도(밝은 안전영역/어두운 미탐색영역 '배경')는 영역 클릭=지도탐색이라 4.4에서 함께 넣는다.
※ 무게중심(user_coord)은 안전추천에서 버렸고 지도에서도 표시 안 함(A-10 제거 방향).
"""


def get_map(user):
    """취향 지도 렌더 데이터. {enough, watched:[...]}.

    enough=False(시청<MAP_MIN_WATCHED)면 watched 는 빈 리스트 — 프론트가 경고 오버레이를
    띄운다(차단 403 아님). 별점(rating)은 별 밝기, 좌표(x,y)는 마커 위치.
    """
    from .areas import MAP_MIN_WATCHED  # 게이트 기준값(추천과 단일 출처)

    rows = list(user.watch_records.filter(
        movie__umap_x__isnull=False, movie__umap_y__isnull=False
    ).values_list(
        "movie_id", "movie__title", "movie__poster_path",
        "movie__release_year", "movie__umap_x", "movie__umap_y", "rating",
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
    return {"enough": True, "watched": watched}
