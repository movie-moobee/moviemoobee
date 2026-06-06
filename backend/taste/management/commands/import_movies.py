from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "TMDB에서 영화 수집 → movies 적재 (개발자 A)"
    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=2000)
    def handle(self, *args, **opts):
        # TODO: TMDB 호출 → Movie/Genre/Keyword 저장
        self.stdout.write("TODO: import_movies")
