# 🚀 빠른 시작 가이드

## 5분 안에 시작하기

### 1단계: 설치 (2분)
```bash
# 저장소 복제
git clone https://github.com/HyobinKu/embamex-periodico-mexicano-diario-auto-hyobin-ku.git
cd embamex-periodico-mexicano-diario-auto-hyobin-ku

# 의존성 설치
pip install -r requirements.txt
```

### 2단계: API 키 준비 (1분)
1. [OpenAI 웹사이트](https://platform.openai.com/api-keys)에서 API 키 생성
2. 키를 환경변수로 설정:
```bash
export OPENAI_API_KEY="sk-your-api-key"  # Linux/Mac
set OPENAI_API_KEY=sk-your-api-key      # Windows
```

### 3단계: 실행 (2분)
```bash
python mexico_briefing_improved.py
```

## 💡 자주 사용하는 명령어

### 기본 실행
```bash
python mexico_briefing_improved.py
```

### 더 많은 기사 수집
```bash
python mexico_briefing_improved.py --pages 20
```

### 맞춤 설정
```bash
python mexico_briefing_improved.py --pages 15 --threshold 0.75 --top 10
```

### 다른 폴더에 저장
```bash
python mexico_briefing_improved.py --output my_briefings
```

## 📂 결과 확인

```
results/
├── briefing_20240527_143022.json       # 모든 데이터
├── briefing_summary_20240527_143022.csv # 요약 (Excel/Google Sheets 열기 가능)
├── briefing_articles_20240527_143022.csv # 전체 기사
└── briefing_20240527_143022.html        # 웹브라우저에서 열기 👈 추천!
```

## ✅ 체크리스트

- [ ] Python 3.8+ 설치
- [ ] `pip install -r requirements.txt` 실행
- [ ] OpenAI API 키 발급
- [ ] 환경변수 설정
- [ ] `python mexico_briefing_improved.py` 실행
- [ ] `results/briefing_*.html` 웹브라우저에서 열기

## 🎯 팁

1. **첫 실행이 느린 이유**: 문장 임베딩 모델 다운로드 중입니다 (한번만)
2. **API 비용 절감**: `--top 5` 로 상위 5개만 요약하면 더 저렴
3. **좋은 결과**: `--pages 15 --threshold 0.75` 권장
4. **자동화**: 매일 아침 자동 실행하게 설정 가능

## 🆘 문제 해결

**"ModuleNotFoundError" 나는 경우**
```bash
pip install -r requirements.txt --upgrade
```

**"Invalid API key" 나는 경우**
```bash
# API 키 확인
echo $OPENAI_API_KEY

# 유효한 API 키인지 확인 (sk-로 시작해야 함)
```

**"No articles found" 나는 경우**
- 네트워크 연결 확인
- `--pages 20`으로 더 많은 페이지 수집
- 잠시 후 다시 실행

## 📞 지원

문제가 있으면 [GitHub Issues](https://github.com/HyobinKu/embamex-periodico-mexicano-diario-auto-hyobin-ku/issues)에 등록하세요!