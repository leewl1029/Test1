# 🛒 쇼핑리스트

아이템을 추가·수정·삭제·체크할 수 있는 간단한 쇼핑리스트 웹 앱입니다. Python과 Streamlit으로 만들었습니다.

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 http://localhost:8501 로 접속합니다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `app.py` | Streamlit 화면 |
| `storage.py` | 데이터 저장/불러오기 (`data/shopping_list.json`) |
| `PRD.md` | 요구사항 문서 |

## 비밀번호 설정

리스트는 서버의 파일 하나를 모든 접속자가 함께 씁니다. 배포할 때는 반드시 비밀번호를 설정하세요.

- **로컬:** `.streamlit/secrets.toml`에 아래 내용을 넣습니다. 이 파일은 git에 올라가지 않습니다.
  ```toml
  APP_PASSWORD = "원하는 비밀번호"
  ```
- **Streamlit Community Cloud:** 앱 설정 → **Secrets**에 같은 내용을 붙여넣습니다.

`APP_PASSWORD`가 없으면 비밀번호 없이 열립니다(로컬 개발용).

## Streamlit Community Cloud 배포

1. 이 폴더를 GitHub 저장소에 push합니다.
2. https://share.streamlit.io 에 GitHub 계정으로 로그인합니다.
3. **Create app** → 저장소, 브랜치(`main`), 메인 파일(`app.py`)을 선택합니다.
4. **Advanced settings → Secrets**에 `APP_PASSWORD = "..."`를 입력하고 **Deploy**를 누릅니다.
5. 이후 `main`에 push하면 자동으로 다시 배포됩니다.

## 알아둘 점

- **데이터 초기화:** Streamlit Community Cloud에서는 앱이 다시 시작되거나 재배포될 때 `data/shopping_list.json`이 초기화될 수 있습니다. 데이터를 계속 보관하려면 외부 저장소(Google Sheets, Supabase 등)로 바꿔야 합니다.
- **여러 기기 동시 사용:** 여러 탭·기기에서 동시에 써도 서로의 변경을 덮어쓰지 않습니다. 다른 기기에서 바꾼 내용은 5초 안에 화면에 반영됩니다.
- **저장 파일 손상:** 저장 파일이 손상되면 `data/shopping_list.corrupt-<시각>.json`으로 옮겨 두고 화면에 알립니다.
