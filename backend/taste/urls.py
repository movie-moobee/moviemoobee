from django.urls import path

from . import views

urlpatterns = [
    path("me/map", views.taste_map, name="taste_map"),  # GET 취향 지도(본 영화 마커·밝기) (F-MAP-01)
    path("recommendations", views.recommendations, name="recommendations"),  # GET 안전·미탐색 추천 (F-REC, 4.1/4.2)
]
