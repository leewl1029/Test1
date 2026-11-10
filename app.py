"""쇼핑리스트 Streamlit 메인 앱."""

import hmac
import html

import streamlit as st

import storage

MAX_NAME_LEN = 50
MIN_QTY = 1
MAX_QTY = 999
WATCH_SECONDS = 5  # 다른 탭·기기의 변경을 확인하는 주기


# ---------- 상태 ----------

def init_state() -> None:
    """세션 상태를 처음 한 번만 초기화한다. 아이템 목록은 세션에 담지 않고 매번 파일에서 읽는다."""
    defaults = {
        "editing_id": None,
        "add_error": None,
        "edit_error": None,
        "load_warnings": [],
        "seen_mtime": None,
        "new_name": "",
        "new_qty": 1,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _remember_warnings(warnings: list[str]) -> None:
    for w in warnings:
        if w not in st.session_state["load_warnings"]:
            st.session_state["load_warnings"].append(w)


def load_items() -> list[dict]:
    """파일에서 최신 아이템 목록을 읽는다."""
    items, warnings = storage.load_items_with_warnings()
    _remember_warnings(warnings)
    return items


def change_items(change) -> None:
    """파일의 최신 목록에 변경을 적용하고 저장한다 (다른 세션의 변경을 덮어쓰지 않는다)."""
    _remember_warnings(storage.update_items(change))


def data_mtime() -> float | None:
    try:
        return storage.DATA_FILE.stat().st_mtime
    except FileNotFoundError:
        return None


def validation_error(name: str, quantity: int) -> str | None:
    """이름(앞뒤 공백 제거 후)과 수량을 검사해, 문제가 있으면 경고 문구를 반환한다.

    입력칸에 max_chars/min_value를 쓰지 않고 여기서 검사한다. 위젯 제한은 길게 붙여넣은
    글자를 통째로 버리거나 폼 제출을 말없이 막기 때문이다 (REVIEW.md M1, L1).
    """
    if not name:
        return "아이템 이름을 입력해 주세요."
    if len(name) > MAX_NAME_LEN:
        return f"이름은 {MAX_NAME_LEN}자 이하로 입력해 주세요. (지금 {len(name)}자)"
    if not MIN_QTY <= quantity <= MAX_QTY:
        return f"수량은 {MIN_QTY}~{MAX_QTY} 사이로 입력해 주세요."
    return None


# ---------- 콜백 (상태 변경) ----------

def add_item() -> None:
    """F-01: 입력 폼의 값으로 아이템을 추가한다. 실패하면 입력값을 그대로 둔다."""
    name = st.session_state["new_name"].strip()
    quantity = int(st.session_state["new_qty"])
    if error := validation_error(name, quantity):
        st.session_state["add_error"] = error
        return
    st.session_state["add_error"] = None
    change_items(lambda items: items.append(storage.new_item(name, quantity)))
    st.session_state["new_name"] = ""
    st.session_state["new_qty"] = 1
    st.toast("아이템을 추가했어요", icon="🛒")


def start_edit(item_id: str) -> None:
    """F-02: 아이템을 수정 모드로 바꾸고 입력칸에 현재 값을 채운다."""
    item = next((i for i in load_items() if i["id"] == item_id), None)
    if item is None:
        st.toast("다른 곳에서 삭제된 아이템이에요", icon="⚠️")
        return
    st.session_state["editing_id"] = item_id
    st.session_state["edit_error"] = None
    st.session_state[f"edit_name_{item_id}"] = item["name"]
    st.session_state[f"edit_qty_{item_id}"] = item["quantity"]


def save_edit(item_id: str) -> None:
    """F-02: 수정한 값을 저장한다. 검사에 실패하면 저장하지 않고 수정 모드를 유지한다."""
    name = st.session_state[f"edit_name_{item_id}"].strip()
    quantity = int(st.session_state[f"edit_qty_{item_id}"])
    if error := validation_error(name, quantity):
        st.session_state["edit_error"] = error
        return

    found = False

    def apply(items: list[dict]) -> None:
        nonlocal found
        for item in items:
            if item["id"] == item_id:
                item["name"] = name
                item["quantity"] = quantity
                found = True

    change_items(apply)
    cancel_edit()
    if not found:
        st.toast("다른 곳에서 삭제된 아이템이라 저장하지 못했어요", icon="⚠️")


def cancel_edit() -> None:
    """F-02: 값을 바꾸지 않고 수정 모드를 끝낸다."""
    st.session_state["editing_id"] = None
    st.session_state["edit_error"] = None


def delete_item(item_id: str) -> None:
    """F-03: 아이템 하나를 삭제한다."""
    change_items(lambda items: items.__setitem__(slice(None), [i for i in items if i["id"] != item_id]))
    if st.session_state["editing_id"] == item_id:
        cancel_edit()
    st.toast("아이템을 삭제했어요", icon="🗑️")


def delete_checked() -> None:
    """F-03: 체크된 아이템을 모두 삭제한다."""
    removed = 0

    def apply(items: list[dict]) -> None:
        nonlocal removed
        removed = sum(1 for i in items if i["checked"])
        items[:] = [i for i in items if not i["checked"]]

    change_items(apply)
    st.toast(f"완료한 아이템 {removed}개를 정리했어요", icon="🧹")


def toggle_item(item_id: str, widget_key: str) -> None:
    """F-04: 체크박스 값으로 아이템의 체크 상태를 바꾼다."""
    checked = bool(st.session_state[widget_key])

    def apply(items: list[dict]) -> None:
        for item in items:
            if item["id"] == item_id:
                item["checked"] = checked

    change_items(apply)


def dismiss_warnings() -> None:
    st.session_state["load_warnings"] = []


# ---------- 접근 제한 ----------

def configured_password() -> str | None:
    """st.secrets의 APP_PASSWORD. 설정되지 않았으면 None (로컬 개발용)."""
    try:
        password = st.secrets.get("APP_PASSWORD")
    except Exception:  # secrets.toml이 아예 없을 때
        return None
    return str(password) if password else None


def check_password() -> bool:
    """APP_PASSWORD가 설정돼 있으면 비밀번호를 맞혀야 앱을 보여준다."""
    expected = configured_password()
    if expected is None or st.session_state.get("authenticated"):
        return True

    st.title("🛒 쇼핑리스트")
    with st.form("login_form"):
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("들어가기", type="primary")
    if submitted:
        if hmac.compare_digest(password.encode(), expected.encode()):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("비밀번호가 맞지 않습니다.")
    return False


# ---------- 화면 ----------

def inject_css() -> None:
    """앱 전체에 쓰는 커스텀 CSS를 한 곳에서 넣는다.

    레이아웃은 Streamlit 공식 API(가로 컨테이너, width)로만 잡는다. 여기 CSS는 이 앱이 직접 만든
    HTML 클래스에만 적용하고, Streamlit 내부 구조(data-testid 등)에는 의존하지 않는다 (REVIEW.md L8).
    """
    st.html(
        """
        <style>
        /* 내용 길이를 0으로 알려서, 긴 이름도 가로 컨테이너에서 줄을 넘기지 않고 남는 공간 안에서 줄바꿈 */
        .item-label { width: 0; min-width: 100%; }
        .item-name { font-size: 1rem; line-height: 1.4; overflow-wrap: anywhere; }
        .item-name.checked { text-decoration: line-through; color: #9AA5A0; }
        .item-qty { font-size: 0.85rem; color: #8A948F; margin-left: 0.4rem; white-space: nowrap; }
        .empty-state { text-align: center; color: #6B7670; padding: 2rem 0 1rem; }
        .empty-state .emoji { font-size: 2.5rem; display: block; margin-bottom: 0.5rem; }
        </style>
        """
    )


@st.fragment(run_every=WATCH_SECONDS)
def watch_for_changes() -> None:
    """다른 탭·기기에서 데이터가 바뀌면 화면을 새로 그린다. 수정 중일 때는 기다린다."""
    if st.session_state["editing_id"] is None and data_mtime() != st.session_state["seen_mtime"]:
        st.rerun(scope="app")


def render_load_warnings() -> None:
    """저장 파일을 불러오며 생긴 문제를 알린다."""
    if not st.session_state["load_warnings"]:
        return
    with st.container(border=True):
        for message in st.session_state["load_warnings"]:
            st.warning(message, icon="⚠️")
        st.button("확인", key="dismiss_warnings", on_click=dismiss_warnings)


def render_header(items: list[dict]) -> None:
    """제목과 진행 상황."""
    total = len(items)
    done = sum(1 for i in items if i["checked"])
    st.title("🛒 쇼핑리스트")
    with st.container(border=True, key="summary"):
        st.progress(done / total if total else 0.0, text=f"**{done} / {total} 완료**")
        if total == 0:
            st.caption("살 물건을 추가해 보세요.")
        elif done == total:
            st.caption("🎉 모두 담았어요!")
        else:
            st.caption(f"남은 아이템 {total - done}개")


def render_add_form() -> None:
    """아이템 추가 폼. 이름 길이·수량은 콜백에서 검사해 한국어로 안내한다."""
    with st.form("add_form", border=False):
        with st.container(horizontal=True, vertical_alignment="bottom", gap="small"):
            st.text_input("아이템 이름", key="new_name", placeholder="예: 우유", width="stretch")
            st.number_input("수량", key="new_qty", step=1, width=100)
            st.form_submit_button("추가", on_click=add_item, type="primary", width="content")
    if st.session_state["add_error"]:
        st.warning(st.session_state["add_error"], icon="⚠️")
        st.session_state["add_error"] = None


def item_label_html(item: dict) -> str:
    """아이템 이름·수량 HTML. 사용자 입력은 반드시 escape한다."""
    css_class = "item-name checked" if item["checked"] else "item-name"
    return (
        f'<div class="item-label"><span class="{css_class}">{html.escape(item["name"])}</span>'
        f'<span class="item-qty">x{int(item["quantity"])}</span></div>'
    )


def render_item_row(item: dict) -> None:
    """아이템 한 줄 (보기 모드). 가로 컨테이너라 좁은 화면에서도 한 줄로 유지된다."""
    item_id = item["id"]
    # 체크 상태를 key에 넣어, 다른 기기에서 체크가 바뀌면 체크박스도 새 값으로 다시 만든다.
    check_key = f"check_{item_id}_{int(item['checked'])}"
    # 다른 아이템을 수정하는 중이면 수정 버튼을 막아, 입력하던 내용이 사라지지 않게 한다 (L4).
    editing_other = st.session_state["editing_id"] is not None
    with st.container(
        border=True, horizontal=True, vertical_alignment="center", gap="small", key=f"row_{item_id}"
    ):
        st.checkbox(
            item["name"],
            value=item["checked"],
            key=check_key,
            on_change=toggle_item,
            args=(item_id, check_key),
            label_visibility="collapsed",
            width="content",
        )
        st.html(item_label_html(item), width="stretch")
        # 글자 라벨을 둬서 화면 읽기 프로그램이 "수정"/"삭제"로 읽게 한다 (L5).
        st.button(
            "수정", icon=":material/edit:", key=f"edit_{item_id}", on_click=start_edit,
            args=(item_id,), type="tertiary", width="content", disabled=editing_other,
            help="수정 중인 아이템을 먼저 저장하거나 취소하세요." if editing_other else None,
        )
        st.button(
            "삭제", icon=":material/delete:", key=f"del_{item_id}", on_click=delete_item,
            args=(item_id,), type="tertiary", width="content",
        )


def render_edit_row(item: dict) -> None:
    """아이템 한 줄 (수정 모드). 폼이라 이름 칸에서 Enter를 누르면 저장된다 (L3)."""
    item_id = item["id"]
    with st.container(border=True, key=f"edit_box_{item_id}"):
        with st.form(f"edit_form_{item_id}", border=False):
            st.text_input("이름 수정", key=f"edit_name_{item_id}")
            with st.container(horizontal=True, vertical_alignment="bottom", gap="small"):
                st.number_input("수량 수정", key=f"edit_qty_{item_id}", step=1, width="stretch")
                # 폼에서 Enter는 첫 번째 제출 버튼을 누른 것과 같으므로 저장을 먼저 둔다.
                st.form_submit_button(
                    "저장", key=f"save_{item_id}", on_click=save_edit, args=(item_id,),
                    type="primary", width="content",
                )
                st.form_submit_button(
                    "취소", key=f"cancel_{item_id}", on_click=cancel_edit, width="content"
                )
        if st.session_state["edit_error"]:
            st.warning(st.session_state["edit_error"], icon="⚠️")


def render_empty_state() -> None:
    """리스트가 비었을 때 안내."""
    st.html(
        '<div class="empty-state"><span class="emoji">🧺</span>'
        "아직 추가된 아이템이 없습니다.<br>위에서 살 물건을 추가해 보세요!</div>"
    )


def main() -> None:
    """앱 화면을 그린다."""
    st.set_page_config(page_title="쇼핑리스트", page_icon="🛒", layout="centered")
    inject_css()
    init_state()
    if not check_password():
        return

    # 화면을 그릴 때마다 파일에서 최신 목록을 읽는다 (다른 탭·기기의 변경 반영).
    st.session_state["seen_mtime"] = data_mtime()
    items = load_items()
    if st.session_state["editing_id"] not in {i["id"] for i in items}:
        cancel_edit()  # 수정 중인 아이템이 다른 곳에서 삭제된 경우

    watch_for_changes()
    render_header(items)
    render_load_warnings()
    render_add_form()

    if not items:
        render_empty_state()
        return

    # 미체크 항목이 위, 체크된 항목이 아래. 각 그룹 안에서는 추가된 순서.
    for item in sorted(items, key=lambda i: (i["checked"], i["created_at"])):
        if item["id"] == st.session_state["editing_id"]:
            render_edit_row(item)
        else:
            render_item_row(item)

    st.button(
        "✔ 체크된 항목 모두 삭제",
        on_click=delete_checked,
        disabled=not any(i["checked"] for i in items),
        type="secondary",
        width="stretch",
    )


main()
