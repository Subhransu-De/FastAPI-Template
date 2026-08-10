import logfire
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from app.settings import app_settings

_configured = False


def _format_span(span: ReadableSpan) -> str:
    return f"{span.to_json(indent=None)}\n"


def configure_observability() -> None:
    global _configured
    if _configured:
        return

    logfire.configure(
        service_name=app_settings.app_name,
        send_to_logfire=False,
        console=False,
        metrics=False,
        additional_span_processors=[
            SimpleSpanProcessor(
                ConsoleSpanExporter(formatter=_format_span),
            ),
        ],
    )
    _configured = True
