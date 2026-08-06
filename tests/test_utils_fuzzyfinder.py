#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.fuzzyfinder
"""

import asyncio
import inspect
import threading
from unittest.mock import MagicMock

from metagit.core.utils import fuzzyfinder
from metagit.core.utils.fuzzyfinder import FuzzyFinderApp, FuzzyFinderConfig, _run_textual_app


def test_fuzzyfinder_basic():
    collection = ["apple", "banana", "grape", "apricot"]
    results = list(fuzzyfinder.fuzzyfinder("ap", collection))
    assert "apple" in results
    assert "apricot" in results
    assert "banana" not in results


def test_fuzzyfinder_empty():
    assert list(fuzzyfinder.fuzzyfinder("", ["a", "b"])) == ["a", "b"]
    assert list(fuzzyfinder.fuzzyfinder("x", [])) == []


def test_fuzzyfinder_no_match():
    collection = ["cat", "dog"]
    assert list(fuzzyfinder.fuzzyfinder("zebra", collection)) == []


def test_fuzzyfinder_non_preview_results_class_in_css_and_compose_source():
    assert ".fuzzy-finder-results-full" in FuzzyFinderApp.CSS
    assert "width: 100%" in FuzzyFinderApp.CSS
    src = inspect.getsource(FuzzyFinderApp.compose)
    assert "fuzzy-finder-results-full" in src
    assert "enable_preview" in src


def test_fuzzyfinder_quit_bindings_have_priority():
    """Ctrl+C / Esc must beat focused Input so nav can exit an empty-looking TUI."""
    by_key = {binding.key: binding for binding in FuzzyFinderApp.BINDINGS}
    for key in ("ctrl+c", "escape", "ctrl+q"):
        assert key in by_key
        assert by_key[key].priority is True
        assert by_key[key].action == "quit"


def test_fuzzyfinder_config_get_item_opacity_for_strings():
    """String items (project picker) must not raise via a bogus self.config lookup."""
    config = FuzzyFinderConfig(items=["ai", "default"], item_opacity=0.75)
    assert config.get_item_opacity("ai") == 0.75
    assert config.get_item_opacity(fuzzyfinder.FuzzyFinderTarget(name="x", description="y", opacity=0.25)) == 0.25


def test_fuzzyfinder_app_shows_string_items_on_mount():
    """Regression: nav project picker uses plain strings; list must populate on mount."""

    async def _run() -> None:
        config = FuzzyFinderConfig(
            items=["ai", "default", "gdo"],
            prompt_text="Search projects: ",
            max_results=10,
            total_count=3,
            enable_preview=False,
        )
        app = FuzzyFinderApp(config)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.current_results == ["ai", "default", "gdo"]
            results = app.query_one("#results_list")
            assert len(results.children) == 3

    asyncio.run(_run())


def test_fuzzyfinder_app_search_not_capped_by_max_results():
    config = FuzzyFinderConfig(items=["a", "b", "c"], max_results=1)
    app = FuzzyFinderApp(config)
    results = app._search("")
    assert results == ["a", "b", "c"]


def test_run_textual_app_keyboard_interrupt_returns_none() -> None:
    app = MagicMock()
    app.run.side_effect = KeyboardInterrupt()
    assert _run_textual_app(app) is None


def test_run_textual_app_uses_thread_when_event_loop_is_running(monkeypatch) -> None:
    app = MagicMock()
    app.run.return_value = "selected"
    started = threading.Event()
    finished = threading.Event()

    def _fake_run() -> str:
        started.set()
        finished.wait(timeout=1)
        return "selected"

    app.run.side_effect = _fake_run

    loop = asyncio.new_event_loop()
    loop_ready = threading.Event()

    def _run_loop() -> None:
        asyncio.set_event_loop(loop)
        loop_ready.set()
        loop.run_forever()

    loop_thread = threading.Thread(target=_run_loop, daemon=True)
    loop_thread.start()
    loop_ready.wait(timeout=1)

    async def _invoke() -> str:
        return _run_textual_app(app)

    future = asyncio.run_coroutine_threadsafe(_invoke(), loop)
    started.wait(timeout=1)
    finished.set()
    assert future.result(timeout=2) == "selected"

    loop.call_soon_threadsafe(loop.stop)
    loop_thread.join(timeout=2)
    loop.close()
