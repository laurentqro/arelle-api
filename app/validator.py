"""Arelle XBRL validation wrapper."""

import tempfile
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field
from arelle.api.Session import Session
from arelle.RuntimeOptions import RuntimeOptions
from arelle.logging.handlers.StructuredMessageLogHandler import StructuredMessageLogHandler


# Cache directory with pre-populated taxonomy files
# Structure mirrors URL path: cache/http/amsf.mc/fr/taxonomy/strix/2025/strix.xsd
CACHE_DIR = Path(__file__).parent.parent / "cache"


@dataclass
class ValidationMessage:
    severity: str
    code: str
    message: str
    line: int | None = None
    column: int | None = None

    def to_dict(self) -> dict:
        result = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.line is not None:
            result["location"] = {"line": self.line, "column": self.column}
        return result


@dataclass
class ValidationResult:
    valid: bool
    messages: list[ValidationMessage] = field(default_factory=list)

    def to_dict(self) -> dict:
        errors = sum(1 for m in self.messages if m.severity == "error")
        warnings = sum(1 for m in self.messages if m.severity == "warning")
        info = sum(1 for m in self.messages if m.severity == "info")

        return {
            "valid": self.valid,
            "summary": {"errors": errors, "warnings": warnings, "info": info},
            "messages": [m.to_dict() for m in self.messages],
        }


def validate_xbrl(xml_content: str) -> ValidationResult:
    """Validate XBRL content against the bundled taxonomy."""

    # Write XML to temp file (Arelle requires file paths)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as xml_file:
        xml_file.write(xml_content)
        xml_path = xml_file.name

    try:
        messages = _run_arelle_validation(xml_path)
        has_errors = any(m.severity == "error" for m in messages)
        return ValidationResult(valid=not has_errors, messages=messages)
    finally:
        os.unlink(xml_path)


def _run_arelle_validation(file_path: str) -> list[ValidationMessage]:
    """Run Arelle validation and capture messages."""

    options = RuntimeOptions(
        entrypointFile=file_path,
        validate=True,
        cacheDirectory=str(CACHE_DIR),
        internetConnectivity="offline",
    )

    log_handler = StructuredMessageLogHandler()

    with Session() as session:
        session.run(options, logHandler=log_handler)
        log_xml = session.get_logs("xml")

    return _parse_log_xml(log_xml)


def _parse_log_xml(log_xml: str) -> list[ValidationMessage]:
    """Parse Arelle XML log output into ValidationMessages."""
    messages = []

    if not log_xml or not log_xml.strip():
        return messages

    try:
        root = ET.fromstring(log_xml)

        for entry in root.findall("entry"):
            code = entry.get("code", "unknown")
            level = entry.get("level", "info").lower()
            severity = _normalize_severity(level)

            # Get message text from nested message element
            message_elem = entry.find("message")
            if message_elem is not None:
                message_text = message_elem.text or ""
                line = _safe_int(message_elem.get("line"))
                column = _safe_int(message_elem.get("column"))
            else:
                message_text = entry.text or ""
                line = None
                column = None

            messages.append(
                ValidationMessage(
                    severity=severity,
                    code=code,
                    message=message_text.strip(),
                    line=line,
                    column=column,
                )
            )
    except ET.ParseError:
        # If XML parsing fails, return raw content as error
        messages.append(
            ValidationMessage(
                severity="error",
                code="arelle:logParseError",
                message=f"Failed to parse Arelle log output: {log_xml[:200]}",
            )
        )

    return messages


def _safe_int(value: str | None) -> int | None:
    """Safely convert string to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _normalize_severity(level: str) -> str:
    """Normalize log level to severity."""
    level = level.lower()
    if level in ("error", "err", "fatal", "critical"):
        return "error"
    if level in ("warning", "warn"):
        return "warning"
    return "info"
