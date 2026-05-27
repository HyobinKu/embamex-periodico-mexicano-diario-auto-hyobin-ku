"""
mexico_briefing.py (개선판)
──────────────────────────────────────────────────────────────
주한 멕시코 대사관 뉴스 브리핑 자동화 툴 (v2.0)
네이버 뉴스 수집 → 클러스터링 → GPT 요약/번역 → 파일 저장

개선사항:
  ✓ Import 중복 제거
  ✓ 강화된 에러 처리 및 재시도 로직
  ✓ 결과를 JSON/CSV로 저장
  ✓ 구조화된 로깅
  ✓ 임베딩 캐싱
  ✓ 타임스탬프 기반 결과 디렉토리

실행:
  pip install requests beautifulsoup4 openai scikit-learn sentence-transformers
  python mexico_briefing_improved.py
  python mexico_briefing_improved.py --pages 20 --threshold 0.75 --output results
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

# ─────────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────────
QUERY = "멕시코 -뉴멕시코"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
CATEGORIES = ["외교", "경제", "문화", "치안", "스포츠", "기타"]

# 카테고리별 터미널 색상
CAT_COLORS = {
    "외교": "\033[94m",   # 파랑
    "경제": "\033[92m",   # 초록
    "문화": "\033[93m",   # 노랑
    "치안": "\033[91m",   # 빨강
    "스포츠": "\033[96m", # 시안
    "기타": "\033[90m",   # 회색
}
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"

# 캐시 설정
CACHE_DIR = Path(".cache")
EMBEDDINGS_CACHE = CACHE_DIR / "embeddings.json"

# ─────────────────────────────────────────────────────────────
# 로깅 설정
# ─────────────────────────────────────────────────────────────
def setup_logging(output_dir: Path) -> logging.Logger:
    """구조화된 로깅 설정"""
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"briefing_{timestamp}.log"
    
    logger = logging.getLogger("mexico_briefing")
    logger.setLevel(logging.DEBUG)
    
    # 파일 핸들러
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    
    # 포맷터
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger


# ─────────────────────────────────────────────────────────────
# 유틸 함수
# ─────────────────────────────────────────────────────────────
def step(n: int, total: int, msg: str):
    print(f"\n{CYAN}[{n}/{total}]{RESET} {BOLD}{msg}{RESET}")

def ok(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")

def info(msg: str):
    print(f"  {DIM}{msg}{RESET}")

def err(msg: str):
    print(f"  {RED}✗ {msg}{RESET}")

def section(title: str):
    width = 60
    print(f"\n{'─' * width}")
    print(f"  {BOLD}{title}{RESET}")
    print(f"{'─' * width}")


# ─────────────────────────────────────────────────────────────
# 캐싱 함수
# ─────────────────────────────────────────────────────────────
def load_embeddings_cache() -> dict:
    """임베딩 캐시 로드"""
    CACHE_DIR.mkdir(exist_ok=True)
    if EMBEDDINGS_CACHE.exists():
        try:
            with open(EMBEDDINGS_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_embeddings_cache(cache: dict):
    """임베딩 캐시 저장"""
    CACHE_DIR.mkdir(exist_ok=True)
    with open(EMBEDDINGS_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────
# 1. 네이버 뉴스 수집 (개선됨: 재시도 로직)
# ─────────────────────────────────────────────────────────────
def collect_news(max_pages: int = 10, logger: Optional[logging.Logger] = None) -> list[dict]:
    """네이버 뉴스 수집 (재시도 로직 포함)"""
    from urllib.parse import quote
    
    step(1, 4, f"네이버 뉴스 수집 (최대 {max_pages}페이지 / {max_pages*10}건)")

    articles = []
    seen_urls: set[str] = set()
    encoded = quote(QUERY)
    max_retries = 3

    for page in range(1, max_pages + 1):
        start = (page - 1) * 10 + 1
        url = (
            f"https://search.naver.com/search.naver"
            f"?where=news&query={encoded}&start={start}&sort=1"
        )
        
        for attempt in range(1, max_retries + 1):
            try:
                res = requests.get(url, headers=HEADERS, timeout=10)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")
                items = soup.select("div.news_area")
                
                if not items:
                    info(f"페이지 {page}: 결과 없음, 종료")
                    if logger:
                        logger.info(f"Page {page}: No results found")
                    return articles

                for item in items:
                    title_el = item.select_one("a.news_tit")
                    if not title_el:
                        continue
                    title = title_el.get("title", "").strip()
                    link  = title_el.get("href", "")
                    if not title or link in seen_urls:
                        continue
                    if "뉴멕시코" in title or "New Mexico" in title:
                        continue
                    press_el = item.select_one("a.info.press")
                    press = press_el.get_text(strip=True) if press_el else ""
                    seen_urls.add(link)
                    articles.append({"title": title, "url": link, "press": press})

                info(f"페이지 {page}/{max_pages} 완료 — 누적 {len(articles)}건")
                if logger:
                    logger.info(f"Page {page} collected: {len(articles)} total articles")
                time.sleep(0.3)
                break

            except requests.Timeout:
                if attempt < max_retries:
                    info(f"페이지 {page} 시간초과, {attempt}/{max_retries-1} 재시도 중...")
                    time.sleep(2 ** attempt)
                else:
                    err(f"페이지 {page} 최종 실패 (시간초과)")
                    if logger:
                        logger.error(f"Page {page} timeout after {max_retries} attempts")
            except Exception as e:
                if attempt < max_retries:
                    info(f"페이지 {page} 오류, {attempt}/{max_retries-1} 재시도 중...")
                    time.sleep(2 ** attempt)
                else:
                    err(f"페이지 {page} 최종 실패: {e}")
                    if logger:
                        logger.error(f"Page {page} error: {e}")

    ok(f"수집 완료 — 총 {len(articles)}건")
    if logger:
        logger.info(f"Collection complete: {len(articles)} articles")
    return articles


# ─────────────────────────────────────────────────────────────
# 2. 클러스터링 (개선됨: 캐싱)
# ─────────────────────────────────────────────────────────────
def cluster_articles(
    articles: list[dict], 
    threshold: float = 0.78,
    logger: Optional[logging.Logger] = None
) -> list[list[dict]]:
    """기사 클러스터링 (임베딩 캐싱)"""
    step(2, 4, "기사 클러스터링")

    try:
        from sentence_transformers import SentenceTransformer
        info("sentence-transformers 모델 로딩 중...")
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        texts = [a["title"] for a in articles]
        
        # 캐시 로드
        cache = load_embeddings_cache()
        embeddings_list = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            if text in cache:
                embeddings_list.append(cache[text])
            else:
                uncached_indices.append(i)
        
        # 캐시되지 않은 텍스트만 처리
        if uncached_indices:
            uncached_texts = [texts[i] for i in uncached_indices]
            new_embeddings = model.encode(uncached_texts, show_progress_bar=False)
            for idx, emb in zip(uncached_indices, new_embeddings):
                embeddings_list.insert(idx, emb.tolist())
                cache[texts[idx]] = emb.tolist()
            save_embeddings_cache(cache)
        
        embeddings = embeddings_list
        use_vectors = True
        if logger:
            logger.info(f"Embeddings computed: {len(uncached_indices)} new, {len(cache)} cached")
    except ImportError:
        info("sentence-transformers 미설치 → 키워드 기반 클러스터링 사용")
        use_vectors = False
        embeddings = None

    used: set[int] = set()
    clusters: list[list[dict]] = []

    def keyword_sim(t1: str, t2: str) -> float:
        kw = lambda t: set(re.sub(r"[^\w가-힣]", " ", t).split())
        a, b = kw(t1), kw(t2)
        if not a or not b:
            return 0.0
        return len(a & b) / max(len(a), len(b))

    for i in range(len(articles)):
        if i in used:
            continue
        cluster = [articles[i]]
        used.add(i)
        for j in range(i + 1, len(articles)):
            if j in used:
                continue
            if use_vectors:
                score = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
            else:
                score = keyword_sim(articles[i]["title"], articles[j]["title"])
            if score >= threshold:
                cluster.append(articles[j])
                used.add(j)
        clusters.append(cluster)

    clusters.sort(key=lambda c: len(c), reverse=True)
    ok(f"클러스터링 완료 — {len(clusters)}개 그룹")
    if logger:
        logger.info(f"Clustering complete: {len(clusters)} clusters")
    return clusters


# ─────────────────────────────────────────────────────────────
# 3. GPT 요약 + 스페인어 번역 (개선됨: 강화된 에러 처리)
# ─────────────────────────────────────────────────────────────
def summarize_all(
    client: OpenAI, 
    clusters: list[list[dict]], 
    top_n: int = 15,
    logger: Optional[logging.Logger] = None
) -> list[dict]:
    """AI 요약 + 스페인어 번역"""
    step(3, 4, f"AI 요약 + 스페인어 번역 (상위 {min(top_n, len(clusters))}개 클러스터)")

    results = []
    for i, cluster in enumerate(clusters[:top_n]):
        titles = "\n".join(f"- {a['title']}" for a in cluster[:8])
        prompt = f"""다음 뉴스 기사 제목들을 분석해라:
{titles}

