# MPT Easy Changelog

## v0.1.0 — 미출시 (draft)

### Added

- 한국어 Easy UI (`webui/easy/App.py`), 기존 `webui/Main.py`는 그대로 유지
- Preset Engine (`webui/easy/presets.py`): 콘텐츠 유형 3종(정보형 쇼츠/꿀팁·리스트/자유 제작),
  영상 길이 3종(짧게/보통/길게)을 `video_clip_duration`/`paragraph_number` 안전 프로필로 매핑
- `VideoParams` 매핑 (`build_video_params`): `video_count=1`, `subtitle_enabled=True`,
  기본 화면비율 9:16 유지, 기존 `VideoParams` 기본값 재사용
- 준비 상태 검사 (`webui/easy/readiness.py`): 영상 주제 / LLM Provider 설정 / 영상 소재
  Provider(Pexels/Pixabay/Coverr/local/loomloom) 설정을 생성 제출 전에 확인
- LLM/Pexels 초기 설정 화면 (`webui/easy/setup.py`): Kimi/OpenAI/Gemini/Ollama 지원,
  기존 `config.toml` 저장 시스템 재사용, 빈 입력값은 기존 Key를 삭제하지 않음
- 실제 generation 제출 (`webui/easy/generation.py`): readiness 통과 시에만
  `app.services.webui_task.submit_generation()` 호출
- progress/result UI (`webui/easy/progress.py`): 실제 task state(0/5/10/20/30/40/50/100)를
  6단계 한국어 라벨로 투영, 완료 시 결과 MP4 preview/download
- secret masking (`webui/easy/safety.py`): `api_key=`/`Authorization: Bearer`/`token=`/
  `access_token`/`password`/`sk-*`/`AIza*` 패턴 마스킹
- task path safety (`safe_result_video_paths`): 결과 MP4 노출을 해당 task 폴더 내부로 제한
- Mac(`MPT Easy.command`)/Windows(`easy_webui.bat`)/Linux(`easy_webui.sh`) 실행 파일,
  `.venv` → `uv` → PATH streamlit 순 탐색, 포트 충돌 시 자동 회피(8502~8599)

### Security

- `config.toml` 값을 화면·로그·예외에 평문 노출하지 않음
- 저장된 API Key는 Easy 설정 화면에 다시 표시되지 않음(write-only)
- 결과 영상 다운로드는 task 폴더 밖 경로를 허용하지 않음(경로 순회 방지)

### Tested

- 신규 유닛 테스트 7개 파일, 55 passed + 20 subtests
- 전체 회귀 653 passed / 11 skipped / 실패 0 (`pytest -q test`)
- `compileall`, `ruff check` 통과
- FULL E2E 실제 검증 완료: 실제 OpenAI 호환 LLM 계정으로 script/video_terms 자동 생성
  → Pexels 실제 검색·다운로드 → Edge 한국어 TTS → 자막 → ffmpeg 합성까지 전 구간
  사전 주입 없이 통과 (306.2초, 1080x1920 h264+aac MP4). 이때 사용한 base_url은
  Easy UI 화면에서 직접 바꿀 수 있는 값이 아니라 설정 파일 레벨에서 넣은 값입니다 —
  Easy UI가 기본 제공하는 Provider 선택지는 Kimi(Moonshot)/OpenAI/Gemini/Ollama입니다.
- secret leakage 재검사 occurrence count = 0

### Known limitations

- 무료 LLM Provider·무료 모델의 quota·가용성은 외부 서비스 정책에 따라 변동 가능합니다.
  모델별로 별도 일일 한도가 있을 수 있고, 특정 모델이 갑자기 유료로 바뀌거나 한도가
  소진될 수 있습니다.
- 외부 API(LLM/Pexels/TTS) 장애나 정책 변경은 MPT Easy 코드 문제가 아닐 수 있습니다.
- Finder에서 `MPT Easy.command`를 실제로 물리적으로 더블클릭하는 경로는 이번 검증에서
  터미널 실행(`nohup ./MPT\ Easy.command`)으로 대체 확인했습니다. 최종 실사용 환경에서
  한 번은 직접 더블클릭해 확인하는 것을 권장합니다.
- 영상 길이 프리셋(짧게/보통/길게)은 정확한 초 단위를 보장하지 않습니다.
