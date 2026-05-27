# 🇲🇽 멕시코 뉴스 브리핑 자동화 도구

**주한 멕시코 대사관 일일 기사 브리핑 자동화 시스템**

네이버 뉴스에서 최근 24시간 멕시코 관련 기사를 수집하여, GPT-4를 활용해 한국어/스페인어로 요약 및 번역한 후, 다양한 형식으로 저장하는 자동화 도구입니다.

## ✨ 주요 기능

- 🔍 **자동 뉴스 수집**: 네이버 뉴스에서 멕시코 관련 기사 수집
- 🔗 **스마트 클러스터링**: 유사한 기사들을 자동으로 그룹화
- 🤖 **AI 요약 및 번역**: GPT-4o-mini를 활용한 한국어/스페인어 이중 요약
- 💾 **다중 포맷 저장**: JSON, CSV, HTML 형식으로 자동 저장
- 📊 **카테고리 분류**: 외교, 경제, 문화, 치안, 스포츠, 기타로 자동 분류
- ⚡ **임베딩 캐싱**: 반복 실행 시 속도 향상
- 🔄 **자동 재시도**: 네트워크 오류 시 자동 재시도 로직
- 📝 **구조화된 로깅**: 모든 실행 과정을 로그에 기록

## 📋 개선사항 (v2.0)

- ✅ Import 중복 제거
- ✅ 강화된 에러 처리 및 재시도 로직
- ✅ 결과를 JSON/CSV/HTML로 저장
- ✅ 구조화된 로깅 시스템
- ✅ 임베딩 캐싱으로 성능 향상
- ✅ 타임스탬프 기반 결과 디렉토리 자동 생성

## 📦 설치

### 1. 저장소 복제
```bash
git clone https://github.com/HyobinKu/embamex-periodico-mexicano-diario-auto-hyobin-ku.git
cd embamex-periodico-mexicano-diario-auto-hyobin-ku
```

### 2. 가상 환경 설정 (권장)
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. OpenAI API 키 설정
```bash
# 환경변수로 설정 (권장)
export OPENAI_API_KEY="sk-your-api-key-here"

# 또는 실행 시 입력
python mexico_briefing_improved.py
```

## 🚀 사용법

### 기본 실행
```bash
python mexico_briefing_improved.py
```

### 커스텀 옵션
```bash
python mexico_briefing_improved.py \
  --pages 20 \
  --threshold 0.75 \
  --top 10 \
  --output my_results
```

### 커맨드 라인 옵션

| 옵션 | 기본값 | 설명 |
|------|-------|------|
| `--pages` | 10 | 수집할 네이버 뉴스 페이지 수 (최대 40) |
| `--threshold` | 0.78 | 클러스터링 유사도 임계값 (0.0~1.0) |
| `--top` | 15 | AI 요약할 최대 클러스터 수 |
| `--output` | results | 결과 저장 디렉토리 |

## 📂 출력 파일

실행 후 다음 파일들이 생성됩니다:

```
results/
├── briefing_20240527_143022.json           # 완전한 JSON 데이터
├── briefing_summary_20240527_143022.csv    # 요약 정보 (CSV)
├── briefing_articles_20240527_143022.csv   # 상세 기사 목록 (CSV)
├── briefing_20240527_143022.html           # 아름다운 웹 뷰
└── logs/
    └── briefing_20240527_143022.log        # 실행 로그
```

### JSON 구조
```json
{
  "metadata": {
    "generated_at": "2024-05-27T14:30:22.123456",
    "total_articles": 45,
    "total_clusters": 12
  },
  "results": [
    {
      "title": "멕시코 대통령 방한",
      "category": "외교",
      "summary_ko": "멕시코의 셰인바움 대통령이 한국을 방문...",
      "summary_es": "La presidenta de México Claudia Sheinbaum visitó Corea del Sur...",
      "article_count": 3,
      "articles": [
        {
          "title": "멕시코 대통령 한국 방문 (경향신문)",
          "url": "https://...",
          "press": "경향신문"
        }
      ]
    }
  ]
}
```