아래 JSON 형식으로만 답해라 (마크다운 없이):
{{
  "summary_ko": "2~3줄 한국어 요약 (육하원칙 기반)",
  "summary_es": "스페인어 외교 공식보고체 번역 (단순과거, 과장 없이, 3문장 이내)",
  "category": "{'/'.join(CATEGORIES)} 중 하나"
}}"""

        max_retries = 3
        parsed = None
        
        for attempt in range(1, max_retries + 1):
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "너는 주한 멕시코 대사관 뉴스 분석관이다. JSON만 출력한다."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=600,
                )
                raw = resp.choices[0].message.content.strip()
                
                # JSON 파싱 (마크다운 제거)
                clean_json = raw.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_json)
                
                if logger:
                    logger.debug(f"Cluster {i+1} summarized successfully")
                break
                
            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    if logger:
                        logger.warning(f"Cluster {i+1} JSON parse error (attempt {attempt}/{max_retries}): {e}")
                    time.sleep(1)
                else:
                    err(f"클러스터 {i+1} JSON 파싱 실패")
                    parsed = {
                        "summary_ko": cluster[0]["title"],
                        "summary_es": "",
                        "category": "기타"
                    }
                    if logger:
                        logger.error(f"Cluster {i+1} JSON parse failed after {max_retries} attempts")
                        
            except Exception as e:
                if attempt < max_retries:
                    if logger:
                        logger.warning(f"Cluster {i+1} API error (attempt {attempt}/{max_retries}): {e}")
                    time.sleep(2)
                else:
                    err(f"클러스터 {i+1} API 실패: {e}")
                    parsed = {
                        "summary_ko": cluster[0]["title"],
                        "summary_es": "",
                        "category": "기타"
                    }
                    if logger:
                        logger.error(f"Cluster {i+1} API failed after {max_retries} attempts: {e}")

        if not parsed:
            parsed = {
                "summary_ko": cluster[0]["title"],
                "summary_es": "",
                "category": "기타"
            }

        results.append({
            "title":      cluster[0]["title"],
            "summary_ko": parsed.get("summary_ko", ""),
            "summary_es": parsed.get("summary_es", ""),
            "category":   parsed.get("category", "기타"),
            "articles":   cluster,
        })
        info(f"{i+1}/{min(top_n, len(clusters))} [{parsed.get('category','기타')}] {cluster[0]['title'][:45]}...")
        time.sleep(0.5)

    ok(f"요약 완료 — {len(results)}건")
    if logger:
        logger.info(f"Summarization complete: {len(results)} results")
    return results


# ─────────────────────────────────────────────────────────────
# 4. 화면 출력
# ─────────────────────────────────────────────────────────────
def print_briefing(results: list[dict], total_articles: int):
    """브리핑을 터미널에 출력"""
    step(4, 4, "브리핑 출력")

    now = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")

    print(f"\n{'━' * 62}")
    print(f"  {BOLD}🇲🇽 멕시코 뉴스 브리핑{RESET}  {DIM}{now}{RESET}")
    print(f"  {DIM}수집 기사 {total_articles}건 → {len(results)}개 클러스터{RESET}")
    print(f"{'━' * 62}")

    for idx, item in enumerate(results, 1):
        cat   = item.get("category", "기타")
        color = CAT_COLORS.get(cat, RESET)

        print(f"\n{BOLD}{idx:02d}.{RESET} {BOLD}{item['title']}{RESET}  {color}[{cat}]{RESET}")
        print(f"    {DIM}관련 기사 {len(item['articles'])}건{RESET}")
        print()

        # 한국어 요약
        print(f"  {BOLD}▸ 한국어 요약{RESET}")
        for line in item["summary_ko"].split(". "):
            line = line.strip()
            if line:
                print(f"    {line}{'.' if not line.endswith('.') else ''}")
        print()

        # 스페인어 번역
        if item.get("summary_es"):
            print(f"  {BOLD}▸ Resumen en español{RESET}")
            for line in item["summary_es"].split(". "):
                line = line.strip()
                if line:
                    print(f"    {DIM}{line}{'.' if not line.endswith('.') else ''}{RESET}")
            print()

        # 원문 링크
        print(f"  {BOLD}▸ 원문 기사{RESET}")
        for art in item["articles"][:5]:
            press = f"[{art['press']}]" if art["press"] else ""
            print(f"    {DIM}{press}{RESET} {art['title'][:55]}")
            print(f"    {CYAN}{art['url']}{RESET}")
        if len(item["articles"]) > 5:
            print(f"    {DIM}... 외 {len(item['articles'])-5}건{RESET}")

        print(f"\n  {'·' * 56}")

    print(f"\n{'━' * 62}")
    print(f"  {GREEN}{BOLD}브리핑 완료{RESET}  {DIM}{now}{RESET}")
    print(f"{'━' * 62}\n")


# ─────────────────────────────────────────────────────────────
# 5. 결과 저장 (NEW)
# ─────────────────────────────────────────────────────────────
def save_results(results: list[dict], total_articles: int, output_dir: Path):
    """결과를 JSON, CSV, HTML로 저장"""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # ───────────────────────────────────────────────────────────
    # JSON 저장
    # ───────────────────────────────────────────────────────────
    json_path = output_dir / f"briefing_{timestamp}.json"
    json_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_articles": total_articles,
            "total_clusters": len(results),
        },
        "results": []
    }
    
    for item in results:
        json_data["results"].append({
            "title": item["title"],
            "category": item["category"],
            "summary_ko": item["summary_ko"],
            "summary_es": item["summary_es"],
            "article_count": len(item["articles"]),
            "articles": [
                {
                    "title": a["title"],
                    "url": a["url"],
                    "press": a["press"]
                }
                for a in item["articles"]
            ]
        })
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    ok(f"JSON 저장: {json_path}")
    
    # ───────────────────────────────────────────────────────────
    # CSV 저장 (요약 정보)
    # ───────────────────────────────────────────────────────────
    csv_path = output_dir / f"briefing_summary_{timestamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["번호", "제목", "카테고리", "한국어 요약", "스페인어 요약", "관련기사수"]
        )
        writer.writeheader()
        for idx, item in enumerate(results, 1):
            writer.writerow({
                "번호": idx,
                "제목": item["title"],
                "카테고리": item["category"],
                "한국어 요약": item["summary_ko"].replace("\n", " "),
                "스페인어 요약": item["summary_es"].replace("\n", " "),
                "관련기사수": len(item["articles"])
            })
    ok(f"CSV 저장: {csv_path}")
    
    # ───────────────────────────────────────────────────────────
    # CSV 저장 (상세 기사)
    # ───────────────────────────────────────────────────────────
    csv_detail_path = output_dir / f"briefing_articles_{timestamp}.csv"
    with open(csv_detail_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["클러스터번호", "기사제목", "언론사", "URL"]
        )
        writer.writeheader()
        for idx, item in enumerate(results, 1):
            for art in item["articles"]:
                writer.writerow({
                    "클러스터번호": idx,
                    "기사제목": art["title"],
                    "언론사": art["press"],
                    "URL": art["url"]
                })
    ok(f"CSV 저장 (상세): {csv_detail_path}")
    
    # ───────────────────────────────────────────────────────────
    # HTML 저장 (깔끔한 레이아웃)
    # ───────────────────────────────────────────────────────────
    html_path = output_dir / f"briefing_{timestamp}.html"
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>멕시코 뉴스 브리핑</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .metadata {{
            font-size: 0.9em;
            margin-top: 10px;
            opacity: 0.9;
        }}
        .cluster {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            border-left: 5px solid #667eea;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .cluster.diplomatic {{ border-left-color: #3b82f6; }}
        .cluster.economic {{ border-left-color: #10b981; }}
        .cluster.cultural {{ border-left-color: #f59e0b; }}
        .cluster.security {{ border-left-color: #ef4444; }}
        .cluster.sports {{ border-left-color: #06b6d4; }}
        .cluster.other {{ border-left-color: #6b7280; }}
        
        .cluster-title {{
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .category-badge {{
            font-size: 0.7em;
            padding: 4px 10px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
        }}
        .badge-diplomatic {{ background-color: #3b82f6; }}
        .badge-economic {{ background-color: #10b981; }}
        .badge-cultural {{ background-color: #f59e0b; }}
        .badge-security {{ background-color: #ef4444; }}
        .badge-sports {{ background-color: #06b6d4; }}
        .badge-other {{ background-color: #6b7280; }}
        
        .summary-section {{
            margin: 15px 0;
        }}
        .summary-label {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
            font-size: 0.9em;
        }}
        .summary-text {{
            line-height: 1.6;
            margin: 5px 0;
            padding-left: 10px;
            border-left: 3px solid #e5e7eb;
        }}
        .articles {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e5e7eb;
        }}
        .articles-label {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
            font-size: 0.9em;
        }}
        .article {{
            margin-bottom: 10px;
            padding: 8px;
            background: #f9fafb;
            border-radius: 4px;
        }}
        .article-title {{
            font-weight: 500;
            margin-bottom: 4px;
        }}
        .article-press {{
            color: #6b7280;
            font-size: 0.85em;
            margin-bottom: 4px;
        }}
        .article-url {{
            color: #3b82f6;
            word-break: break-all;
            font-size: 0.85em;
            text-decoration: none;
        }}
        .article-url:hover {{
            text-decoration: underline;
        }}
        .footer {{
            text-align: center;
            color: #6b7280;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🇲🇽 멕시코 뉴스 브리핑</h1>
        <div class="metadata">
            <p>생성 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}</p>
            <p>수집 기사 {total_articles}건 → {len(results)}개 클러스터</p>
        </div>
    </div>
"""
    
    cat_to_class = {
        "외교": "diplomatic",
        "경제": "economic",
        "문화": "cultural",
        "치안": "security",
        "스포츠": "sports",
        "기타": "other"
    }
    
    for idx, item in enumerate(results, 1):
        cat = item["category"]
        cat_class = cat_to_class.get(cat, "other")
        
        html_content += f"""    <div class="cluster {cat_class}">
        <div class="cluster-title">
            <span>{idx}. {item['title']}</span>
            <span class="category-badge badge-{cat_class}">{cat}</span>
        </div>
        
        <div class="summary-section">
            <div class="summary-label">▸ 한국어 요약</div>
            <div class="summary-text">{item['summary_ko']}</div>
        </div>
"""
        
        if item.get("summary_es"):
            html_content += f"""        <div class="summary-section">
            <div class="summary-label">▸ Resumen en español</div>
            <div class="summary-text">{item['summary_es']}</div>
        </div>
"""
        
        html_content += f"""        <div class="articles">
            <div class="articles-label">▸ 원문 기사 ({len(item['articles'])}건)</div>
"""
        
        for art in item["articles"][:10]:
            press = f"[{art['press']}]" if art["press"] else ""
            html_content += f"""            <div class="article">
                <div class="article-title">{art['title']}</div>
                <div class="article-press">{press}</div>
                <a class="article-url" href="{art['url']}" target="_blank">{art['url']}</a>
            </div>
"""
        
        if len(item["articles"]) > 10:
            html_content += f"""            <div class="article" style="color: #6b7280; font-size: 0.85em;">
                ... 외 {len(item['articles'])-10}건
            </div>
"""
        
        html_content += """        </div>
    </div>
"""
    
    html_content += f"""    <div class="footer">
        <p>멕시코 뉴스 브리핑 자동화 시스템 v2.0</p>
        <p>Generated at {datetime.now().isoformat()}</p>
    </div>
</body>
</html>
"""
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    ok(f"HTML 저장: {html_path}")
    
    return {
        "json": str(json_path),
        "csv_summary": str(csv_path),
        "csv_articles": str(csv_detail_path),
        "html": str(html_path)
    }


