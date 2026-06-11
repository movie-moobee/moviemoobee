from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


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
