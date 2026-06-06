"""추천 (F-REC). 안전=코사인 Top N, 미탐색=KDE 저밀도. 이미 본 영화 제외."""

def safe_recommendations(user, n=10):
    # TODO: 사용자 좌표와 코사인 유사도 Top N
    raise NotImplementedError

def unexplored_recommendations(user, n=10):
    # TODO: 미탐색(저밀도) 영역에서 선정
    raise NotImplementedError
