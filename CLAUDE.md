# goma

An unofficial async Python client and CLI for goma.gg shopping lists. It is built to feed BilkaToGo carts through [nickknissen/bilkatogo](https://github.com/nickknissen/bilkatogo), and a Home Assistant integration that does so is planned. Follow bilkatogo's conventions: httpx, a `TokenStorage`, typed frozen dataclasses, an error hierarchy and a typer CLI behind the `cli` extra.

The repo will be public later. Keep sessions, personal data and real list contents out of git and out of test fixtures.

## Commands

```sh
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

CI runs on Python 3.12 and 3.14. On this box, uv's default cache and Python directories sit on a full mergerfs pool, so use local paths:

```sh
export UV_CACHE_DIR=$HOME/.local/tmp/uv-cache UV_LINK_MODE=copy UV_PYTHON_INSTALL_DIR=$HOME/.local/python
```

## goma's API

These calls were observed from goma.gg's own website on 2026-10-28.

- **Backend:** Supabase at `https://api.goma.gg`. Every call sends `apikey: <API_KEY>` (see `const.py`), which is the public publishable key the website uses. Authenticated calls also send `Authorization: Bearer <access_token>`.
- **Bot protection:** goma.gg's HTML answers plain HTTP clients with 429. `api.goma.gg` does not, so no browser is needed.
- **Login:** goma offers Google, Apple and an email code, and only the email code can be automated.
  - `POST /auth/v1/otp` sends the code.
  - `POST /auth/v1/verify` with `{"type": "email"}` redeems it.
  - `POST /auth/v1/token?grant_type=refresh_token` renews the session. The refresh token rotates on every renewal, so always store the new one.
- **Lists:** `shopping_lists` holds the lists. Lists belong to a group (`group_id`). The primary list is `user_preferences.primary_shopping_list_id`.
- **Items:** `shopping_list_items` holds the items.
  - An item with `is_hidden = true` has been removed from the list, and the website never shows it.
  - `is_picked` means the item is ticked off.
  - `quantity` is a float.
- **Products:** `product_search_view` holds product details, keyed by `product_id`.
- **Bilka mapping:** `bilka-<n>` is BilkaToGo Article Number `<n>`. This was verified for 8 of 8 real products against bilkatogo.dk product pages.

## Open questions

- It is not yet known whether a list shared by another goma account shows up in `shopping_lists`. Row-level security suggests it does.
- The bilkatogo README warns that logging in to the Bilka app or website can restore an older cart. Test this before the HA integration relies on cart changes.
