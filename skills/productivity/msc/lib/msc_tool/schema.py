from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Literal

QueryType = Literal["pl", "ib", "kh", "tbmt"]


@dataclass
class ErrorInfo:
    code: str
    message: str


@dataclass
class QueryParams:
    code: str | None = None
    unit: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    n: int | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "unit": self.unit,
            "from": self.from_date,
            "to": self.to_date,
            "n": self.n,
        }


@dataclass
class MscSchema:
    query_type: QueryType
    query_params: QueryParams
    source: str
    script_used: str
    fetched_at: str
    total_count: int
    records: list[dict[str, Any]]
    error: ErrorInfo | None = None

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["query_params"] = self.query_params.to_json()
        if self.error is None:
            d["error"] = None
        return d
