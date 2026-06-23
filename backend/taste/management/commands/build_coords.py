"""전체 영화 → 앵커(장르 대륙) + 키워드 미시분산 → 2D 좌표 생성·적재 (김호준 담당).

좌표 재설계 배경·실측은 docs/08_journal/A-14-anchor-map-coords.md.
- 좌표(umap_x/umap_y, 필드명은 역사적 이름 유지)는 전 사용자 공통·전역 고정값(CLAUDE.md 불변식).
- "가까우면 비슷"이 성립하도록 장르 대륙을 고정 배치(거시) + 같은 대륙 안은 키워드로 분산(미시).
- 여기서 한 번만 fit 하고, 학습된 벡터라이저·앵커·MDS·SVD를 .pkl로 저장한다.
  신규 영화는 이 모델로 transform 만 해야 한다(재학습 금지 — 다시 fit하면 모두의 좌표가 바뀜).

레시피(확정, A-14):
  거시 X_macro = TFIDF(장르×3 + 키워드×1 + 감독×0.5), L2정규화
    앵커 = 주요장르(영화 ≥ MIN_GENRE_MOVIES)의 X_macro 중심벡터
    앵커 2D = MDS(앵커 코사인거리) → ±ANCHOR_SCALE
    P_macro = Σ softmax(cos(영화,앵커)/SOFTMAX_T) · 앵커2D
  미시 X_kw = TFIDF(키워드 only), L2정규화 → SVD 2D → 표준화 → P_kw
  최종 = P_macro + ALPHA · P_kw
"""
import json
import pickle
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from movies.models import Genre, Movie

# 고차원 피처 가중치 (거시 공간)
WEIGHT_GENRES = 3.0
WEIGHT_KEYWORDS = 1.0
WEIGHT_DIRECTORS = 0.5

# 앵커 지도 손잡이 (A-14)
MIN_GENRE_MOVIES = 80   # 이 편수 이상인 장르만 '대륙(앵커)'으로 — 군소 장르 노이즈 제외
SOFTMAX_T = 0.1         # 무게중심 날카로움(작을수록 자기 대륙에 더 딱)
ANCHOR_SCALE = 10.0     # 앵커 2D 좌표 스케일(±)
ALPHA = 0.5             # ★ 미시(키워드) 오프셋 크기 — 튜닝 손잡이. ↑면 분리↑(과하면 대륙 이탈).
                        #   변경 시 build_coords 재실행으로 전 좌표 재bake 필요.

# 학습된 모델 저장 경로 (taste/artifacts/coords_model.pkl). *.pkl 은 gitignore 됨.
MODEL_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "coords_model.pkl"
# 앵커(대륙) 위치 — 프론트 지도 라벨/배경용. pkl과 달리 커밋되어 ML스택 없이도 지도가 대륙을 그림.
ANCHORS_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "anchors.json"


def _tokenize(items):
    """리스트 → 공백 구분 토큰 문자열. 공백 포함 항목은 언더스코어로 한 토큰 처리."""
    return " ".join(item.replace(" ", "_") for item in items if item)


