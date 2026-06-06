from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "TF-IDF(장르+키워드) → UMAP 좌표 생성 → movies.umap_x/y 적재 (개발자 A)"
    def handle(self, *args, **opts):
        # TODO: 전체 영화 fit_transform 후 좌표 저장. 신규 영화는 transform 만(재학습 금지).
        self.stdout.write("TODO: build_coords")
