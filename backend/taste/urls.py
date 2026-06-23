from django.urls import path

from . import views

urlpatterns = [
    path("me/map", views.taste_map, name="taste_map"),  # GET 취향 지도(본 영화 마커·밝기) (F-MAP-01)
    path("recommendations", views.recommendations, name="recommendations"),  # GET 안전·미탐색 추천 (F-REC, 4.1/4.2)
    path("explore", views.explore, name="explore"),  # GET 지도 탐색(KDE 배경+본영화+안전·미탐색 추천) (4.4)
    path("chat", views.chat, name="chat"),  # POST 범용 영화 추천 AI 챗봇 (SSE 스트리밍) (5.4)
]
