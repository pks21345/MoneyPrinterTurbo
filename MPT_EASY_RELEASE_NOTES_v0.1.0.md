# MPT Easy v0.1.0 (draft)

> 이 파일은 GitHub Release 초안입니다. 실제 태그·릴리스는 아직 생성하지 않았습니다.

## 제목 (안)

`MPT Easy v0.1.0 — 한국어 초보자용 Easy UI`

## 본문 (안)

[MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)의 생성 엔진을 그대로
사용하는 한국어 Easy UI 레이어입니다. 복잡한 옵션 없이 주제만 입력하면 쇼츠를 만들 수
있습니다. 기존 고급 WebUI와 생성 엔진은 전혀 수정하지 않았고, 그 위에 별도 화면만
추가했습니다.

### 무엇이 달라지나요

- `MPT Easy.command`(Mac) / `easy_webui.bat`(Windows) / `easy_webui.sh`(Linux)를 실행하면
  기존 `webui.sh`/`webui.bat`와 별개로 Easy 전용 화면이 뜹니다.
- 주제 입력 → 콘텐츠 유형/영상 길이/음성 선택 → 영상 만들기, 4단계면 끝입니다.
- LLM Provider와 Pexels API Key만 화면에서 저장하면 됩니다. 기본 한국어 음성은
  Edge 계열이라 별도 Key가 필요 없습니다.
- 진행 중에는 실제 생성 단계(문안 생성 → 검색어 구성 → 음성 생성 → 자막 생성 →
  영상 소재 준비 → 영상 합성)를 그대로 보여줍니다. 가짜 진행률이 아닙니다.

### 검증

- 유닛 테스트 55개 + 20 subtests(Easy 전용), 전체 회귀 653 passed / 실패 0
- 실제 API로 전 구간 E2E 1회 완주(LLM 자동 생성 포함, 우회 없음) — 306초, 9:16 MP4 완성 확인
- API Key 노출 여부 재검사 결과 0건

### 알려진 제한

- 무료 LLM Provider의 사용량 한도는 외부 서비스 정책에 따라 바뀔 수 있습니다.
- 영상 길이 프리셋은 정확한 초 단위를 보장하지 않습니다.
- Finder 더블클릭 자체의 최종 확인은 각자 실사용 환경에서 한 번 해보시길 권합니다.

### 설치

기존 저장소를 그대로 업데이트하면 됩니다. 새 의존성은 없습니다(기존 `pyproject.toml`
그대로 사용). `config.toml`은 건드리지 않으므로 기존 설정을 유지한 채 바로 사용 가능합니다.
