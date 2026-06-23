from django.db import migrations


class Migration(migrations.Migration):
    """영화 좌표 필드 umap_x/umap_y → map_x/map_y 이름 변경 (A-15 후속).
    좌표 엔진은 A-14에서 UMAP → 앵커 대륙 지도로 교체됨 → 이름의 'umap' 잔재 제거.
    RenameField라 데이터·컬럼 값은 그대로 보존(재bake 불필요)."""

    dependencies = [
        ("movies", "0003_movie_trailer_key"),
    ]

    operations = [
        migrations.RenameField(model_name="movie", old_name="umap_x", new_name="map_x"),
        migrations.RenameField(model_name="movie", old_name="umap_y", new_name="map_y"),
    ]
