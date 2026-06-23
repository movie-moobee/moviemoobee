from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .services.recommend import get_explore, get_recommendations
from .services.taste_map import get_map


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recommendations(request):
    """안전(본 영화 kNN 근접)·미탐색(KDE 저밀도, 도달가능 밴드) 추천 (F-REC, 4.1/4.2).

    응답: {enough, safe:[...], unexplored:[...], today}.
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
def explore(request):
    """지도 탐색 탭 (F-MAP-03, 4.4): KDE 탐색도 배경 + 본 영화 + 안전·미탐색 추천(좌표 포함).

    응답: {enough, grid:{w,h,extent,values}, watched:[{x,y,rating}],
           safe:[{...,x,y,distance}], unexplored:[{...,x,y,density,continent}]}.
    안전·미탐색 = 추천 페이지와 같은 전역 Top N — 지도 핀으로 토글 표시.
    """
    return Response(get_explore(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request):
    """범용 영화 추천 AI 챗봇 (5.4). body {messages:[{role,content}]}.
    내 취향 집합 최근접 후보로 grounding 한 LLM 응답을 SSE(text/event-stream)로 스트리밍.
    """
    from .services.chat import general_messages, sse
    messages = general_messages(request.user, request.data.get("messages", []))
    resp = StreamingHttpResponse(sse(messages), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp
