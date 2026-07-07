#!/usr/bin/env python
"""
Unit tests for metagit.core.utils.fuzzyfinder
"""

import asyncio
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


def test_fuzzyfinder_app_search_not_capped_by_max_results():
    config = FuzzyFinderConfig(items=["a", "b", "c"], max_results=1)
    app = FuzzyFinderApp(config)
    results = app._search("")
    assert results == ["a", "b", "c"]


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
