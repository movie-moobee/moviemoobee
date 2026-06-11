from django.urls import path

from . import views

urlpatterns = [
    path("me/coord", views.my_coord, name="my_coord"),  # GET 내 취향 좌표 (F-MAP-00)
]
