from django.urls import path

from . import views

urlpatterns = [
    path("me/coord", views.my_coord, name="my_coord"),  # GET 내 취향 좌표 (F-MAP-00)
    path("recommendations", views.recommendations, name="recommendations"),  # GET 안전·미탐색 추천 (F-REC, 4.1/4.2)
]
