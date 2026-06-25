from django.contrib import admin
from .models import Movie, Genre, Keyword, WatchRecord


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    autocomplete_fields = ("genres", "keywords")   # 14,472개 통째 로딩 방지 → 검색 박스
    search_fields = ["title", "original_title"]


@admin.register(WatchRecord)
class WatchRecordAdmin(admin.ModelAdmin):
    autocomplete_fields = ("movie",)   # 영화 FK 3,744개 통째 로딩 방지 → 검색 박스
