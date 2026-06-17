"""전체 영화 → TF-IDF(장르+키워드+감독) → UMAP 2D 좌표 생성·적재 (김호준 담당, 0.5 파이프라인 후반부).

PoC-A(2_embed_and_map.py) 로직을 DB 적재로 이식.
- 좌표(umap_x/umap_y)는 전 사용자 공통·전역 고정값(CLAUDE.md 불변식).
- 여기서 한 번만 fit 하고, 학습된 벡터라이저+UMAP을 .pkl로 저장한다.
  신규 영화는 이 모델로 transform 만 해야 한다(재학습 금지 — 다시 fit하면 모두의 좌표가 바뀜).
"""
import pickle
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError       # -> 이걸로 python manage.py build_coords 할 수 있다 개신기.

from movies.models import Movie         # 좌표 업데이트는 ? movies의 모델 Movie

# 가중치 (PoC-A 튜닝값), 영 이상하면 여기서 수정
WEIGHT_GENRES = 3.0
WEIGHT_KEYWORDS = 1.0
WEIGHT_DIRECTORS = 0.5

# 학습된 모델 저장 경로 (taste/artifacts/coords_model.pkl). *.pkl 은 gitignore 됨.  .pkl : 피클 파일 확장자. 남이 만든 피클 파일은 함부로 열지말자.(임의로 파이썬 코드 실행해서 해킹해버릴수도 ㄷㄷ)
MODEL_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "coords_model.pkl"     # pkl은 학습 완료된거 저장해주는 역할 (바이너리 형태) / resolve().parents[2]는 상위 2단계 디렉토리를 말함 (=taste 여기선)


def _tokenize(items):
    """리스트 → 공백 구분 토큰 문자열. 공백 포함 항목은 언더스코어로 한 토큰 처리."""
    return " ".join(item.replace(" ", "_") for item in items if item)
    # 공백으로 있는 단어 -> _로 이음 -> 그리고 각 단어들을 다시 공백으로 구분짓기

class Command(BaseCommand):
    help = "TF-IDF(장르+키워드+감독) → UMAP 좌표 생성 → movies.umap_x/y 적재 (당연하게도 '프로그래밍계의 김정호' 김호준이 작성)"    # backend폴더에서 python manage.py help coords.py를 하면 볼 수 있다.
    
    # python manage.py buld_coords.py 의 진입점
    def handle(self, *args, **opts):
        # 무거운 ML 의존성은 커맨드 실행 시점에만 import (웹 부팅엔 불필요) ★
        import umap
        from scipy.sparse import hstack
        from sklearn.feature_extraction.text import TfidfVectorizer

        movies = list(
            Movie.objects.prefetch_related("genres", "keywords").order_by("id")     # 화와 다대다(M2M) 관계인 장르와 키워드를 한 번의 쿼리로 미리 가져와사 N+1 Problem 방지 및 속도 향상 기대.
        )
        if not movies:
            raise CommandError("영화가 없습니다. 먼저 import_movies 를 실행하세요.")
        self.stdout.write(f"[좌표] 영화 {len(movies)}편 로드")

        genre_docs = [_tokenize([g.name for g in m.genres.all()]) for m in movies]  # ex ['액션 코미디', '멜로 로맨스', ...] -> ['액션_코미디', '멜로_로맨스', ...]
        keyword_docs = [_tokenize([k.name for k in m.keywords.all()]) for m in movies]
        director_docs = [_tokenize([m.director]) for m in movies]

        # Scikit-learn의 기본 토크나이저는 글자 수가 적거나 특수문자가 있으면 단어를 무시할수도?
        vec_genre = TfidfVectorizer(token_pattern=r"[^ ]+")                 # 정규식 [^ ]+ 을 통해 공백이 아닌 모든 문자열 덩어리 통째로 하나의 토큰(단어)으로 인식하게 강제
        vec_keyword = TfidfVectorizer(token_pattern=r"[^ ]+", min_df=2)     # 최소 2편 이상 등장한 키워드만 피처로 채택, 전체 영화 중 단 1편에만 등장하는 키워드는 노이즈
        vec_director = TfidfVectorizer(token_pattern=r"[^ ]+")

        x_genre = vec_genre.fit_transform(genre_docs) * WEIGHT_GENRES           # fit__transform: 텍스트 데이터를 기반으로 단어 사전을 만들고(fit), 각 문서의 단어 빈도 점수(TF-IDF) 행렬을 생성(transform)
        x_keyword = vec_keyword.fit_transform(keyword_docs) * WEIGHT_KEYWORDS
        x_director = vec_director.fit_transform(director_docs) * WEIGHT_DIRECTORS
        x = hstack([x_genre, x_keyword, x_director]).tocsr()
        self.stdout.write(
            f"[좌표] 피처 차원 genre={x_genre.shape[1]} "
            f"keyword={x_keyword.shape[1]} director={x_director.shape[1]} "
            f"total={x.shape[1]}"
        )

        reducer = umap.UMAP(
            n_components=2,         # 2차원
            n_neighbors=15,
            min_dist=0.1,
            metric="cosine",        # 코사인 유사도 기반으로 영화 유사도 판단
            random_state=42,        # UMAP은 확률적 요소를 사용하므로 실행할 때마다 결과 좌표가 조금씩 바뀔 수도. 이를 고정하여 언제 실행해도 완전히 동일한 좌표가 나오도록 제어
        )
        coords = reducer.fit_transform(x)       # 고차원 데이터를 바탕으로 공간 구조를 학습, 최종 2차원 좌표 데이터(coords)를 반환
        self.stdout.write(f"[좌표] UMAP 2D 생성 완료 {coords.shape}")

        
        # DB 반영
        for m, (cx, cy) in zip(movies, coords):
            m.umap_x = float(cx)
            m.umap_y = float(cy)                # 영화 객체의 필드(umap_x, umap_y)에 대입
        Movie.objects.bulk_update(movies, ["umap_x", "umap_y"], batch_size=500)         # bulk_update를 통해 지정한 필드(umap_x/y)만 500개 단위(batch_size=500)로 묶어서 한 번에 업데이트

        # 좌표가 바뀌었으니 추천 서비스의 메모리 좌표 캐시 무효화(같은 프로세스에서 돌 경우 대비).
        from taste.services.areas import clear_movies_cache
        clear_movies_cache()

        
        # 모델 직렬화
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)        # artifacts 폴더 있나 없나 체크 없으면 생성
        with open(MODEL_PATH, "wb") as f:                           # 파일을 쓰기 전용 바이너리 모드(wb)로 엶
            pickle.dump(                                            # .pkl 파일 굽기
                {
                    "vec_genre": vec_genre,
                    "vec_keyword": vec_keyword,
                    "vec_director": vec_director,
                    "reducer": reducer,
                    "weights": (WEIGHT_GENRES, WEIGHT_KEYWORDS, WEIGHT_DIRECTORS),
                },
                f,
            )

        self.stdout.write(self.style.SUCCESS(
            f"[완료] {len(movies)}편 좌표 적재 + 모델 저장 → {MODEL_PATH}"
        ))  # 이 파일이 남아있기 때문에, 추후 새로 추가되는 영화는 새로 fit할 필요 없이 이 파일만 load해서 transform() 메서드만 호출하면 기존 좌표계의 깨짐 없이 고정된 위치에 안착

