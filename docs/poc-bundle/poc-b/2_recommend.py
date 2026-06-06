"""
2_recommend.py

PoC-B의 핵심 로직 검증:
    1. 사용자 좌표 계산 (단순 평균 vs 별점 가중 평균 비교)
    2. 코사인 유사도 기반 영화 추천
    3. 미탐색 영역 정의 3가지 비교 (거리/밀도/분산)

생성 결과:
    output/recommendations.json — 추천 결과
    output/unexplored_zones.json — 미탐색 영역 좌표

사용법:
    python 2_recommend.py
"""

import json
from pathlib import Path

import numpy as np
from scipy.stats import gaussian_kde
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).parent
POC_A_OUTPUT = BASE_DIR.parent / "poc-a" / "output" / "movies_2d.json"
USER_PATH = BASE_DIR / "output" / "virtual_user.json"
OUTPUT_DIR = BASE_DIR / "output"


# ============================================================
# 1. 사용자 좌표 계산
# ============================================================

def compute_user_centroid_simple(watched: list[dict]) -> np.ndarray:
    """단순 평균: 모든 시청 영화의 좌표 평균.
    
    문제점:
    - 1점 준 영화도 동일하게 반영됨 → 사용자가 싫어한 영역으로 좌표가 끌려감
    """
    coords = np.array([[w["x"], w["y"]] for w in watched])
    return coords.mean(axis=0)


def compute_user_centroid_weighted(
    watched: list[dict],
    neutral_rating: float = 3.0,
) -> np.ndarray:
    """별점 가중 평균: 별점 - 중립값으로 가중치 부여.
    
    핵심 아이디어:
    - 4점, 5점 영화 → 양의 가중치 (그쪽으로 끌림)
    - 3점 영화 → 가중치 0 (영향 없음)
    - 1점, 2점 영화 → 음의 가중치 (반대쪽으로 밀려남)
    
    이게 진짜 "내가 좋아하는 좌표"에 가깝습니다.
    """
    coords = np.array([[w["x"], w["y"]] for w in watched])
    ratings = np.array([w["rating"] for w in watched])

    weights = ratings - neutral_rating  # -1.5 ~ +2.0
    
    # 가중치 합이 0이면 단순 평균으로 fallback
    if abs(weights.sum()) < 0.01:
        return coords.mean(axis=0)

    # 음수 가중치를 어떻게 처리할지: 두 가지 방법
    # 방법 A: 그대로 사용 (싫어하는 영화의 반대쪽으로 좌표 이동)
    # 방법 B: 양수만 사용 (좋아하는 영화만 반영)
    
    # PoC-B에서는 방법 A 채택. 검증 후 결정.
    return np.average(coords, axis=0, weights=weights)


# ============================================================
# 2. 코사인 유사도 기반 추천
# ============================================================

def recommend_by_cosine(
    user_coord: np.ndarray,
    all_movies: list[dict],
    watched_ids: set[int],
    top_n: int = 10,
) -> list[dict]:
    """사용자 좌표와 코사인 유사도가 높은 미관람 영화 추천.
    
    주의: 코사인 유사도는 방향만 본다(크기 무시).
    원점 근처는 의미가 달라지므로 좌표를 원점에서 평행이동하는 게 좋지만,
    UMAP 좌표는 이미 적절히 퍼져있어 그대로 사용.
    """
    movie_coords = np.array([[m["x"], m["y"]] for m in all_movies])
    
    # 사용자 좌표와의 코사인 유사도
    sims = cosine_similarity(user_coord.reshape(1, -1), movie_coords)[0]
    
    # 미관람 영화만 추리고 유사도 순 정렬
    candidates = []
    for i, m in enumerate(all_movies):
        if m["id"] not in watched_ids:
            candidates.append({
                "movie_id": m["id"],
                "title": m["title"],
                "genres": m["genres"],
                "x": m["x"],
                "y": m["y"],
                "similarity": float(sims[i]),
                "distance": float(np.linalg.norm(movie_coords[i] - user_coord)),
            })

    candidates.sort(key=lambda c: -c["similarity"])
    return candidates[:top_n]


def recommend_by_distance(
    user_coord: np.ndarray,
    all_movies: list[dict],
    watched_ids: set[int],
    top_n: int = 10,
) -> list[dict]:
    """비교용: 유클리드 거리 기반 추천 (가까운 순)."""
    movie_coords = np.array([[m["x"], m["y"]] for m in all_movies])
    dists = np.linalg.norm(movie_coords - user_coord, axis=1)

    candidates = []
    for i, m in enumerate(all_movies):
        if m["id"] not in watched_ids:
            candidates.append({
                "movie_id": m["id"],
                "title": m["title"],
                "genres": m["genres"],
                "x": m["x"],
                "y": m["y"],
                "distance": float(dists[i]),
            })

    candidates.sort(key=lambda c: c["distance"])
    return candidates[:top_n]


