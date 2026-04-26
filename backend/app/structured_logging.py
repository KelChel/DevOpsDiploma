import json
import logging
import sys
from datetime import UTC, date, datetime
from typing import Any


_RESERVED_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "taskName",
    "thread",
    "threadName",
}

_SENSITIVE_FIELD_MARKERS = ("password", "secret", "token", "authorization", "medical", "patient")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_FIELDS or key.startswith("_"):
                continue
            payload[key] = _json_safe(value)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def configure_structured_logging(*, app_name: str, app_env: str) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = JsonLogFormatter()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        root_logger.addHandler(handler)

    for handler in root_logger.handlers:
        handler.setFormatter(formatter)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("devops_ticket_system").info(
        "application_logging_configured",
        extra={"event": "application_logging_configured", "app_name": app_name, "app_env": app_env},
    )


def get_app_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"devops_ticket_system.{name}")


def safe_log_fields(**fields: Any) -> dict[str, Any]:
    safe_fields: dict[str, Any] = {}
    for key, value in fields.items():
        lowered_key = key.lower()
        if any(marker in lowered_key for marker in _SENSITIVE_FIELD_MARKERS):
            safe_fields[key] = "[redacted]"
        else:
            safe_fields[key] = _json_safe(value)
    return safe_fields


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)
