# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Streamlit shopping-list web app (add / edit / delete / check items) for Streamlit Community Cloud. User-facing text and docs are in Korean.

- `PRD.md` is the source of truth for requirements: features F-01–F-05, the data model, and acceptance criteria in §9.
- `PROMPTS.md` is the staged build plan. Stages 1–5 are done.
- `REVIEW.md` is the Playwright review report. All findings (H1–L9) are fixed, and each fix notes how it was re-verified. Use its scenarios as the regression checklist.

## Commands

```bash
pip install -r requirements.txt
python -m streamlit run app.py                     # `streamlit` is not on PATH on this machine
python -m streamlit run app.py --server.headless true --server.port 8502   # for Playwright tests
```

There is no test suite or linter. Verification is done in two ways.

**Headless check with AppTest**, run from the project root:
```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py").run()
at.text_input(key="new_name").input("우유")
next(b for b in at.button if b.label == "추가").click().run()   # don't use at.button[0]: the 확인 button of a load warning can come first
assert not at.exception
```
Per-item widgets have keys you can target: `edit_{id}`, `del_{id}`, `check_{id}_{0|1}`, `edit_name_{id}`, `edit_qty_{id}`, `save_{id}`, `cancel_{id}`.

**Real browser via the Playwright MCP:**
- Use port 8502 and leave the user's own server on 8501 alone.
- Back up `data/shopping_list.json` before the test and restore it afterwards.
- Save screenshots under `review-screens/`, which is gitignored. The MCP can only write inside the project directory.
- Streamlit renders asynchronously. After each action, wait until `[data-testid="stStatusWidget"]` is gone before asserting.

## Architecture

All sessions (tabs, devices, users) share one JSON file, `data/shopping_list.json`. The design centers on never losing another session's changes.

- **The item list is never cached in `st.session_state`.**
  - `app.py` re-reads the file on every run.
  - Every mutation goes through `change_items(fn)` → `storage.update_items(fn)`. That function holds a process-wide `RLock` while it reads the latest file, applies `fn(items)` in place, and saves through a uniquely named temp file plus `replace`.
  - Never save a list that was read earlier in the run. Doing so brings back the cross-tab overwrite bug (REVIEW.md H1).
- **Syncing changes from other sessions:** `watch_for_changes()` is an `st.fragment(run_every=5)`. It compares the file mtime with `seen_mtime` and triggers a full rerun when the data changed. It pauses while an item is in edit mode.
- **Session state** holds UI state only: `editing_id`, `add_error`/`edit_error`, `load_warnings`, `seen_mtime`, `authenticated`, and widget values.
- **Loading data** (`storage.load_items_with_warnings()`):
  - A corrupt or non-list file is moved to `shopping_list.corrupt-<ts>.json`.
  - Malformed items are normalized or dropped. If any are dropped, the original is copied to `shopping_list.invalid-<ts>.json` and the cleaned list is saved right away, so the backup isn't recreated on every rerun.
  - Warnings are shown in the UI. Never silently return `[]`: the next save would wipe the user's data.
- **Access control:** if `APP_PASSWORD` is set in `st.secrets`, `check_password()` gates the app. Locally that's `.streamlit/secrets.toml` (gitignored); on Streamlit Cloud it's the Secrets setting. Without it the app is open, which is meant for local dev only. Streamlit caches secrets, so restart the server after adding or removing `secrets.toml`.
- **Item schema:** `{id (uuid4 str), name (1–50 chars), quantity (int 1–999), checked (bool), created_at (ISO 8601)}`.
- **Display order:** unchecked items first, then checked, each group sorted by `created_at`.

### Conventions that matter for correctness

- Change data only in `on_click`/`on_change` callbacks. Find items **by `id`, never by list index**.
- Every per-item widget key includes the item id. The checkbox key also includes the checked state, so the checkbox re-syncs when another device toggles the item.
- Validate name length and quantity in the callbacks with `validation_error()`, not with widget limits:
  - `number_input(min_value=...)` blocks form submission without any visible message.
  - `text_input(max_chars=...)` drops an over-long paste entirely.
- Use only public layout APIs: `st.container(horizontal=True)` and `width=`.
  - CSS in `inject_css()` targets only classes the app emits itself, never Streamlit internals such as `data-testid` or `st-key-*`.
  - `.item-label { width: 0; min-width: 100% }` keeps a long name from pushing the row's buttons onto a new line on narrow screens.
- The add form and the edit row are `st.form`s. In the edit form, [저장] is the first submit button so that Enter saves.
- User text rendered as HTML (`st.html` in `item_label_html`) must go through `html.escape()`.

## Deployment

- Deployment steps are in `README.md`. Set `APP_PASSWORD` in Cloud Secrets before sharing the URL.
- `requirements.txt` pins `streamlit>=1.67,<2` because the horizontal container and `width=` APIs need a recent version.
- Streamlit Community Cloud may wipe the filesystem on restart or redeploy, so the JSON file is not durable storage. That's accepted for the MVP. Durable storage (Google Sheets or Supabase via `st.secrets`) is planned for v2.