# ============================================================
# 3. 미탐색 영역 정의 3가지
# ============================================================

def detect_unexplored_by_distance(
    user_coord: np.ndarray,
    all_movies: list[dict],
    watched_ids: set[int],
    percentile: int = 80,
) -> dict:
    """방법 1: 사용자 좌표에서 거리 기반.
    
    상위 percentile% 이상 멀리 떨어진 영화 = 미탐색.
    
    장점: 단순, 직관적
    단점: 사용자 좌표 하나에 의존 → 잡식 사용자는 영원히 미탐색이 없음
    """
    movie_coords = np.array([[m["x"], m["y"]] for m in all_movies])
    dists = np.linalg.norm(movie_coords - user_coord, axis=1)
    threshold = np.percentile(dists, percentile)
    
    unexplored = []
    for i, m in enumerate(all_movies):
        if m["id"] not in watched_ids and dists[i] >= threshold:
            unexplored.append({**m, "distance": float(dists[i])})

    return {
        "method": "distance",
        "threshold": float(threshold),
        "count": len(unexplored),
        "movies": unexplored,
    }


def detect_unexplored_by_density(
    watched_coords: np.ndarray,
    all_movies: list[dict],
    watched_ids: set[int],
    percentile: int = 20,
) -> dict:
    """방법 2: 사용자 시청 영화의 KDE(밀도) 기반.
    
    사용자 영화 밀도가 하위 percentile% 인 영역 = 미탐색.
    
    장점: 잡식 사용자도 작동, "내가 안 본 영역"을 정확히 짚음
    단점: 시청 영화 수가 적으면 KDE가 불안정
    """
    movie_coords = np.array([[m["x"], m["y"]] for m in all_movies])

    # 사용자 시청 영화 좌표로 KDE 학습
    kde = gaussian_kde(watched_coords.T, bw_method=0.3)
    densities = kde(movie_coords.T)
    
    threshold = np.percentile(densities, percentile)
    
    unexplored = []
    for i, m in enumerate(all_movies):
        if m["id"] not in watched_ids and densities[i] <= threshold:
            unexplored.append({**m, "density": float(densities[i])})

    return {
        "method": "density",
        "threshold": float(threshold),
        "count": len(unexplored),
        "movies": unexplored,
    }


def detect_unexplored_by_variance(
    watched_coords: np.ndarray,
    all_movies: list[dict],
    watched_ids: set[int],
    sigma_threshold: float = 1.5,
) -> dict:
    """방법 3: 사용자 영화의 분산 범위 밖.
    
    사용자 영화들의 평균에서 sigma_threshold * std 이상 떨어진 영역 = 미탐색.
    
    장점: 통계적으로 명확
    단점: 분포가 비대칭일 때 부정확
    """
    mean = watched_coords.mean(axis=0)
    std = watched_coords.std(axis=0)
    threshold_dist = sigma_threshold * np.linalg.norm(std)

    movie_coords = np.array([[m["x"], m["y"]] for m in all_movies])
    dists = np.linalg.norm(movie_coords - mean, axis=1)
    
    unexplored = []
    for i, m in enumerate(all_movies):
        if m["id"] not in watched_ids and dists[i] >= threshold_dist:
            unexplored.append({**m, "distance_from_mean": float(dists[i])})

    return {
        "method": "variance",
        "threshold": float(threshold_dist),
        "count": len(unexplored),
        "movies": unexplored,
    }


# ============================================================
# 4. 미탐색 영역 추천 (보너스)
# ============================================================

