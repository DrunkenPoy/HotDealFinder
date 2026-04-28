# HotDealFinder — CLAUDE.md

## 프로젝트 개요

개드립(dogdrip.net/hotdeal) 핫딜 게시글을 실시간으로 크롤링하여,
쇼핑몰 형태의 UI로 핫딜 품목·가격·구매 사이트를 한눈에 보여주는 정적 사이트.
배포: **GitHub Pages (github.io)**

---

## 아키텍처

### 전체 흐름

```
[개드립 핫딜 게시판]
        │  (크롤링 · GitHub Actions Cron)
        ▼
[크롤러 스크립트 — Python]
        │  파싱 결과를 JSON으로 저장
        ▼
[data/deals.json]           ← 단일 데이터 소스
        │  (GitHub Actions로 자동 커밋 & 배포)
        ▼
[정적 프론트엔드 — Vanilla JS / HTML / CSS]
        │
        ▼
[GitHub Pages 배포]
```

### 디렉터리 구조

```
HotDealFinder/
├── CLAUDE.md                  # 이 파일
├── .github/
│   └── workflows/
│       └── crawl.yml          # 크롤링 + 배포 자동화 (Actions Cron)
├── crawler/
│   ├── crawl.py               # 메인 크롤러
│   ├── parser.py              # HTML 파싱 로직 (품목·가격·링크 추출)
│   ├── dedup.py               # 중복 게시글 처리 (구매 링크 기준)
│   └── requirements.txt       # requests, beautifulsoup4, lxml 등
├── data/
│   └── deals.json             # 크롤링 결과 저장 (자동 갱신)
├── public/                    # 정적 사이트 루트
│   ├── index.html             # 메인 페이지 (썸네일 카드 목록)
│   ├── detail.html            # 상품 상세 페이지
│   ├── css/
│   │   └── style.css          # 전체 스타일 (쇼핑몰 UI)
│   └── js/
│       ├── main.js            # 카드 렌더링·검색·카테고리 필터
│       ├── detail.js          # 상세 페이지 렌더링
│       └── utils.js           # 공통 유틸 함수
└── README.md
```

---

## 크롤러 사양

### 대상 사이트
- **현재**: `https://www.dogdrip.net/hotdeal` (개드립 핫딜 게시판)
- **확장 고려**: 다른 커뮤니티 사이트 추가 가능하도록 소스별 `source` 필드 포함

### 크롤링 주기
- GitHub Actions Cron: **5분마다** 실행 (`*/5 * * * *`)

### 수집 데이터 (게시글 1건)

| 필드 | 설명 |
|------|------|
| `id` | 개드립 게시글 고유 ID |
| `title` | 게시글 제목 (품목명 포함) |
| `price` | 가격 (원 단위 정수, 파싱 실패 시 null) |
| `thumbnail` | 대표 이미지 URL |
| `category` | 자동 분류된 카테고리 |
| `purchase_url` | 구매 가능한 사이트 URL |
| `store_name` | 쇼핑몰 이름 (11번가, 지마켓 등 — URL 패턴으로 판별) |
| `original_url` | 개드립 원문 게시글 URL |
| `duplicate_urls` | 중복 판단된 다른 게시글 URL 목록 |
| `posted_at` | 게시 시각 (ISO 8601) |
| `crawled_at` | 크롤링 시각 (ISO 8601) |
| `source` | 출처 식별자 (현재 `"dogdrip"`) |
| `extra_info` | 추가 정보 (본문 요약, 기타 메모) |

### 만료 정책
- `posted_at` 기준 **3일 초과** 게시글은 `deals.json`에서 자동 삭제

### 중복 처리
- `purchase_url`이 동일한 게시글 = 중복
- 먼저 등록된 게시글을 원본으로 유지
- 이후 중복 게시글의 `original_url`을 원본의 `duplicate_urls`에 추가

### 쇼핑몰 판별 (store_name)
구매 URL 도메인 패턴으로 자동 판별. 예시:

| 도메인 패턴 | store_name |
|------------|-----------|
| `11st.co.kr` | 11번가 |
| `gmarket.co.kr` | 지마켓 |
| `auction.co.kr` | 옥션 |
| `coupang.com` | 쿠팡 |
| `shopping.naver.com` | 네이버쇼핑 |
| `ssg.com` | SSG.COM |
| `lotteon.com` | 롯데온 |
| `wemakeprice.com` | 위메프 |
| `tmon.co.kr` | 티몬 |
| `interpark.com` | 인터파크 |
| `bunjang.co.kr` | 번개장터 |

---

## 카테고리 분류

게시글 제목과 본문 키워드를 분석해 자동 분류. 카테고리 목록:

- 전자제품
- 컴퓨터/주변기기
- 스마트폰/태블릿
- 생활가전
- 식품/음료
- 패션/의류
- 뷰티/건강
- 스포츠/레저
- 가구/인테리어
- 도서/문구
- 소프트웨어/게임
- 기타

---

## 프론트엔드 사양

### 메인 페이지 (index.html)
- 카드형 그리드 레이아웃 (썸네일 + 품목명 + 가격 + 쇼핑몰 배지)
- 상단: 카테고리 필터 탭
- 상단: 검색창 (품목명 검색)
- 정렬: 최신순 / 가격 낮은순 / 가격 높은순
- 반응형 (모바일/데스크톱)

### 상세 페이지 (detail.html?id=xxx)
- 상품 이미지 (크게)
- 품목명, 가격
- 쇼핑몰 이름 + 구매 링크 버튼
- 추가 정보 (extra_info)
- 원문 개드립 링크
- 중복 게시글 링크 목록 (있을 경우)
- 게시 시각
