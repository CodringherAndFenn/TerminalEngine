"""
Run the test suite on every core: one worker process per core, each taking
whole test modules from a shared queue (slowest first, so no long module is
left to run alone at the end). A worker keeps its process between modules,
so it builds each island once (tests/islands.py) and reuses it.

From EngineASCII/:

    ascii_adventurers/.venv/bin/python -m ascii_adventurers.tests.parallel
    ... -m ascii_adventurers.tests.parallel -j 4                 (4 workers)
    ... -m ascii_adventurers.tests.parallel test_m29_5 test_p7   (some modules)
    ... -m ascii_adventurers.tests.parallel --durations 10       (+ slowest tests)

Tests marked @timed (they measure wall-clock time) run last, on their own,
once the workers are done. It prints one line per finished module, then
every failure in full, then the total. It exits 1 if anything failed, like
unittest does.

Each module's time is kept in ascii_adventurers/.cache/test_times.json and
orders the next run. Without it (a fresh checkout, CI), the biggest files
go first.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import traceback
import unittest
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_TIMES = _TESTS.parent / ".cache" / "test_times.json"
_PACKAGE = "ascii_adventurers.tests"


def _cases(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from _cases(t)
        else:
            yield t


def _is_timed(test) -> bool:
    """@timed (tests/__init__.py): measures wall-clock time."""
    return getattr(getattr(test, getattr(test, "_testMethodName", ""), None), "timed", False)


def _run_module(name: str) -> dict:
    """Run one module's tests in this worker, all but the @timed ones (left
    for the end: their ids come back in "timed"); what happened, as plain
    data."""
    try:
        suite = unittest.defaultTestLoader.loadTestsFromName(f"{_PACKAGE}.{name}")
    except Exception:
        return {"name": name, "run": 0, "skipped": 0, "durations": [], "seconds": 0.0, "timed": [],
                "problems": [("ERROR", f"loading {name}", traceback.format_exc())]}
    cases = list(_cases(suite))
    out = _run(name, unittest.TestSuite(t for t in cases if not _is_timed(t)))
    out["timed"] = [t.id() for t in cases if _is_timed(t)]
    return out


def _run(name: str, suite: unittest.TestSuite) -> dict:
    out = {"name": name, "run": 0, "skipped": 0, "problems": [], "durations": []}
    start = time.perf_counter()
    try:
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0, buffer=True).run(suite)
    except Exception:
        out["problems"].append(("ERROR", f"running {name}", traceback.format_exc()))
    else:
        out["run"] = result.testsRun
        out["skipped"] = len(result.skipped)
        for kind, cases in (("FAIL", result.failures), ("ERROR", result.errors)):
            out["problems"] += [(kind, str(test), text) for test, text in cases]
        out["problems"] += [("UNEXPECTED SUCCESS", str(test), "")
                            for test in result.unexpectedSuccesses]
        out["durations"] = list(getattr(result, "collectedDurations", []))
    out["seconds"] = time.perf_counter() - start
    return out


def _modules(wanted: list[str]) -> list[str]:
    found = sorted(p.stem for p in _TESTS.glob("test_*.py"))
    if not wanted:
        return found
    names = [w.rsplit(".", 1)[-1].removesuffix(".py") for w in wanted]
    missing = [n for n in names if n not in found]
    if missing:
        sys.exit(f"no such test module: {', '.join(missing)}")
    return names


def _load_times() -> dict:
    try:
        return json.loads(_TIMES.read_text())
    except (OSError, ValueError):
        return {}


def _save_times(times: dict) -> None:
    try:
        _TIMES.parent.mkdir(parents=True, exist_ok=True)
        _TIMES.write_text(json.dumps(times, indent=1, sort_keys=True))
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ascii_adventurers.tests.parallel")
    ap.add_argument("modules", nargs="*", help="test modules to run (default: all)")
    cores = os.process_cpu_count() if hasattr(os, "process_cpu_count") else os.cpu_count()
    ap.add_argument("-j", "--jobs", type=int, default=cores or 1,
                    help="worker processes (default: one per core)")
    ap.add_argument("--durations", type=int, default=0, metavar="N",
                    help="also list the N slowest tests")
    args = ap.parse_args(argv)

    mods = _modules(args.modules)
    times = _load_times()
    mods.sort(key=lambda m: times.get(m, (_TESTS / f"{m}.py").stat().st_size / 1000), reverse=True)
    jobs = max(1, min(args.jobs, len(mods)))
    print(f"{len(mods)} test modules on {jobs} processes", flush=True)

    start = time.perf_counter()
    results: list[dict] = []
    broken = None
    pool = ProcessPoolExecutor(max_workers=jobs)
    try:
        futures = {pool.submit(_run_module, m): m for m in mods}
        for fut in as_completed(futures):
            try:
                r = fut.result()
            except BrokenProcessPool as e:
                broken = f"a worker process died while running {futures[fut]}: {e}"
                break
            results.append(r)
            mark = "FAILED" if r["problems"] else "ok"
            print(f"[{len(results):>3}/{len(mods)}] {r['seconds']:6.1f}s  {r['name']:<16}"
                  f" {r['run']:>4} tests  {mark}", flush=True)
    except KeyboardInterrupt:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    pool.shutdown(wait=True, cancel_futures=True)

    # The @timed tests, one at a time with every worker gone.
    timed = [t for r in results for t in r.pop("timed", [])]
    if timed and not broken:
        r = _run("@timed", unittest.defaultTestLoader.loadTestsFromNames(timed))
        print(f"[timed] {r['seconds']:6.1f}s  {len(timed)} tests run alone"
              f"  {'FAILED' if r['problems'] else 'ok'}", flush=True)
        results.append(r)
    wall = time.perf_counter() - start

    problems = [p for r in results for p in r["problems"]]
    for kind, test, text in problems:
        print("=" * 70)
        print(f"{kind}: {test}")
        print("-" * 70)
        print(text.rstrip())
    print("=" * 70)

    modules = [r for r in results if r["name"] != "@timed"]
    times.update({r["name"]: round(r["seconds"], 2) for r in modules})
    _save_times(times)
    slow = sorted(modules, key=lambda r: r["seconds"], reverse=True)[:5]
    print("slowest modules: " + ", ".join(f"{r['name']} {r['seconds']:.0f}s" for r in slow))
    if args.durations:
        tests = sorted((d for r in results for d in r["durations"]), key=lambda d: d[1], reverse=True)
        for test, secs in tests[:args.durations]:
            print(f"  {secs:6.2f}s  {test}")

    ran = sum(r["run"] for r in results)
    skipped = sum(r["skipped"] for r in results)
    fails = sum(1 for p in problems if p[0] == "FAIL")
    errors = len(problems) - fails
    print(f"Ran {ran} tests from {len(modules)} modules in {wall:.1f}s on {jobs} processes"
          + (f" ({skipped} skipped)" if skipped else ""))
    if broken:
        print(f"FAILED: {broken}")
        return 1
    if problems:
        print(f"FAILED (failures={fails}, errors={errors})")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
