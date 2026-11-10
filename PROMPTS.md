# 쇼핑리스트 앱 단계별 개발 프롬프트

> 각 단계의 프롬프트를 순서대로 Claude Code에 붙여넣어 사용하세요.
> 한 단계가 끝나면 `streamlit run app.py`로 직접 확인한 뒤 다음 단계로 넘어가는 것을 권장합니다.

---

## 1단계: 기본 뼈대 작성

```
PRD.md를 읽고, 쇼핑리스트 앱의 기본 뼈대를 만들어줘.

[만들 파일]
- app.py: Streamlit 메인 앱. 제목(🛒 쇼핑리스트)과 빈 리스트 안내 문구("아직 추가된 아이템이 없습니다.")만 표시
- storage.py: 데이터 저장/불러오기 모듈
  - load_items() -> list[dict]: data/shopping_list.json을 읽어 반환. 파일이나 폴더가 없거나 JSON이 깨져 있으면 빈 리스트 반환
  - save_items(items: list[dict]) -> None: 리스트를 JSON 파일로 저장 (ensure_ascii=False, indent=2, 폴더 자동 생성)
  - new_item(name: str, quantity: int = 1) -> dict: PRD 4장의 데이터 모델(id, name, quantity, checked, created_at)에 맞는 아이템 생성
- requirements.txt: streamlit>=1.40
- .gitignore: __pycache__/, .venv/, data/*.json 등
- README.md: 프로젝트 소개, 로컬 실행 방법

[구현 조건]
- 앱 시작 시 st.session_state["items"]가 없으면 load_items()로 초기화
- st.session_state["editing_id"]도 None으로 초기화 (2단계 수정 기능용)
- 이 단계에서는 추가/수정/삭제/체크 기능은 만들지 말 것
- 함수마다 짧은 docstring 작성

완료 후 `streamlit run app.py`로 실행했을 때 에러 없이 뜨는지 확인하고, 만든 파일 목록과 각 역할을 요약해줘.
```

---

## 2단계: 주요 기능 추가

```
PRD.md 3장(기능 요구사항)을 기준으로 app.py에 핵심 기능을 구현해줘. 디자인은 3단계에서 다듬을 거니까 기본 위젯으로 동작에 집중해줘.

[F-01 아이템 추가]
- st.form(clear_on_submit=True) 안에 이름 text_input, 수량 number_input(최소 1, 기본 1), [추가] 버튼
- Enter로도 제출되게
- 이름을 strip() 했을 때 비어 있으면 st.warning으로 경고하고 추가하지 않음
- 이름은 최대 50자 (max_chars=50)
- 새 아이템은 checked=False

[F-02 아이템 수정]
- 각 행의 [수정] 버튼을 누르면 st.session_state["editing_id"]에 해당 id 저장
- 수정 모드인 행은 이름/수량 입력칸 + [저장] [취소] 버튼으로 표시
- 저장 시 빈 이름이면 경고, 아니면 반영 후 editing_id = None
- 취소 시 값 변경 없이 editing_id = None
- 한 번에 하나의 아이템만 수정 모드

[F-03 아이템 삭제]
- 각 행의 [삭제] 버튼으로 해당 아이템만 삭제
- 하단에 [체크된 항목 모두 삭제] 버튼 (체크된 항목이 없으면 disabled)

[F-04 아이템 체크]
- 각 행 맨 앞 체크박스로 checked 토글
- 상단에 "완료 수 / 전체 수 완료" 텍스트와 st.progress 진행 바 표시 (아이템 0개면 0으로 처리, 0으로 나누기 오류 없게)
- 정렬: 미체크 항목이 위, 체크된 항목이 아래 (각 그룹 안에서는 created_at 순)

[F-05 데이터 저장]
- 모든 상태 변경(추가/수정/삭제/체크) 직후 storage.save_items() 호출

[구현 규칙]
- 위젯 key는 반드시 아이템 id를 포함해서 중복 key 오류 방지 (예: f"check_{item['id']}")
- 상태 변경은 on_click / on_change 콜백 함수로 처리하고, 콜백 안에서 id로 아이템을 찾아서 변경 (리스트 인덱스에 의존하지 말 것)
- 추가/수정/삭제/토글 로직은 각각 별도 함수로 분리
- 행 레이아웃은 st.columns로 [체크박스 | 이름 x수량 | 수정 | 삭제]

완료 후 PRD 9장 수용 기준 중 기능 관련 항목을 하나씩 짚으면서 어떻게 구현했는지 설명해줘.
```

---

## 3단계: UI 디자인

