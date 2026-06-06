from django.contrib import admin
from .models import Movie, Genre, Keyword, WatchRecord
admin.site.register([Movie, Genre, Keyword, WatchRecord])
