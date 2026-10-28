# goma

Read your [goma.gg](https://goma.gg) shopping lists from Python or the terminal. goma plans your meals from this week's offers and builds the shopping list. This package gives you that list as data: each item with its quantity, goma's product details, and the store's own product number where goma has one.

```console
$ goma items
[ ] 1 x Kartofler (Salling)  ·  Bilka 51138
[ ] 1 x Creme fraiche 38% fedt øko (Salling ØKO)  ·  Bilka 85164
[ ] 1 x Salt  ·  no product
```

> **Unofficial.** This project is not affiliated with or endorsed by goma. It uses the same private API as the goma.gg website, so that API can change or break at any time.

- [Install](#install)
- [Command line](#command-line)
- [Library](#library)
- [How it works](#how-it-works)
- [Development](#development)

## Install

Requires Python 3.12 or newer. The repository is private for now, so install it straight from GitHub:

```sh
pip install 'goma[cli] @ git+https://github.com/Hjord/goma'
# or run it without installing
uvx --from 'goma[cli] @ git+https://github.com/Hjord/goma' goma --help
```

Leave out `[cli]` if you only want the library. Its only dependency is httpx.

## Command line

```sh
goma login                       # goma emails you a 6-digit code; type it in
goma lists                       # your lists; * marks the primary one
goma items                       # what's on the primary list
goma items 12345 --all           # a given list, including ticked-off items
goma items --json                # machine-readable, with bilka_article_number
```

`goma login` reads the email from `--email` or `GOMA_EMAIL`, and asks for it when neither is set. The session is stored as `session.json` in `~/.config/goma`, readable only by you, and renewed on its own. Set `GOMA_CONFIG_DIR` to keep it somewhere else.

When a command answers `Run goma login`, goma has ended the session. Log in again.

## Library

```python
import asyncio

from goma import FileTokenStorage, GomaClient


async def main() -> None:
    async with GomaClient(token_storage=FileTokenStorage("session.json")) as client:
        # First time only: goma emails a 6-digit code.
        # await client.request_code("you@example.com")
        # await client.verify_code("you@example.com", input("Code: "))

        lists = await client.get_lists()
        primary = next(lst for lst in lists if lst.is_primary)

        for item in await client.get_items(primary.id):
            print(item.quantity, item.name, item.bilka_article_number)


asyncio.run(main())
```

### Logging in

goma offers Google, Apple, or a code sent by email. Only the email code can be automated, so that is what the client uses.

- `request_code(email)` asks goma to email a code. It never creates an account.
- `verify_code(email, code)` logs in and saves the session to `token_storage`.

The client then renews the session on its own. goma replaces the refresh token on every renewal, and the client saves the new one each time. When goma stops accepting the session, every call raises `NotLoggedInError` until you log in again.

`token_storage` is any `TokenStorage`: an object with an async `load()` and an async `save(data)`. `FileTokenStorage` writes a JSON file with mode 600. Without a storage, the session lasts only as long as the client.

### Lists and items

- `get_lists()` returns every list the account can see, newest first, as `ShoppingList(id, name, group_id, is_primary)`.
- `get_items(list_id, include_picked=False)` returns what you see on the list in goma. Items removed from the list are left out. Ticked-off items are left out unless you pass `include_picked=True`.

Each item is a `ListItem`:

| Field | |
|---|---|
| `name` | The product name, or the text of a free-text item |
| `quantity` | Whole units, rounded up |
| `is_picked` | Ticked off on the list |
| `bilka_article_number` | The BilkaToGo Article Number, or `None` for other stores and free text |
| `product` | goma's `Product`: `name`, `brand`, `store_name`, `price`, `amount`, `unit` |
| `custom_name` | The text of a free-text item |
| `recipe_id` | The goma recipe the item came from, if any |

Prices and amounts are `Decimal`.

### Errors

Every error derives from `GomaError`:

| Error | Meaning |
|---|---|
| `NotLoggedInError` | There is no session, or goma no longer accepts it. Log in again. |
| `InvalidCodeError` | The email code is wrong or has expired. Request a new one. |
| `GomaUnreachableError` | goma could not be reached. Retry later. |
| `UnexpectedResponseError` | goma answered with something the client does not understand. |

## How it works

goma.gg runs on Supabase, and this client calls the same REST and auth endpoints at `api.goma.gg` that the website calls. goma's product ids for Bilka look like `bilka-85164`, and the part after `bilka-` is the BilkaToGo Article Number. That was checked against bilkatogo.dk for every product on a real list.

One use is putting a goma list into a BilkaToGo cart, for example with [bilkatogo](https://github.com/nickknissen/bilkatogo).

## Development

```sh
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

The tests run against `tests/fake_goma.py`, an in-memory stand-in for goma's API, so no test talks to the real goma. CI runs on Python 3.12 and 3.14.
