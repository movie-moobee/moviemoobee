"""사용자 좌표 계산 (F-MAP-00).
user 좌표 = 시청 영화 좌표의 별점 가중 평균 (weight = rating - 3.0).
별점 추가/수정/삭제 시에만 호출하고 user.coord_x/y 에 캐싱한다.
"""

def recompute_user_coord(user):
    # TODO: watch_records 좌표 + 별점으로 가중 평균 → user.coord_x/y 저장
    raise NotImplementedError
