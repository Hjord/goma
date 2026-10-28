import asyncio
import dataclasses
import functools
import json
import os
from collections.abc import Callable, Coroutine
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any

import typer

from .client import GomaClient
from .exceptions import GomaError, NotLoggedInError
from .models import ListItem
from .token_storage import FileTokenStorage

app = typer.Typer(no_args_is_help=True, help="Read your goma.gg shopping lists.")

JsonOption = Annotated[bool, typer.Option("--json", help="Output JSON.")]


def config_dir() -> Path:
    if override := os.environ.get("GOMA_CONFIG_DIR"):
        return Path(override)
    return Path(typer.get_app_dir("goma", force_posix=True))


def make_client() -> GomaClient:
    return GomaClient(token_storage=FileTokenStorage(config_dir() / "session.json"))


def run_async[**P, R](func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return asyncio.run(func(*args, **kwargs))
        except NotLoggedInError as err:
            typer.echo(f"{err}. Run `goma login`.", err=True)
            raise typer.Exit(1) from None
        except GomaError as err:
            typer.echo(str(err), err=True)
            raise typer.Exit(1) from None

    return wrapper


def to_json(data: Any) -> str:
    def default(obj: Any) -> Any:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        raise TypeError(type(obj).__name__)

    return json.dumps(data, default=default, ensure_ascii=False, indent=2)


@app.command()
@run_async
async def login(
    email: Annotated[
        str | None, typer.Option("--email", envvar="GOMA_EMAIL", help="goma account email.")
    ] = None,
) -> None:
    """Log in with a code goma emails you. The session is stored and renewed on its own."""
    email = email or typer.prompt("Email")
    async with make_client() as client:
        await client.request_code(email)
        code = typer.prompt(f"Code sent to {email}")
        await client.verify_code(email, code)
    typer.echo("Logged in.")


@app.command("lists")
@run_async
async def show_lists(as_json: JsonOption = False) -> None:
    """Your shopping lists. * marks the primary list."""
    async with make_client() as client:
        lists = await client.get_lists()
    if as_json:
        typer.echo(to_json(lists))
        return
    for shopping_list in lists:
        marker = "*" if shopping_list.is_primary else " "
        typer.echo(f"{marker} {shopping_list.id:>8}  {shopping_list.name}")


@app.command()
@run_async
async def items(
    list_id: Annotated[
        int | None, typer.Argument(help="List id from `goma lists`; the primary list if left out.")
    ] = None,
    include_picked: Annotated[
        bool, typer.Option("--all", help="Include items ticked off on the list.")
    ] = False,
    as_json: JsonOption = False,
) -> None:
    """The items on a shopping list, with their Bilka Article Number where goma has one."""
    async with make_client() as client:
        if list_id is None:
            list_id = await primary_list_id(client)
        found = await client.get_items(list_id, include_picked=include_picked)
    if as_json:
        typer.echo(
            to_json(
                [
                    {
                        **dataclasses.asdict(item),
                        "name": item.name,
                        "bilka_article_number": item.bilka_article_number,
                    }
                    for item in found
                ]
            )
        )
        return
    for item in found:
        typer.echo(describe(item))


async def primary_list_id(client: GomaClient) -> int:
    lists = await client.get_lists()
    for shopping_list in lists:
        if shopping_list.is_primary:
            return shopping_list.id
    if lists:
        return lists[0].id
    typer.echo("You have no shopping lists on goma.", err=True)
    raise typer.Exit(1)


def describe(item: ListItem) -> str:
    tick = "x" if item.is_picked else " "
    brand = f" ({item.product.brand})" if item.product and item.product.brand else ""
    if item.bilka_article_number:
        where = f"Bilka {item.bilka_article_number}"
    elif item.product and item.product.store_name:
        where = item.product.store_name
    else:
        where = "no product"
    return f"[{tick}] {item.quantity} x {item.name}{brand}  ·  {where}"
