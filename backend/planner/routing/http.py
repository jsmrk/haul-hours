import time

import httpx

from planner.errors import PlanningProblem
from planner.routing.contracts import ProviderBudget


def request_json(client: httpx.Client, method: str, url: str, budget: ProviderBudget,
                 timeout: float = 10, **kwargs) -> dict:
    for attempt in range(2):
        request_timeout = budget.consume(timeout)
        try:
            response = client.request(method, url, timeout=request_timeout, **kwargs)
            if response.status_code == 429:
                retry = response.headers.get("Retry-After", "")
                hint = f" Retry after {retry} seconds." if retry.isdigit() and len(retry) <= 5 else ""
                raise PlanningProblem("PROVIDER_RATE_LIMITED", "The map provider is rate limited." + hint, 429, True)
            if response.status_code in (404, 400):
                raise PlanningProblem("ROUTE_UNREACHABLE", "The provider cannot route between these truck locations.", 422)
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
            if attempt == 0 and budget.check() > .3:
                time.sleep(.2)
                continue
            raise PlanningProblem("PROVIDER_UNAVAILABLE", "The map provider is temporarily unavailable.", 503, True) from None
        except (ValueError, TypeError):
            raise PlanningProblem("PROVIDER_INVALID_RESPONSE", "The map provider returned an invalid response.", 503, True) from None
    raise AssertionError("Unreachable")
