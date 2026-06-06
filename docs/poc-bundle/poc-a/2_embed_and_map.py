"""
2_embed_and_map.py

수집한 영화 데이터를 TF-IDF로 임베딩하고 UMAP으로 2D 축소.
결과를 movies_2d.json + scatter plot으로 저장.

핵심 가설:
    - 장르(가중치 3.0), 키워드(가중치 1.0), 감독(가중치 0.5)
    - 가중치는 PoC에서 실험하면서 튜닝

사용법:
    python 2_embed_and_map.py
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import umap
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer

# ---------- 경로 ----------
BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "movies.json"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------- 한글 폰트 자동 설정 ----------
def setup_korean_font():
    """OS별로 사용 가능한 한글 폰트를 자동 탐색."""
    candidates = [
        "AppleGothic",        # macOS
        "Apple SD Gothic Neo",
        "Malgun Gothic",      # Windows
        "NanumGothic",        # Linux (보통 설치 필요)
        "Noto Sans CJK KR",
        "Noto Sans KR",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams["font.family"] = font
            plt.rcParams["axes.unicode_minus"] = False
            print(f"✅ 한글 폰트 설정: {font}")
            return
    print("⚠️  한글 폰트를 찾지 못했습니다. 시각화에서 한글이 깨질 수 있습니다.")
    print("    Linux: sudo apt install fonts-nanum  /  Mac: 기본 폰트 사용 가능")


# ---------- 가중치 (튜닝 포인트) ----------
WEIGHT_GENRES = 3.0      # 장르가 가장 강한 신호
WEIGHT_KEYWORDS = 1.0    # 키워드는 보조
WEIGHT_DIRECTORS = 0.5   # 감독은 약한 신호 (감독별 영화 수 적음)


def tokenize_list(items: list[str]) -> str:
    """리스트 → 공백으로 구분된 토큰 문자열.
    공백 포함 항목은 언더스코어로 묶어서 한 토큰으로 처리.
    예: ['액션', '슈퍼히어로'] → '액션 슈퍼히어로'
    예: ['Christopher Nolan'] → 'Christopher_Nolan'
    """
    return " ".join(item.replace(" ", "_") for item in items)


def build_features(movies: list[dict]):
    """각 영화 → TF-IDF 벡터 (장르 + 키워드 + 감독 concat)."""

    genre_docs = [tokenize_list(m["genres"]) for m in movies]
    keyword_docs = [tokenize_list(m["keywords"]) for m in movies]
    director_docs = [tokenize_list(m["directors"]) for m in movies]

    # 각각 별도 vectorizer → 가중치 적용 후 concat
    vec_genre = TfidfVectorizer(token_pattern=r"[^ ]+")
    vec_keyword = TfidfVectorizer(token_pattern=r"[^ ]+", min_df=2)
    vec_director = TfidfVectorizer(token_pattern=r"[^ ]+")

    X_genre = vec_genre.fit_transform(genre_docs) * WEIGHT_GENRES
    X_keyword = vec_keyword.fit_transform(keyword_docs) * WEIGHT_KEYWORDS
    X_director = vec_director.fit_transform(director_docs) * WEIGHT_DIRECTORS

    print("📐 피처 차원:")
    print(f"  장르:   {X_genre.shape[1]}")
    print(f"  키워드: {X_keyword.shape[1]}")
    print(f"  감독:   {X_director.shape[1]}")

    X = hstack([X_genre, X_keyword, X_director]).tocsr()
    print(f"  전체:   {X.shape}")

    return X, {
        "genre": vec_genre,
        "keyword": vec_keyword,
        "director": vec_director,
    }


def reduce_to_2d(X, n_neighbors: int = 15, min_dist: float = 0.1):
    """UMAP으로 2D 축소.
    
    n_neighbors: 작을수록 지역 구조 강조 (5~50)
    min_dist:    작을수록 클러스터가 빽빽 (0.0~0.99)
    """
    print("\n🗺️  UMAP 2D 축소 중...")
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric="cosine",  # TF-IDF는 cosine이 적합
        random_state=42,
    )
    coords = reducer.fit_transform(X)
    print(f"✅ 2D 좌표 생성 완료: {coords.shape}")
    return coords


def visualize(movies: list[dict], coords: np.ndarray, output_path: Path):
    """장르별 색칠한 scatter plot."""
    fig, ax = plt.subplots(figsize=(14, 10))

    # 대표 장르(첫 번째)별로 색상
    primary_genres = [m["genres"][0] if m["genres"] else "기타" for m in movies]
    unique_genres = sorted(set(primary_genres))
    cmap = plt.get_cmap("tab20")
    color_map = {g: cmap(i % 20) for i, g in enumerate(unique_genres)}

    for genre in unique_genres:
        mask = np.array([g == genre for g in primary_genres])
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            c=[color_map[genre]],
            label=genre,
            alpha=0.7,
            s=40,
            edgecolors="white",
            linewidths=0.5,
        )

    ax.set_title("영화 취향 지도 (TF-IDF + UMAP)", fontsize=16, pad=20)
    ax.set_xlabel("UMAP-1")
    ax.set_ylabel("UMAP-2")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    print(f"✅ 시각화 저장: {output_path}")


def save_coords(movies: list[dict], coords: np.ndarray, output_path: Path):
    """영화 + 2D 좌표를 JSON으로 저장 (다음 단계에서 사용)."""
    result = []
    for m, (x, y) in zip(movies, coords):
        result.append({
            "id": m["id"],
            "title": m["title"],
            "genres": m["genres"],
            "directors": m["directors"],
            "release_year": m["release_year"],
            "vote_average": m["vote_average"],
            "x": float(x),
            "y": float(y),
        })
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ 좌표 데이터 저장: {output_path}")


# ---------- 메인 ----------
def main():
    if not DATA_PATH.exists():
        raise SystemExit(f"❌ {DATA_PATH}가 없습니다. 먼저 1_fetch_movies.py를 실행하세요.")

    setup_korean_font()

    movies = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    print(f"📂 영화 {len(movies)}편 로드\n")

    X, vectorizers = build_features(movies)
    coords = reduce_to_2d(X)

    save_coords(movies, coords, OUTPUT_DIR / "movies_2d.json")
    visualize(movies, coords, OUTPUT_DIR / "taste_map.png")

    print("\n🎉 PoC-A 완료!")
    print(f"\n다음 검토 항목:")
    print(f"  1. {OUTPUT_DIR / 'taste_map.png'}를 열어 시각적으로 확인")
    print(f"  2. 비슷한 장르 영화가 가까이 모였는가?")
    print(f"  3. 분리가 너무 약하거나 강하면 WEIGHT_* 값 조정")
    print(f"  4. 결과가 그럴듯하면 PoC-B로 진행")


if __name__ == "__main__":
    main()