# ─────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="멕시코 뉴스 브리핑 자동화 v2.0")
    parser.add_argument("--pages",     type=int,   default=10,      help="수집 페이지 수 (기본 10)")
    parser.add_argument("--threshold", type=float, default=0.78,    help="클러스터링 유사도 기준 (기본 0.78)")
    parser.add_argument("--top",       type=int,   default=15,      help="요약할 최대 클러스터 수 (기본 15)")
    parser.add_argument("--output",    type=str,   default="results", help="결과 저장 디렉토리 (기본 results)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    logger = setup_logging(output_dir)
    
    # OpenAI API Key
    api_key = os.getenv("OPENAI_API_KEY") or ""
    if not api_key:
        api_key = input(f"\n{YELLOW}OpenAI API Key (sk-...): {RESET}").strip()
    if not api_key.startswith("sk-"):
        print(f"{RED}유효하지 않은 API Key입니다.{RESET}")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    section("멕시코 뉴스 브리핑 자동화 v2.0 시작")
    print(f"  페이지: {args.pages}  |  유사도 기준: {args.threshold}  |  상위: {args.top}개")
    print(f"  결과 저장: {output_dir.resolve()}")
    
    logger.info(f"Starting briefing with pages={args.pages}, threshold={args.threshold}, top={args.top}")

    articles = collect_news(max_pages=args.pages, logger=logger)
    if not articles:
        msg = "수집된 기사가 없습니다. 잠시 후 다시 시도해주세요."
        print(f"\n{RED}{msg}{RESET}\n")
        logger.error(msg)
        sys.exit(1)

    clusters = cluster_articles(articles, threshold=args.threshold, logger=logger)
    results  = summarize_all(client, clusters, top_n=args.top, logger=logger)
    
    print_briefing(results, total_articles=len(articles))
    
    # 결과 저장
    section("결과 저장")
    file_info = save_results(results, len(articles), output_dir)
    print()
    info(f"저장된 파일:")
    for file_type, path in file_info.items():
        print(f"  {file_type.upper()}: {path}")
    
    logger.info(f"Briefing complete. Files saved to {output_dir}")


if __name__ == "__main__":
    main()
