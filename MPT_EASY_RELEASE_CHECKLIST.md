# MPT Easy v0.1.0 Release Checklist

## 완료

- [x] main/origin SHA 일치 (`bbedc5147b706823524fa7d9cdcc6f7e8d232aa4`, ahead 0 / behind 0)
- [x] 애플리케이션 코드(`app/`, `webui/`, launcher) working tree clean
- [x] compileall (`python -m compileall app cli.py main.py webui test`)
- [x] ruff (`ruff check app cli.py main.py webui test`)
- [x] pytest (653 passed / 11 skipped / 실패 0)
- [x] FULL E2E (LLM script/video_terms 자동 생성 → Pexels → TTS → 자막 → 합성, 사전 주입 없음)
- [x] secret scan (occurrence count = 0)
- [x] config.toml 미포함 (원격 커밋 이력에 없음)
- [x] launcher smoke (Mac `.command`, `.venv` python 사용, 포트 자동 회피 확인)
- [x] README 감사 (`MPT_EASY_README.md` — 10단계 흐름, provider 편향 표현 제거)
- [x] CHANGELOG 감사 (`MPT_EASY_CHANGELOG.md` — 사실 근거, 특정 provider 이름 일반화)
- [x] Release Notes 감사 (`MPT_EASY_RELEASE_NOTES_v0.1.0.md` — 원본 프로젝트 관계 명시)
- [x] 문서 4개 민감정보·개인 경로 스캔 (매칭 0건)

## 아직

- [ ] 릴리스 문서 최종 사용자 승인
- [ ] 릴리스 문서 commit
- [ ] origin/main push
- [ ] v0.1.0 tag
- [ ] GitHub Release 생성