def recommend_from_unexplored(
    user_coord: np.ndarray,
    unexplored_movies: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """미탐색 영역 중에서도 사용자 좌표와 '적당히' 떨어진 영화 추천.
    
    너무 가까우면 미탐색이 아니고, 너무 멀면 너무 이질적.
    "도전적이지만 시도해볼 만한" 영역을 골라야 함.
    """
    if not unexplored_movies:
        return []

    # 사용자 좌표 기준 거리의 중앙값 근처 영화 추천
    coords = np.array([[m["x"], m["y"]] for m in unexplored_movies])
    dists = np.linalg.norm(coords - user_coord, axis=1)
    
    # 거리 기준 정렬 후 30~70 퍼센타일 영역에서 추천
    sorted_indices = np.argsort(dists)
    lower = int(len(sorted_indices) * 0.3)
    upper = int(len(sorted_indices) * 0.7)
    
    candidates = []
    for i in sorted_indices[lower:upper]:
        m = unexplored_movies[i]
        candidates.append({
            "movie_id": m["id"],
            "title": m["title"],
            "genres": m["genres"],
            "x": m["x"],
            "y": m["y"],
            "distance": float(dists[i]),
        })
    return candidates[:top_n]


# ============================================================
# 메인
# ============================================================

def print_recommendations(recs: list[dict], title: str):
    print(f"\n📌 {title}")
    print("-" * 60)
    for i, r in enumerate(recs, 1):
        genres = ", ".join(r["genres"][:3])
        sim_str = f"sim={r['similarity']:.3f}" if "similarity" in r else f"dist={r['distance']:.3f}"
        print(f"  {i:2}. {r['title'][:30]:30} [{genres}] ({sim_str})")


def main():
    if not POC_A_OUTPUT.exists():
        raise SystemExit(f"❌ {POC_A_OUTPUT}가 없습니다.")
    if not USER_PATH.exists():
        raise SystemExit(f"❌ {USER_PATH}가 없습니다. 1_create_virtual_user.py 먼저 실행.")

    all_movies = json.loads(POC_A_OUTPUT.read_text(encoding="utf-8"))
    user = json.loads(USER_PATH.read_text(encoding="utf-8"))
    watched = user["watched"]
    watched_ids = {w["movie_id"] for w in watched}
    watched_coords = np.array([[w["x"], w["y"]] for w in watched])

    print(f"📂 영화 {len(all_movies)}편, 사용자 시청 {len(watched)}편\n")
    print(f"👤 사용자 취향: {user['profile']['primary_genre']} + {user['profile'].get('secondary_genre', '없음')}")

    # ============ 1. 사용자 좌표 계산 비교 ============
    print("\n" + "=" * 60)
    print("📍 사용자 좌표 계산")
    print("=" * 60)

    centroid_simple = compute_user_centroid_simple(watched)
    centroid_weighted = compute_user_centroid_weighted(watched)

    print(f"\n  단순 평균:     ({centroid_simple[0]:.3f}, {centroid_simple[1]:.3f})")
    print(f"  별점 가중 평균: ({centroid_weighted[0]:.3f}, {centroid_weighted[1]:.3f})")
    print(f"  → 두 좌표의 거리: {np.linalg.norm(centroid_simple - centroid_weighted):.3f}")
    print(f"  → 거리가 클수록 별점이 좌표에 영향을 많이 줬다는 뜻")

    # 별점 가중 평균을 메인 좌표로 사용
    user_coord = centroid_weighted

    # ============ 2. 추천 비교 ============
    print("\n" + "=" * 60)
    print("🎬 추천 결과")
    print("=" * 60)

    recs_cosine = recommend_by_cosine(user_coord, all_movies, watched_ids, top_n=10)
    recs_distance = recommend_by_distance(user_coord, all_movies, watched_ids, top_n=10)

    print_recommendations(recs_cosine, "코사인 유사도 기반 Top 10")
    print_recommendations(recs_distance, "유클리드 거리 기반 Top 10 (비교용)")

    # ============ 3. 미탐색 영역 3가지 비교 ============
    print("\n" + "=" * 60)
    print("🗺️  미탐색 영역 감지")
    print("=" * 60)

    zone_dist = detect_unexplored_by_distance(user_coord, all_movies, watched_ids)
    zone_dens = detect_unexplored_by_density(watched_coords, all_movies, watched_ids)
    zone_var = detect_unexplored_by_variance(watched_coords, all_movies, watched_ids)

    print(f"\n  거리 기반 (사용자 좌표에서 먼 80% 영역)")
    print(f"     → 미탐색 영화: {zone_dist['count']}편")
    print(f"\n  밀도 기반 (사용자 영화 밀도 하위 20% 영역)")
    print(f"     → 미탐색 영화: {zone_dens['count']}편")
    print(f"\n  분산 기반 (사용자 영화 평균에서 1.5σ 밖)")
    print(f"     → 미탐색 영화: {zone_var['count']}편")

    # 미탐색 영역에서의 추천
    print("\n  💡 밀도 기반 미탐색에서 추천 (적당히 떨어진 영화):")
    unexplored_recs = recommend_from_unexplored(user_coord, zone_dens["movies"], top_n=5)
    for r in unexplored_recs:
        genres = ", ".join(r["genres"][:3])
        print(f"     - {r['title'][:30]:30} [{genres}]")

    # ============ 저장 ============
    result = {
        "user_coordinate": {
            "simple": centroid_simple.tolist(),
            "weighted": centroid_weighted.tolist(),
        },
        "recommendations": {
            "cosine": recs_cosine,
            "distance": recs_distance,
            "from_unexplored": unexplored_recs,
        },
        "unexplored_zones": {
            "distance": zone_dist,
            "density": zone_dens,
            "variance": zone_var,
        },
    }
    output_path = OUTPUT_DIR / "recommendations.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 결과 저장: {output_path}")
    print(f"\n다음 단계: python 3_visualize.py")


if __name__ == "__main__":
    main()
