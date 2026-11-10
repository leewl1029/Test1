"""쇼핑리스트 데이터 저장/불러오기 모듈.

모든 세션이 같은 JSON 파일을 공유한다. 여러 탭·기기에서 동시에 써도 서로의 변경을
덮어쓰지 않도록, 변경은 항상 `update_items()`로 "잠금 → 파일 읽기 → 변경 → 저장" 순서로 한다.
"""

import json
import shutil
import threading
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "shopping_list.json"

# Streamlit은 모든 세션을 한 프로세스의 스레드로 실행하므로 스레드 잠금으로 충분하다.
_LOCK = threading.RLock()


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _backup(reason: str, move: bool) -> Path:
    """현재 데이터 파일을 백업 이름으로 옮기거나(move) 복사한다."""
    backup = DATA_FILE.with_name(f"{DATA_FILE.stem}.{reason}-{_timestamp()}.json")
    if move:
        DATA_FILE.replace(backup)
    else:
        shutil.copy2(DATA_FILE, backup)
    return backup


def _normalize(raw: object) -> dict | None:
    """저장된 항목 하나를 검사해 올바른 아이템으로 만든다. 살릴 수 없으면 None."""
    if not isinstance(raw, dict):
        return None
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    quantity = raw.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        quantity = 1
    item_id = raw.get("id")
    created_at = raw.get("created_at")
    return {
        "id": item_id if isinstance(item_id, str) and item_id else str(uuid.uuid4()),
        "name": name.strip(),
        "quantity": quantity,
        "checked": raw.get("checked") is True,
        "created_at": created_at if isinstance(created_at, str) else "",
    }


def load_items_with_warnings() -> tuple[list[dict], list[str]]:
    """아이템 목록과, 사용자에게 알려야 할 경고 목록을 반환한다.

    - 파일이 없으면 빈 리스트.
    - JSON이 깨졌거나 리스트가 아니면 파일을 백업 이름으로 옮기고 빈 리스트로 시작한다.
    - 형식이 잘못된 항목은 건너뛰되, 원본 파일을 먼저 복사해 둔다.
    """
    with _LOCK:
        try:
            with DATA_FILE.open(encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return [], []
        except (json.JSONDecodeError, UnicodeDecodeError):
            backup = _backup("corrupt", move=True)
            return [], [f"저장 파일이 손상되어 `{backup.name}`(으)로 옮겨 두고 빈 리스트로 시작합니다."]

        if not isinstance(data, list):
            backup = _backup("corrupt", move=True)
            return [], [f"저장 파일 형식이 올바르지 않아 `{backup.name}`(으)로 옮겨 두고 빈 리스트로 시작합니다."]

        items = [item for item in map(_normalize, data) if item is not None]
        skipped = len(data) - len(items)
        if skipped:
            backup = _backup("invalid", move=False)
            save_items(items)  # 정리한 목록을 바로 저장해, 다음 로드에서 백업이 또 생기지 않게 한다.
            return items,[f"형식이 잘못된 항목 {skipped}개를 건너뛰었습니다. 원본은 `{backup.name}`에 보관했습니다."]
        return items, []


def load_items() -> list[dict]:
    """아이템 목록을 반환한다 (경고는 버린다)."""
    return load_items_with_warnings()[0]


def save_items(items: list[dict]) -> None:
    """아이템 목록을 JSON 파일로 저장한다. 폴더가 없으면 만든다."""
    with _LOCK:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        # 임시 파일에 먼저 쓰고 교체해서, 저장 도중 실패해도 기존 파일이 깨지지 않게 한다.
        tmp_file = DATA_FILE.with_name(f".{DATA_FILE.name}.{uuid.uuid4().hex}.tmp")
        try:
            with tmp_file.open("w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            tmp_file.replace(DATA_FILE)
        finally:
            tmp_file.unlink(missing_ok=True)


def update_items(change: Callable[[list[dict]], None]) -> list[str]:
    """파일의 최신 목록을 읽어 `change(items)`로 그 자리에서 고친 뒤 저장한다.

    다른 세션이 그 사이에 바꾼 내용을 덮어쓰지 않기 위해, 변경은 항상 이 함수로 한다.
    불러오면서 생긴 경고 목록을 반환한다.
    """
    with _LOCK:
        items, warnings = load_items_with_warnings()
        change(items)
        save_items(items)
        return warnings


def new_item(name: str, quantity: int = 1) -> dict:
    """PRD 4장 데이터 모델에 맞는 새 아이템을 만든다."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "quantity": quantity,
        "checked": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
