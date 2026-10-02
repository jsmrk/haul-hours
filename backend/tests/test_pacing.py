import time
from threading import Thread

import pytest

from planner.errors import PlanningProblem
from planner.routing.contracts import ProviderBudget
from planner.routing.http import RequestPacer


def test_pacing_spaces_requests_and_refuses_to_wait_past_deadline(monkeypatch):
    import planner.routing.http as transport
    clock = [100.0]
    monkeypatch.setattr(transport.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(transport.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    pacer = RequestPacer(2)
    pacer.wait(ProviderBudget(110, 5))
    pacer.wait(ProviderBudget(110, 5))
    assert clock[0] == 102
    with pytest.raises(PlanningProblem) as caught:
        pacer.wait(ProviderBudget(103, 5))
    assert caught.value.code == "PLANNING_TIMEOUT"
    assert clock[0] == 102


def test_concurrent_pacing_lock_wait_respects_the_request_deadline():
    pacer = RequestPacer(2)
    problems = []
    def attempt():
        try:
            pacer.wait(ProviderBudget(time.monotonic() + .02, 5))
        except PlanningProblem as problem:
            problems.append(problem.code)
    pacer.lock.acquire()
    worker = Thread(target=attempt, daemon=True)
    try:
        worker.start()
        worker.join(.1)
        assert problems == ["PLANNING_TIMEOUT"]
    finally:
        pacer.lock.release()
        worker.join(1)
