# Circuit Netlist Converter

PCB 회로 데이터시트/이미지(PDF, PNG, JPG)를 로컬 LLM(Ollama)으로 분석하여
Zuken 호환 넷리스트로 변환하고, 회로도 이미지를 생성하는 도구입니다.

## 사전 요구사항

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) 패키지 매니저
- [Ollama](https://ollama.ai/) + `llama3.2-vision` 모델

## 설치

```bash
uv venv
uv pip install -e ".[dev]"
```

## Ollama 모델 준비

```bash
ollama pull llama3.2-vision
ollama pull nomic-embed-text
```

## 사용법

### CLI

```bash
# 파일 변환
netlist convert input.pdf -o output.cir -f spice

# 넷리스트 시각화
netlist visualize output.cir -o schematic.png

# DB 조회
netlist db list
```

### Web UI

```bash
netlist web
# http://localhost:8000 접속
```

## 지원 출력 포맷

| 포맷 | 확장자 | 설명 |
|------|--------|------|
| SPICE | .cir | 범용 넷리스트 (대부분 EDA 도구 호환) |
| EDIF 2.0.0 | .edf | Zuken CR-5000/CR-8000 import 가능 |
| KiCad | .net | 오픈소스 EDA 도구 호환 |
| JSON | .json | 커스텀 import 용 |

## 프로젝트 구조

```
src/netlist_converter/
  core/           - 문서 로딩, 비전 분석, 파싱
  models/         - Pydantic 데이터 모델
  generators/     - 넷리스트/이미지 생성기
  db/             - ChromaDB + SQLite 저장소
  llm/            - LLM Provider 추상화
  web/            - FastAPI Web UI
```
