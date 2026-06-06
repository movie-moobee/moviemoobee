# PoC-A: TMDB 데이터 → 2D 취향 지도

## 🎯 이 PoC가 검증하려는 것

**"TF-IDF + UMAP만으로도 의미 있는 2D 영화 지도가 나오는가?"**

이 질문에 답이 나와야 본 프로젝트의 ③ 기능(2D 취향 지도)을 안전하게 진행할 수 있습니다.

### 합격 기준

- 같은 장르의 영화들이 시각적으로 군집을 이룬다
- 시리즈 영화(예: 어벤져스 1~4)가 가까이 모인다
- 같은 감독의 영화가 가까이 위치한다
- "이 영화 주변엔 어떤 영화가 있나" 검사 시 사람 눈에 그럴듯하다

### 불합격 시 대안

- 가중치 (`WEIGHT_GENRES`, `WEIGHT_KEYWORDS`, `WEIGHT_DIRECTORS`) 튜닝
- 그래도 안 되면 Sentence-BERT로 overview 임베딩 추가 (PoC-A2)

---

## 📦 구성

```
poc-a/
├── .env.example          ← 환경변수 템플릿
├── requirements.txt      ← 의존성
├── 1_fetch_movies.py     ← TMDB에서 영화 N편 수집
├── 2_embed_and_map.py    ← 임베딩 + UMAP + 시각화
├── 3_inspect.py          ← 결과 검증 (이웃 확인)
├── data/
│   └── movies.json       ← 1번 스크립트가 생성
└── output/
    ├── movies_2d.json    ← 영화별 2D 좌표 (PoC-B에서 사용)
    └── taste_map.png     ← 시각화 결과
```

---

## 🚀 실행 순서

### 1. 환경 준비

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 열어서 TMDB_API_KEY 채우기
```

### 2. 영화 데이터 수집 (5~10분)

```bash
python 1_fetch_movies.py
```

기본 300편을 가져옵니다. 더 많이/적게 원하면 `.env`의 `MOVIE_COUNT` 변경.

**출력 예시:**
```
🎬 TMDB에서 영화 300편 수집 시작
✅ 영화 ID 300개 수집 완료
✅ 297편 저장 완료 → data/movies.json
📊 수집 요약:
  - 평균 장르 수: 2.4
  - 평균 키워드 수: 8.7
  ...
```

### 3. 임베딩 + 2D 지도 생성 (수십 초)

```bash
python 2_embed_and_map.py
```

**출력 결과:**
- `output/taste_map.png` — 장르별 색칠한 산점도
- `output/movies_2d.json` — 영화별 좌표 데이터

### 4. 결과 검증 (직접 확인 필수)

먼저 `taste_map.png`를 눈으로 확인하세요. 그 다음:

```bash
# 무작위 5편 샘플 + 각각의 이웃 확인
python 3_inspect.py

# 특정 영화 검색
python 3_inspect.py --title "인터스텔라"
python 3_inspect.py --title "어벤져스"

# 이웃 더 많이 보기
python 3_inspect.py --title "인터스텔라" --top 10
```

**출력 예시:**
```
🎬 인터스텔라 (2014)
   장르: 모험, 드라마, SF
   감독: Christopher Nolan

📍 가까운 영화 Top 5:
  1. 🎬 인셉션 (2010) [거리 0.234]
     장르: 액션, SF, 모험
     감독: Christopher Nolan
  2. 🎬 그래비티 (2013) [거리 0.412]
     ...
```

---

## 🧪 튜닝 가이드

결과가 마음에 안 들면 `2_embed_and_map.py` 상단의 가중치 조정:

```python
WEIGHT_GENRES = 3.0      # ↑ 장르별로 더 강하게 뭉침
WEIGHT_KEYWORDS = 1.0    # ↑ 세부 주제별로 뭉침 (액션 안에서도 슈퍼히어로 vs 첩보)
WEIGHT_DIRECTORS = 0.5   # ↑ 감독별로 더 뭉침 (놀란 영화끼리)
```

UMAP 파라미터:
```python
reduce_to_2d(X, n_neighbors=15, min_dist=0.1)
# n_neighbors ↑ → 전역 구조 강조 (큰 클러스터)
# n_neighbors ↓ → 지역 구조 강조 (작은 그룹들)
# min_dist ↓    → 클러스터가 빽빽
# min_dist ↑    → 점들이 흩어짐
```

### 페어와 함께 할 일

1. `taste_map.png` 같이 보면서 "이 색 분포가 말이 되는가" 토론
2. `3_inspect.py`로 각자 좋아하는 영화 검색해서 이웃 확인
3. **합격이면** → PoC-B로 진행
4. **불합격이면** → 가중치 두 번까지만 튜닝 시도, 그래도 안 되면 Sentence-BERT 추가 검토

---

## ⚠️ 주의 사항

- TMDB API는 무료지만 rate limit 있음. `1_fetch_movies.py`에 보호 로직 들어있음.
- 인기 영화 위주로 가져오기 때문에 데이터가 한쪽으로 쏠림. 본 프로젝트에선 사용자 등록 영화 기반이라 다른 분포가 나올 수 있음.
- 한국어 키워드/장르 사용 (`.env`의 `TMDB_LANGUAGE=ko-KR`). 영어로 바꾸려면 `en-US`.

---

## 📊 다음 단계 (PoC-B 예고)

이 PoC가 통과하면 다음을 검증합니다:
- 사용자가 본 영화 10편의 좌표를 어떻게 평균낼 것인가
- 별점을 가중치로 어떻게 반영할 것인가
- "미탐색 영역"을 어떻게 정의할 것인가 (거리 vs 밀도)
- 추천 결과가 그럴듯한가