```
기능은 그대로 두고 쇼핑리스트 앱의 UI를 다듬어줘. 기존 동작(추가/수정/삭제/체크/저장)이 깨지면 안 돼.

[디자인 요구사항]
- st.set_page_config(page_title="쇼핑리스트", page_icon="🛒", layout="centered")
- .streamlit/config.toml로 테마 설정 (primaryColor는 초록 계열, 깔끔한 밝은 배경)
- 상단: 제목 + 진행 상황("3 / 5 완료")과 진행 바를 한 블록으로 묶어서 보기 좋게
- 입력 영역: 이름 입력칸을 넓게, 수량과 [추가] 버튼은 좁게 한 줄 배치
- 아이템 행:
  - 체크된 아이템은 이름에 취소선 + 회색 글자 (st.markdown의 ~~취소선~~ 또는 CSS 사용)
  - 수량은 "x2"처럼 이름 옆에 작고 흐리게
  - 수정/삭제 버튼은 아이콘(✏️, 🗑️)으로 작게, help 툴팁 추가
  - 각 행을 구분선 또는 st.container(border=True)로 구분
- 빈 리스트일 때 안내 문구를 가운데 정렬하고 이모지와 함께 친근하게
- [체크된 항목 모두 삭제]는 하단에 secondary 스타일로 배치
- 추가/삭제 성공 시 st.toast로 짧은 피드백

[모바일 대응]
- 375px 폭에서도 행의 버튼이 줄바꿈되거나 겹치지 않게 st.columns 비율과 vertical_alignment="center" 조정
- 필요하면 st.markdown(unsafe_allow_html=True)로 최소한의 CSS 추가 (과하게 쓰지 말 것)

[주의]
- 커스텀 CSS는 한 곳(함수 하나)에 모아둘 것
- 사용자 입력(아이템 이름)을 unsafe_allow_html로 출력할 때는 반드시 html.escape() 처리할 것 (XSS 방지)

완료 후 변경한 내용을 항목별로 요약해줘.
```

---

## 4단계: PRD 기준 검토 및 버그 점검 (Playwright 활용)

```
PRD.md를 기준으로 지금까지 만든 쇼핑리스트 앱을 꼼꼼하게 검토해줘. Playwright MCP 도구로 실제 브라우저에서 테스트해야 해.

[준비]
1. 기존 data/shopping_list.json이 있으면 백업(data/shopping_list.backup.json)하고 빈 상태에서 시작
2. `streamlit run app.py --server.headless true --server.port 8501`을 백그라운드로 실행
3. Playwright로 http://localhost:8501 접속 (Streamlit은 렌더링이 비동기이므로 매 동작 후 화면 갱신을 기다릴 것)

[A. 기능 테스트 - PRD 9장 수용 기준]
각 항목마다 실제로 조작하고 결과를 snapshot/screenshot으로 확인:
1. 빈 상태에서 안내 문구 표시
2. "우유"(수량 1), "계란"(수량 2), "식빵"(수량 3) 추가 → 리스트에 표시, 입력창 비워짐
3. Enter 키로 추가 동작
4. 빈 이름 / 공백만 입력 → 추가 안 되고 경고 표시
5. "우유" 수정 → "저지방 우유", 수량 2 로 저장 → 반영 확인
6. 수정 중 취소 → 원래 값 유지
7. "계란" 체크 → 취소선 표시, 아래로 정렬, 진행률 "1 / 3 완료"
8. 체크 해제 → 원래대로 복구
9. "식빵" 삭제 → 해당 항목만 삭제
10. 2개 체크 후 [체크된 항목 모두 삭제] → 체크 항목만 삭제
11. 페이지 새로고침 → 리스트 유지 (data/shopping_list.json 내용도 직접 확인)

[B. 엣지 케이스 / 버그 탐색]
- 같은 이름 아이템 여러 개 추가 후 하나만 수정/삭제/체크 → 다른 항목에 영향 없는지 (id 기반 동작 확인)
- 50자 초과 입력, 이모지/특수문자/한글 입력
- <script>alert(1)</script>, <b>굵게</b> 같은 HTML 입력 → 그대로 텍스트로 보이는지 (XSS)
- 수정 모드 중 다른 아이템 체크/삭제 시 동작
- 수정 중인 아이템을 삭제했을 때 editing_id 처리
- 버튼 빠르게 연속 클릭
- 아이템 0개일 때 진행 바/체크 항목 삭제 버튼 상태
- 아이템 30개 이상일 때 동작 속도
- JSON 파일을 일부러 깨뜨린 뒤 앱 실행 → 앱이 죽지 않는지
- 브라우저 콘솔 에러, Streamlit 에러 메시지(DuplicateWidgetID 등) 확인

[C. UI / 반응형]
- 데스크톱(1280x800)과 모바일(375x667) 해상도로 각각 스크린샷
- 모바일에서 버튼 겹침, 줄바꿈, 가로 스크롤 여부 확인

[D. 코드 리뷰]
- PRD 3장·4장·7장과 코드 비교: 빠진 요구사항, PRD와 다르게 구현된 부분
- 콜백/세션 상태 사용의 문제점, 인덱스 기반 접근 여부
- 예외 처리, 파일 저장 시 데이터 손실 가능성
- 배포 관점: requirements.txt, .gitignore, Streamlit Cloud에서 파일 저장이 초기화되는 한계가 README에 안내되어 있는지

[결과 보고]
REVIEW.md 파일로 정리해줘:
1. 요약 (통과/실패 개수)
2. 수용 기준 체크리스트 (각 항목 ✅/❌ + 근거)
3. 발견한 버그 목록 - 심각도(높음/중간/낮음), 재현 방법, 예상 결과 vs 실제 결과, 원인 코드 위치(파일:줄), 수정 제안
4. PRD와 다른 부분
5. 개선 제안
6. 스크린샷 파일 경로

[주의]
- 이 단계에서는 코드를 수정하지 말고 검토·보고만 할 것 (수정은 보고서를 보고 따로 요청할게)
- 테스트가 끝나면 streamlit 서버를 종료하고, 백업해둔 데이터 파일을 원래대로 복구할 것
```

---

## (선택) 5단계: 버그 수정 후 재검증

```
REVIEW.md에서 심각도 "높음"과 "중간" 버그를 모두 수정해줘.
수정한 버그마다 Playwright로 같은 재현 방법을 다시 실행해서 해결됐는지 확인하고,
REVIEW.md에 "수정 결과" 섹션을 추가해 정리해줘.
```