### CSV 형식
**briefing_summary_*.csv**
```
번호,제목,카테고리,한국어 요약,스페인어 요약,관련기사수
1,멕시코 대통령 방한,외교,멕시코의 셰인바움...,La presidenta de México...,3
```

**briefing_articles_*.csv**
```
클러스터번호,기사제목,언론사,URL
1,멕시코 대통령 한국 방문,경향신문,https://...
```

## 🔧 환경 설정

### .env 파일 (선택사항)
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

### 클러스터링 임계값 튜닝
- `--threshold 0.95`: 매우 높은 유사도만 그룹화 (적은 클러스터)
- `--threshold 0.78`: 기본값 (균형잡힌 그룹화)
- `--threshold 0.50`: 낮은 유사도도 그룹화 (많은 클러스터)

## 📊 카테고리

| 카테고리 | 색상 | 예시 |
|---------|------|------|
| 외교 | 🔵 파랑 | 대사 방문, 국제 회담 |
| 경제 | 🟢 초록 | 무역, 투자, 기업 뉴스 |
| 문화 | 🟡 노랑 | 영화, 음악, 예술 전시 |
| 치안 | 🔴 빨강 | 마약, 범죄, 안전 |
| 스포츠 | 🔵 시안 | 축구, 올림픽, 체육 |
| 기타 | ⚫ 회색 | 기타 뉴스 |

## 🔄 자동화 스케줄링 (선택사항)

### Linux/Mac (Cron)
```bash
# 매일 오전 8시 실행
0 8 * * * cd /path/to/repo && /path/to/venv/bin/python mexico_briefing_improved.py --output results >> results/cron.log 2>&1
```

### Windows (Task Scheduler)
1. Task Scheduler 실행
2. "기본 작업 만들기"
3. 트리거: 매일 오전 8시
4. 작업: `python mexico_briefing_improved.py --output results`

## ⚠️ 주의사항

- **API 키**: OpenAI API 키가 필수입니다 (유료 서비스)
- **네이버 크롤링**: 네이버의 이용약관을 준수하세요
- **Rate Limiting**: 과도한 요청은 피하세요
- **캐시**: `.cache/` 디렉토리가 자동 생성됩니다

## 🐛 트러블슈팅

### "ModuleNotFoundError: No module named 'sentence_transformers'"
```bash
pip install sentence-transformers
```

### "OpenAI API Error: Invalid API key"
- API 키가 올바른지 확인하세요
- `sk-` 로 시작하는지 확인하세요
- 환경변수 설정 확인

### "No articles found" 나는 경우
- 네이버 뉴스 페이지 구조 변경될 수 있습니다
- 일시적인 네트워크 문제일 수 있습니다
- `--pages` 값을 늘려보세요

## 📈 성능 최적화

- **첫 실행**: 문장 임베딩 모델 다운로드 (약 5-10분)
- **이후 실행**: 캐싱으로 빠른 속도 (약 1-2분)
- **병렬 처리**: 추후 버전에서 추가 예정

## 📝 로그 분석

```bash
# 최근 실행 로그 확인
tail -f results/logs/briefing_*.log

# 오류 확인
grep ERROR results/logs/briefing_*.log
```

## 🤝 기여 방법

이슈 제보 및 Pull Request를 환영합니다!

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 공개되어 있습니다.

## 👨‍💻 개발자

**Hyobin Ku** - [@HyobinKu](https://github.com/HyobinKu)

## 🙏 감사의 말

- OpenAI (GPT-4o-mini)
- Sentence Transformers
- Naver News
- Beautiful Soup

## 📞 문의

이슈 및 질문은 GitHub Issues에서 수집됩니다.

---

**마지막 업데이트**: 2024년 5월 27일
**버전**: 2.0
**상태**: ✅ 활발히 유지 중