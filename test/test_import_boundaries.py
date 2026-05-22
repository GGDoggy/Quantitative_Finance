from __future__ import annotations

import importlib
import sys


def _clear_modules(*prefixes: str) -> None:
    to_delete = [name for name in sys.modules if any(name == p or name.startswith(f"{p}.") for p in prefixes)]
    for name in to_delete:
        sys.modules.pop(name, None)


def test_import_src_plotlib_isolated_from_gui_and_preprocess() -> None:
    _clear_modules("src.plotlib", "gui", "src.preprocess")

    importlib.import_module("src.plotlib")

    assert "src.plotlib" in sys.modules
    assert "gui" not in sys.modules
    assert "src.preprocess" not in sys.modules


def test_renderer_loader_does_not_import_discovery_locator_or_catalog_modules() -> None:
    _clear_modules("src.plotlib.loaders.simulation", "src.plotlib.discovery", "src.preprocess.catalog")

    importlib.import_module("src.plotlib.loaders.simulation")

    assert "src.plotlib.discovery" not in sys.modules
    assert "src.preprocess.catalog" not in sys.modules


def test_app_registry_can_import_src_plotlib_without_reverse_dependency() -> None:
    _clear_modules("src.app_plot_registry", "src.plotlib")

    importlib.import_module("src.app_plot_registry")
    importlib.import_module("src.plotlib")

    assert "src.app_plot_registry" in sys.modules
    assert "src.plotlib" in sys.modules

    _clear_modules("src.app_plot_registry", "src.plotlib")
    importlib.import_module("src.plotlib")
    assert "src.app_plot_registry" not in sys.modules


def test_src_plots_package_is_removed() -> None:
    _clear_modules("src.plots")

    try:
        importlib.import_module("src.plots")
    except ModuleNotFoundError:
        return

    raise AssertionError("src.plots should not be importable after Stage C removal.")
