from gui.webUI import build_app


def test_build_app_smoke() -> None:
    app = build_app()
    assert app is not None
