def main() -> None:
    try:
        from .cli import app
    except ImportError:
        raise SystemExit("The goma CLI needs its extras: pip install 'goma-gg[cli]'") from None
    app()


if __name__ == "__main__":
    main()
