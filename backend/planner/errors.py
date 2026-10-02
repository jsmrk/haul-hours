from planner.contracts import DutyEvent, to_wire


class PlanningProblem(Exception):
    def __init__(self, code: str, message: str, status: int = 409, retryable: bool = False,
                 field_errors: dict[str, list[str]] | None = None,
                 safe_prefix: tuple[DutyEvent, ...] = ()):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.retryable = retryable
        self.field_errors = field_errors or {}
        self.safe_prefix = safe_prefix

    def payload(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable,
                "field_errors": self.field_errors, "safe_prefix": to_wire(self.safe_prefix)}
