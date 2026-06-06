"""미탐색·안전 영역 감지 (F-MAP-03).
안전 = 사용자 좌표와 코사인 유사도 상위. 미탐색 = 시청 분포 KDE 저밀도.
같은 KDE 밀도가 지도 밝기 레이어로도 쓰인다(F-MAP-01).
"""

def detect_areas(user):
    # TODO: KDE / 코사인으로 영역 산출
    raise NotImplementedError
