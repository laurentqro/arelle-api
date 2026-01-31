"""Arelle XBRL validation wrapper."""

import tempfile
import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from arelle.api.Session import Session
from arelle.RuntimeOptions import RuntimeOptions


# Cache directory with pre-populated taxonomy files
# Structure: cache/amsf.mc/fr/taxonomy/strix/2025/strix.xsd
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

    # Create temp files for input and log output
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as xml_file:
        xml_file.write(xml_content)
        xml_path = xml_file.name

    log_path = tempfile.mktemp(suffix=".log")

    try:
        _run_arelle_validation(xml_path, log_path)
        messages = _parse_log_file(log_path)
        has_errors = any(m.severity == "error" for m in messages)
        return ValidationResult(valid=not has_errors, messages=messages)
    finally:
        os.unlink(xml_path)
        if os.path.exists(log_path):
            os.unlink(log_path)


def _run_arelle_validation(file_path: str, log_path: str) -> None:
    """Run Arelle validation, writing logs to file."""

    options = RuntimeOptions(
        entrypointFile=file_path,
        validate=True,
        logFile=log_path,
        logLevel="DEBUG",
        cacheDirectory=str(CACHE_DIR),
        internetConnectivity="offline",  # Use only local cache
    )

    with Session() as session:
        session.run(options)


def _parse_log_file(log_path: str) -> list[ValidationMessage]:
    """Parse Arelle log file into ValidationMessages."""
    messages = []

    if not os.path.exists(log_path):
        return messages

    with open(log_path, "r", encoding="utf-8") as f:
        log_content = f.read()

    for line in log_content.strip().split("\n"):
        if not line.strip():
            continue

        # Pattern: [messageCode] message - file, line X, column Y
        match = re.match(r"\[([^\]]+)\]\s*(.+)", line)
        if match:
            code = match.group(1)
            message_text = match.group(2)

            # Determine severity from code
            severity = _severity_from_code(code)

            # Try to extract line/column from message
            line_num = None
            column_num = None

            line_match = re.search(r"line\s+(\d+)", message_text)
            if line_match:
                line_num = int(line_match.group(1))

            col_match = re.search(r"column\s+(\d+)", message_text)
            if col_match:
                column_num = int(col_match.group(1))

            messages.append(
                ValidationMessage(
                    severity=severity,
                    code=code,
                    message=message_text.strip(),
                    line=line_num,
                    column=column_num,
                )
            )

    return messages


def _severity_from_code(code: str) -> str:
    """Determine severity from Arelle message code."""
    code_lower = code.lower()

    # Known error patterns
    if any(
        x in code_lower
        for x in [
            "error",
            "err",
            "invalid",
            "missing",
            "syntax",
            "undefined",
            "violation",
        ]
    ):
        return "error"

    # Known warning patterns
    if any(x in code_lower for x in ["warning", "warn", "deprecated"]):
        return "warning"

    # Info is default
    if code_lower == "info":
        return "info"

    # XBRL spec codes starting with xbrl are usually errors
    if code_lower.startswith("xbrl"):
        return "error"

    # XML schema errors
    if code_lower.startswith("xmlschema"):
        return "error"

    return "info"
