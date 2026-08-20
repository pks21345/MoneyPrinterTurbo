# MPT Easy v0.1

MoneyPrinterTurbo 위에 얹은 한국어 초보자용 Easy UI입니다. 기존 MoneyPrinterTurbo의
고급 기능·엔진은 그대로 두고, 화면만 별도로 추가했습니다.

## 기존 MoneyPrinterTurbo와의 관계

- 엔진은 재구현하지 않았습니다. Easy 화면에서 만든 설정은 그대로
  `app.services.webui_task.submit_generation()`을 거쳐 기존 생성 파이프라인으로 들어갑니다.
- 기존 고급 화면(`webui/Main.py`, 실행 파일 `webui.sh`/`webui.bat`)은 전혀 수정되지 않았습니다.
  세밀한 옵션이 필요하면 그쪽을 계속 쓰면 됩니다.
- Easy 쪽 코드는 전부 `webui/easy/`에 신규로만 추가됐습니다. 기존 파일 수정 0건입니다.

## 실행 방법

**Mac**: Finder에서 `MPT Easy.command`를 더블클릭합니다.

**Windows**: `easy_webui.bat`를 실행합니다.

**Linux / macOS 터미널**:
```bash
sh easy_webui.sh
```

세 실행 파일 모두 프로젝트 `.venv` Python을 우선 사용하고, 없으면 `uv`, 그다음 PATH의
`streamlit` 순으로 찾습니다. 기본 포트는 8501이며 사용 중이면 8502~8599 중 빈 포트를
자동으로 씁니다.

## 필요한 API

첫 실행 시 화면 안에서 "처음 설정 / API 연결"을 펼쳐 아래 두 가지를 넣으면 됩니다.
기존 `config.toml`에 그대로 저장되며, MPT Easy가 별도 비밀 저장소를 만들지 않습니다.

- **LLM Provider**: Kimi(Moonshot)/OpenAI/Gemini/Ollama 중 선택. Ollama는 API Key 없이
  로컬 모델 이름만 입력하면 됩니다. 이미 저장된 Key는 화면에 다시 표시되지 않습니다.
  무료 요금제·무료 사용량을 제공하는 Provider도 있지만, 한도·가격 정책은 각 서비스가
  자체적으로 바꿀 수 있으니 최신 정보는 해당 Provider 공식 페이지에서 확인하세요.
- **Pexels**: 영상 소재(스톡 영상) 검색에 필요합니다.
- **음성(TTS)**: 기본으로 노출되는 한국어 음성 3종(`ko-KR-SunHiNeural` 등)은 Edge 계열이라
  **별도 API Key가 필요 없습니다.**

## 첫 영상 만드는 순서

1. 설치된 MoneyPrinterTurbo 폴더를 엽니다.
2. `MPT Easy.command`(또는 해당 OS 실행 파일)를 실행합니다.
3. 브라우저가 열리면 "처음 설정 / API 연결"을 펼칩니다.
4. LLM Provider를 하나 고르고 API Key를 입력합니다(Ollama는 Key 없이 모델 이름만).
5. Pexels API Key를 입력합니다.
6. "저장 후 연결 확인"을 눌러 두 연결이 정상인지 확인합니다.
7. 영상 주제를 한 문장 입력합니다.
8. 콘텐츠 유형(정보형 쇼츠 / 꿀팁·리스트 / 자유 제작)과 영상 길이(짧게/보통/길게)를 고릅니다.
9. 음성을 고르고, 필요하면 "고급 설정"에서 화면비율(9:16/16:9/1:1)을 바꿉니다.
10. "영상 만들기"를 누르면 실제 task가 제출되고, 화면에 실제 진행률(문안 생성 → 검색어 구성
    → 음성 생성 → 자막 생성 → 영상 소재 준비 → 영상 합성)이 표시됩니다. 완료되면 미리보기와
    MP4 다운로드 버튼이 뜹니다.

길이 선택은 정확한 초 단위를 보장하지 않습니다 — `video_clip_duration`/`paragraph_number`
안전 프로필로만 매핑됩니다.

## 보안 — config.toml을 절대 Git에 올리지 마세요

`config.toml`에는 입력한 API Key가 평문으로 저장됩니다. 이 프로젝트의 `.gitignore`가
`config.toml`을 이미 제외하고 있지만, `git add -A` 같은 명령을 쓰기 전에 반드시
`git status`로 `config.toml`이 스테이징되지 않았는지 확인하세요. Easy 화면은 저장된
Key를 다시 평문으로 보여주지 않으며, 오류 메시지도 마스킹해서 표시합니다.

## 문제가 생기면

Easy 화면에서 뭔가 막히면 기존 고급 WebUI(`webui/Main.py`, `webui.sh`/`webui.bat`)에서
같은 작업 상태와 더 많은 옵션을 확인할 수 있습니다. 두 화면은 같은 task 엔진을 공유합니다.
