from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .services.recommend import get_recommendations
from .services.taste_map import get_map


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recommendations(request):
    """안전(좌표거리 근접)·미탐색(KDE 저밀도, 도달가능 밴드) 추천 (F-REC, 4.1/4.2).

    응답: {enough, user_coord, safe:[...], unexplored:[...]}.
    enough=False(시청<5)면 safe/unexplored 는 빈 리스트 — 200 OK로 내리고
    프론트가 경고 오버레이를 띄운다(3.3). 차단(403)이 아니다.
    """
    return Response(get_recommendations(request.user))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def taste_map(request):
    """취향 지도 데이터 (F-MAP-01): 본 영화 마커(좌표·별점).

    응답: {enough, watched:[{movie_id,title,poster_path,release_year,x,y,rating}]}.
    별점=별 밝기. enough=False(시청<5)면 watched 는 빈 리스트 — 프론트가 경고 오버레이(차단 아님).
    """
    return Response(get_map(request.user))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_coord(request):
    """내 취향 좌표(캐시값) 반환 (F-MAP-00). 좌표는 별점 변경 시에만 재계산됨.

    선호 영화가 없으면 coord_x/y 는 null 로 내려간다(프론트는 null 처리 필요). -> 책임 전가 아님.
    """
    user = request.user
    return Response({
        "coord_x": user.coord_x,
        "coord_y": user.coord_y,
        "coord_updated_at": user.coord_updated_at,
    })
