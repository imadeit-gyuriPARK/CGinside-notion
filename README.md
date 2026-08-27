# notion 회의 제목 자동 정리

노션 회의 DB의 페이지 제목을, 정해둔 규칙에 맞게 자동으로 덮어쓰는 도구.
매번 손으로 제목 타이핑하는 걸 없애기 위한 것.

## 이게 어떻게 "알아서" 돌아가나 (요약)

1. 이 폴더를 GitHub 저장소(repo)로 올린다.
2. `.github/workflows/notion-meeting-titles.yml` 파일이 GitHub에게 "매일 09:00(KST)에 `python rename.py --apply` 실행해라"라고 알려준다.
3. 정해진 시간이 되면 **GitHub의 서버**가 알아서 이 repo를 내려받아 스크립트를 돌리고 꺼진다. 내 PC는 꺼져 있어도 됨.
4. 스크립트는 `NOTION_TOKEN`(GitHub repo의 Secret에 저장, 코드에는 안 들어감)으로 노션에 접속해 제목을 고친다.

> **LLM/AI 안 씀.** 노션 속성 값을 규칙대로 이어붙이는 문자열 작업이라 API 키도, 요금도 없다.
> (Claude/LLM은 지금 이 코드를 *만드는* 데만 쓰였고, 돌아갈 때는 관여하지 않는다.)

## 로컬에서 먼저 테스트

```bash
python -m venv .venv
.venv\Scripts\activate            # (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env             # 그리고 .env 에 토큰/DB ID 채우기

python rename.py --show-props      # DB 속성 이름/값 확인 (제목 규칙 설계용)
python rename.py                   # 미리보기: "지금 제목 -> 바뀔 제목"
python rename.py --apply           # 실제로 덮어쓰기
```

## 노션 integration 만들기

1. https://www.notion.so/my-integrations → **New integration**
2. 이름 아무거나, 워크스페이스 선택
3. Capabilities: **Read content** + **Update content** 체크
4. **Internal Integration Secret**(`ntn_...`) 복사 → `.env` 의 `NOTION_TOKEN`
5. 회의 DB 페이지 열기 → 우측 상단 `···` → **Connections** → 방금 만든 integration 추가
   (이 단계 빠지면 스크립트가 DB를 못 읽음)

## GitHub Actions로 자동화 켜기

1. 이 repo를 GitHub에 push
2. repo → **Settings → Secrets and variables → Actions → New repository secret**
   - `NOTION_TOKEN` = integration 토큰
   - `NOTION_DATABASE_ID` = DB ID
3. 끝. 스케줄대로 자동 실행. repo → **Actions** 탭에서 실행 기록/로그 확인.
   즉시 돌려보려면 Actions 탭에서 **Run workflow**.

## 제목 규칙 바꾸기

`rename.py` 의 `build_title()` 함수 하나만 고치면 된다.
