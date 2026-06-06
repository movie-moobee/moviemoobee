# PoC-B: 사용자 좌표 + 추천 + 미탐색 영역

## 🎯 이 PoC가 검증하려는 것

PoC-A에서 만든 2D 지도 위에서:

1. **사용자 좌표를 어떻게 계산할 것인가?** (단순 평균 vs 별점 가중 평균)
2. **추천이 실제로 그럴듯한가?** (코사인 유사도)
3. **"미탐색 영역"을 어떻게 정의할 것인가?** (거리/밀도/분산 3가지 비교)
4. **시각화했을 때 사용자에게 이해되는가?**

## 📋 합격 기준

- [ ] 사용자 좌표가 시청 영화 클러스터 중심부에 위치
- [ ] 코사인 추천 Top 10이 사용자 취향 장르 위주로 나옴
- [ ] 미탐색 영역 3가지 중 최소 하나는 "그럴듯한" 분포를 보임
- [ ] 시각화에서 별/원/X가 한눈에 구분됨

## 📦 구성

```
poc-b/
├── requirements.txt
├── 1_create_virtual_user.py    ← 가상 사용자 생성 (취향 명확)
├── 2_recommend.py              ← 좌표 계산 + 추천 + 미탐색 영역
├── 3_visualize.py              ← 결과 시각화
└── output/
    ├── virtual_user.json         ← 가상 사용자 (1번이 생성)
    ├── recommendations.json      ← 추천 결과 (2번이 생성)
    ├── unexplored_comparison.png ← 미탐색 3가지 비교
    └── final_recommendation.png  ← 최종 추천 시각화
```

## ⚠️ 사전 준비

PoC-A가 먼저 실행되어 있어야 합니다. (`poc-a/output/movies_2d.json` 필요)

## 🚀 실행 순서

### 1. 의존성 설치 (PoC-A 가상환경 재사용 가능)

```bash
pip install -r requirements.txt
```

### 2. 가상 사용자 생성

```bash
# 기본: SF + 액션 위주
python 1_create_virtual_user.py

# 다른 취향으로 테스트
python 1_create_virtual_user.py --primary-genre "공포" --secondary-genre "스릴러"
python 1_create_virtual_user.py --primary-genre "로맨스"
```

### 3. 추천 + 미탐색 영역 계산

```bash
python 2_recommend.py
```

콘솔에 추천 Top 10, 미탐색 영역 3가지 비교 결과가 출력됩니다.

### 4. 시각화

```bash
python 3_visualize.py
```

**출력 파일 2개:**
- `final_recommendation.png` — 한눈에 보는 최종 추천 결과
- `unexplored_comparison.png` — 미탐색 영역 3가지 비교

## 🔍 결과 해석 가이드

### `final_recommendation.png`

**확인할 것:**
- ⭐ 빨강 별(시청 영화)이 한두 클러스터에 모여 있는가? → 취향 명확 사용자라면 그래야 함
- 📍 자홍 X(사용자 좌표)가 별들의 중심에 있는가? → 좌표 계산이 합리적
- 🟦 파랑 원(코사인 추천)이 별 근처에 있는가? → 안전 추천이 작동
- 🟧 주황 원(도전 추천)이 별과 적당히 떨어져 있는가? → 미탐색 추천이 작동

**문제 사례:**
- ❌ 별과 사용자 좌표가 멀리 떨어짐 → 별점 가중치 로직 재검토
- ❌ 파랑 원이 사방에 흩어짐 → 코사인 유사도 부적합 (방향이 무의미한 좌표계)
- ❌ 주황 원이 너무 멀어서 다른 행성처럼 보임 → 너무 이질적, 임계값 조정

### `unexplored_comparison.png`

세 가지 미탐색 정의를 비교합니다. **본 프로젝트에서 어느 걸 쓸지 결정하는 게 PoC-B의 핵심 산출물**입니다.

| 방법 | 특징 | 권장 상황 |
|---|---|---|
| **거리 기반** | 단순, 빠름 | 취향 명확 사용자 |
| **밀도 기반 (KDE)** | 정확, 약간 무거움 | 일반 사용자 (기본 권장) |
| **분산 기반** | 통계적, 분포에 민감 | 시청 영화 많은 사용자 |

대부분의 경우 **밀도 기반(KDE)이 가장 합리적**입니다. 페어와 함께 보고 합의하세요.

## 🧪 다양한 시나리오 테스트

```bash
# 시나리오 1: SF 마니아
python 1_create_virtual_user.py --primary-genre "SF" --seed 1
python 2_recommend.py && python 3_visualize.py

# 시나리오 2: 공포 + 스릴러
python 1_create_virtual_user.py --primary-genre "공포" --secondary-genre "스릴러" --seed 2
python 2_recommend.py && python 3_visualize.py

# 시나리오 3: 다른 시드 (다른 영화 선택됨)
python 1_create_virtual_user.py --seed 99
```

각 시나리오에서 추천이 일관되게 그럴듯하면 합격.

## 📊 본 프로젝트로 가져갈 결정

PoC-B가 끝나면 아래 결정이 명확해져 있어야 합니다.

- [ ] 사용자 좌표 = **별점 가중 평균** (PoC-B에서 검증됨)
- [ ] 추천 알고리즘 = **코사인 유사도** (또는 거리 기반과의 비교 결과)
- [ ] 미탐색 영역 정의 = **밀도(KDE) 기반** (또는 페어 합의 결과)
- [ ] 추천 분기 = **안전 추천(클러스터 내)** + **도전 추천(미탐색)** 두 트랙으로 제공

이 결정들이 본 프로젝트의 `services/recommendation.py`에 그대로 반영됩니다.

## 🔧 본 프로젝트 적용 시 추가 고려사항

PoC를 끝내고 본 프로젝트로 갈 때 신경 쓸 것:

1. **새 영화가 추가될 때 좌표 재계산** — 매번 전체 UMAP 다시 돌리면 안 됨 → `umap.transform()` 사용 (이미 학습된 reducer에 새 점만 투영)
2. **사용자 좌표 캐싱** — 별점 등록 시점에만 재계산, DB에 저장
3. **밀도 추정의 비용** — 사용자가 수천 명이 되면 매번 KDE 학습은 부담 → 시청 영화 좌표만 캐싱하고 추천 요청 시 계산
4. **콜드 스타트** — 영화 3편 미만으로는 좌표가 불안정 → 5편 이상 시청 후 지도 활성화 같은 정책 필요
