import argparse
import json
import random
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.dogdrip.net"
HOTDEAL_URL = f"{BASE_URL}/hotdeal"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.dogdrip.net/",
}

KST = timezone(timedelta(hours=9))

STORE_MAP = {
    "11st.co.kr": "11번가",
    "gmarket.co.kr": "지마켓",
    "auction.co.kr": "옥션",
    "coupang.com": "쿠팡",
    "shopping.naver.com": "네이버쇼핑",
    "smartstore.naver.com": "네이버스마트스토어",
    "ssg.com": "SSG.COM",
    "lotteon.com": "롯데온",
    "wemakeprice.com": "위메프",
    "tmon.co.kr": "티몬",
    "interpark.com": "인터파크",
    "bunjang.co.kr": "번개장터",
    "ohou.se": "오늘의집",
    "musinsa.com": "무신사",
    "29cm.co.kr": "29CM",
    "kurly.com": "마켓컬리",
    "amazon.com": "Amazon",
    "aliexpress.com": "AliExpress",
}


def get_store_name(url: str) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url).hostname or ""
        host = host.lstrip("www.")
        for pattern, name in STORE_MAP.items():
            if pattern in host:
                return name
        return host
    except Exception:
        return ""


def extract_price(text: str) -> int | None:
    # "3만 5천원", "3만5천원"
    m = re.search(r'(\d[\d,]*)\s*만\s*(\d+)\s*천\s*원', text)
    if m:
        return int(m.group(1).replace(',', '')) * 10000 + int(m.group(2)) * 1000

    # "3만원", "30만원"
    m = re.search(r'(\d[\d,]*)\s*만\s*원', text)
    if m:
        return int(m.group(1).replace(',', '')) * 10000

    # "35,000원", "9,900원"
    m = re.search(r'(\d[\d,]+)\s*원', text)
    if m:
        val = int(m.group(1).replace(',', ''))
        if val > 0:
            return val

    return None


def extract_purchase_url(soup: BeautifulSoup) -> str | None:
    links = soup.find_all('a', href=True)

    # Known store domains first
    for a in links:
        href = a['href']
        if not href.startswith('http'):
            continue
        try:
            host = urlparse(href).hostname or ""
            host = host.lstrip("www.")
            for domain in STORE_MAP:
                if domain in host:
                    return href
        except Exception:
            continue

    # Any external link outside dogdrip
    for a in links:
        href = a['href']
        if not href.startswith('http'):
            continue
        if 'dogdrip.net' not in href:
            return href

    return None


def extract_thumbnail(soup: BeautifulSoup) -> str | None:
    og = soup.find('meta', property='og:image')
    if og and og.get('content'):
        return og['content']

    content = soup.find(class_=re.compile(r'article|content|post-body|ed-content', re.I))
    if content:
        img = content.find('img', src=True)
        if img:
            src = img['src']
            if src.startswith('//'):
                src = 'https:' + src
            return src

    return None


def fetch(session: requests.Session, url: str) -> BeautifulSoup | None:
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, 'lxml')
    except Exception as e:
        print(f"[WARN] fetch failed: {url} — {e}", file=sys.stderr)
        return None


def parse_listing_page(soup: BeautifulSoup) -> list[dict]:
    """목록 페이지에서 게시글 스텁 추출."""
    stubs = []
    seen_ids: set[str] = set()

    # dogdrip은 /hotdeal/숫자 패턴 링크로 게시글 판별
    links = soup.find_all('a', href=re.compile(r'/hotdeal/\d+'))
    for a in links:
        href = a['href']
        m = re.search(r'/hotdeal/(\d+)', href)
        if not m:
            continue
        pid = m.group(1)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        # 제목: 링크 텍스트 또는 부모 요소에서 추출
        title = a.get_text(strip=True)
        if not title:
            parent = a.find_parent()
            title = parent.get_text(strip=True) if parent else ""
        if not title:
            continue

        full_url = BASE_URL + href if href.startswith('/') else href
        stubs.append({
            'id': pid,
            'title': title,
            'original_url': full_url,
        })

    return stubs


def parse_posted_at(soup: BeautifulSoup) -> str:
    # og/meta 태그
    for prop in ['article:published_time', 'og:article:published_time']:
        meta = soup.find('meta', property=prop)
        if meta and meta.get('content'):
            return meta['content']

    # <time datetime="...">
    t = soup.find('time', attrs={'datetime': True})
    if t:
        return t['datetime']

    return datetime.now(KST).isoformat()


def parse_post(session: requests.Session, stub: dict) -> dict | None:
    soup = fetch(session, stub['original_url'])
    if not soup:
        return None

    posted_at = parse_posted_at(soup)
    thumbnail = extract_thumbnail(soup)
    purchase_url = extract_purchase_url(soup)
    store_name = get_store_name(purchase_url) if purchase_url else ""
    price = extract_price(stub['title'])

    return {
        'id': stub['id'],
        'title': stub['title'],
        'price': price,
        'thumbnail': thumbnail,
        'purchase_url': purchase_url,
        'store_name': store_name,
        'original_url': stub['original_url'],
        'duplicate_urls': [],
        'posted_at': posted_at,
        'crawled_at': datetime.now(KST).isoformat(),
        'source': 'dogdrip',
        'extra_info': '',
    }


def expire_old(deals: list[dict], days: int = 3) -> list[dict]:
    cutoff = datetime.now(KST) - timedelta(days=days)
    result = []
    for d in deals:
        try:
            posted = datetime.fromisoformat(d['posted_at'])
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=KST)
            if posted >= cutoff:
                result.append(d)
        except Exception:
            result.append(d)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="개드립 핫딜 크롤러")
    parser.add_argument('--pages', type=int, default=2, help='크롤링할 목록 페이지 수 (기본 2)')
    parser.add_argument('--output', default='data/deals.json', help='출력 파일 경로')
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding='utf-8'))
        except Exception:
            existing = []
    existing_ids = {d['id'] for d in existing}
    print(f"[INFO] 기존 deals: {len(existing)}개")

    session = requests.Session()
    all_stubs: list[dict] = []

    for page in range(1, args.pages + 1):
        url = f"{HOTDEAL_URL}?page={page}"
        print(f"[INFO] 목록 페이지 {page} 크롤링: {url}")
        soup = fetch(session, url)
        if not soup:
            continue
        stubs = parse_listing_page(soup)
        print(f"[INFO]   → {len(stubs)}개 게시글 발견")
        all_stubs.extend(stubs)
        time.sleep(random.uniform(0.5, 1.0))

    new_deals: list[dict] = []
    for stub in all_stubs:
        if stub['id'] in existing_ids:
            continue
        print(f"[INFO] 파싱: {stub['id']} — {stub['title'][:50]}")
        deal = parse_post(session, stub)
        if deal:
            new_deals.append(deal)
        time.sleep(random.uniform(0.5, 1.0))

    print(f"[INFO] 신규 deals: {len(new_deals)}개")

    merged = new_deals + existing
    merged = expire_old(merged)
    merged.sort(key=lambda d: d.get('posted_at', ''), reverse=True)

    output_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f"[INFO] 저장 완료: {output_path} ({len(merged)}개)")


if __name__ == '__main__':
    main()
