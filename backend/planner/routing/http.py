import time
from threading import Lock

import httpx

from planner.errors import PlanningProblem
from planner.routing.contracts import ProviderBudget


class RequestPacer:
    """Space uncached requests within one process; not a distributed quota gate."""
    def __init__(self, interval_s: float):
        self.interval_s = interval_s
        self.next_at = 0.0
        self.lock = Lock()

    def wait(self, budget: ProviderBudget):
        if not self.lock.acquire(timeout=budget.check()):
            raise PlanningProblem("PLANNING_TIMEOUT", "Provider pacing reached the planning time limit. Please try again.", 504, True)
        try:
            delay = max(0, self.next_at - time.monotonic())
            if delay >= budget.check():
                raise PlanningProblem("PLANNING_TIMEOUT", "Provider pacing reached the planning time limit. Please try again.", 504, True)
            if delay:
                time.sleep(delay)
            budget.check()
            self.next_at = time.monotonic() + self.interval_s
        finally:
            self.lock.release()


def request_json(client: httpx.Client, method: str, url: str, budget: ProviderBudget,
                 timeout: float = 10, pacer: RequestPacer | None = None, attempts: int = 2, **kwargs) -> dict:
    for attempt in range(attempts):
        if pacer:
            pacer.wait(budget)
        request_timeout = budget.consume(timeout)
        try:
            response = client.request(method, url, timeout=request_timeout, **kwargs)
            if response.status_code == 429:
                retry = response.headers.get("Retry-After", "")
                hint = f" Retry after {retry} seconds." if retry.isdigit() and len(retry) <= 5 else ""
                raise PlanningProblem("PROVIDER_RATE_LIMITED", "The map provider is rate limited." + hint, 429, True)
            if response.status_code in (404, 400):
                raise PlanningProblem("ROUTE_UNREACHABLE", "The provider cannot route between these truck locations.", 422)
            if response.status_code in (401, 403):
                raise PlanningProblem("PROVIDER_CONFIGURATION_ERROR", "The data provider rejected the server credentials. Check the server configuration.", 503)
            if response.status_code >= 500:
                raise httpx.HTTPStatusError("unavailable", request=response.request, response=response)
            if response.status_code >= 400:
                raise PlanningProblem("PROVIDER_UNAVAILABLE", "The map provider is unavailable. Check its configuration.", 503, True)
            if len(response.content) > 16_000_000:
                raise ValueError("Provider response too large")
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")
            return data
        except (httpx.TransportError, httpx.HTTPStatusError):
            if attempt + 1 < attempts and budget.check() > .3:
                time.sleep(.2)
                continue
            raise PlanningProblem("PROVIDER_UNAVAILABLE", "The map provider is temporarily unavailable.", 503, True) from None
        except (ValueError, TypeError):
            raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "The map provider returned an invalid response.", 503, True) from None
    raise AssertionError("Unreachable")