class Command(BaseCommand):
    help = "앵커(장르대륙)+키워드 미시분산 → movies.umap_x/y 좌표 생성·적재 (김호준)"

    def handle(self, *args, **opts):
        # 무거운 ML 의존성은 커맨드 실행 시점에만 import (웹 부팅엔 불필요) ★
        import numpy as np
        from scipy.sparse import hstack
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.manifold import MDS
        from sklearn.metrics.pairwise import cosine_distances
        from sklearn.preprocessing import normalize

        movies = list(Movie.objects.prefetch_related("genres", "keywords").order_by("id"))
        if not movies:
            raise CommandError("영화가 없습니다. 먼저 import_movies 를 실행하세요.")
        self.stdout.write(f"[좌표] 영화 {len(movies)}편 로드")

        genre_docs = [_tokenize([g.name for g in m.genres.all()]) for m in movies]
        keyword_docs = [_tokenize([k.name for k in m.keywords.all()]) for m in movies]
        director_docs = [_tokenize([m.director]) for m in movies]

        vec_genre = TfidfVectorizer(token_pattern=r"[^ ]+")
        vec_keyword = TfidfVectorizer(token_pattern=r"[^ ]+", min_df=2)
        vec_director = TfidfVectorizer(token_pattern=r"[^ ]+")

        # 거시 공간: 장르 가중↑ (대륙을 장르가 좌우하도록)
        x_macro = normalize(hstack([
            vec_genre.fit_transform(genre_docs) * WEIGHT_GENRES,
            vec_keyword.fit_transform(keyword_docs) * WEIGHT_KEYWORDS,
            vec_director.fit_transform(director_docs) * WEIGHT_DIRECTORS,
        ]).tocsr())

        # 앵커: 주요 장르의 거시 중심벡터
        mids = [m.id for m in movies]
        mid_pos = {mid: i for i, mid in enumerate(mids)}
        movie_genres = {m.id: [g.name for g in m.genres.all()] for m in movies}
        anchor_names, anchor_vecs = [], []
        for gname in Genre.objects.values_list("name", flat=True):
            members = [mid_pos[m.id] for m in movies if gname in movie_genres[m.id]]
            if len(members) >= MIN_GENRE_MOVIES:
                anchor_names.append(gname)
                anchor_vecs.append(np.asarray(x_macro[members].mean(axis=0)).ravel())
        anchor_vecs = normalize(np.array(anchor_vecs))
        self.stdout.write(f"[좌표] 대륙(앵커) {len(anchor_names)}개: {anchor_names}")

        # 앵커 2D 배치: 앵커끼리 코사인거리로 MDS → 장르끼리 인접
        anchor_pos = MDS(n_components=2, dissimilarity="precomputed", random_state=42,
                         normalized_stress="auto").fit_transform(cosine_distances(anchor_vecs))
        anchor_pos = anchor_pos / np.abs(anchor_pos).max() * ANCHOR_SCALE

        # 거시 좌표: softmax 가중 무게중심
        sim = np.asarray(x_macro @ anchor_vecs.T)          # (N, G) 코사인 유사도
        w = np.exp(sim / SOFTMAX_T); w = w / w.sum(axis=1, keepdims=True)
        p_macro = w @ anchor_pos                            # (N, 2)

        # 미시 좌표: 키워드 전용 → SVD 2D → 표준화
        x_kw = normalize(vec_keyword.transform(keyword_docs).tocsr())
        svd = TruncatedSVD(n_components=2, random_state=42)
        p_kw = svd.fit_transform(x_kw)
        kw_mean, kw_std = p_kw.mean(axis=0), p_kw.std(axis=0) + 1e-9
        p_kw = (p_kw - kw_mean) / kw_std

        coords = p_macro + ALPHA * p_kw
        self.stdout.write(f"[좌표] 앵커 지도 생성 완료 {coords.shape} (ALPHA={ALPHA})")

        # DB 반영
        for m, (cx, cy) in zip(movies, coords):
            m.umap_x, m.umap_y = float(cx), float(cy)
        Movie.objects.bulk_update(movies, ["umap_x", "umap_y"], batch_size=500)

        # 좌표가 바뀌었으니 추천 서비스의 메모리 좌표 캐시 무효화.
        from taste.services.areas import clear_movies_cache
        clear_movies_cache()

        # 앵커(대륙) 위치를 커밋되는 JSON으로도 저장 — 프론트 지도가 대륙 라벨/배경을 그린다.
        ANCHORS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ANCHORS_PATH, "w", encoding="utf-8") as f:
            json.dump([{"name": n, "x": float(p[0]), "y": float(p[1])}
                       for n, p in zip(anchor_names, anchor_pos)], f, ensure_ascii=False, indent=2)

        # 모델 직렬화 (신규 영화 transform용 — 재fit 금지)
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump({
                "vec_genre": vec_genre, "vec_keyword": vec_keyword, "vec_director": vec_director,
                "weights": (WEIGHT_GENRES, WEIGHT_KEYWORDS, WEIGHT_DIRECTORS),
                "anchor_names": anchor_names, "anchor_vecs": anchor_vecs, "anchor_pos": anchor_pos,
                "svd": svd, "kw_mean": kw_mean, "kw_std": kw_std,
                "softmax_t": SOFTMAX_T, "alpha": ALPHA,
            }, f)

        self.stdout.write(self.style.SUCCESS(
            f"[완료] {len(movies)}편 앵커 좌표 적재 + 모델 저장 → {MODEL_PATH}"))
