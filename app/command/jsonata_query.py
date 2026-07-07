"""
jsonata_query.py
----------------
CLI command that evaluates a JSONata expression and returns the ACTUAL result,
truncated to the first 250 characters for large arrays/objects.

When the result is too large, it hints the user to narrow down the expression
using `jsonata_inspect` first.

Usage examples
--------------
python -m app.command.jsonata_query "study.studyTitle"
python -m app.command.jsonata_query "study.versions[0].versionIdentifier"
python -m app.command.jsonata_query "study.versions[0].studyDesigns[0].name"

# Custom file
python -m app.command.jsonata_query "study" --file Input/CDISC_Pilot_Study_v4_FIXED.json

# JSON output (for LLMs)
python -m app.command.jsonata_query "study.studyTitle" --json
"""

import json
import sys
from pathlib import Path
from typing import Any

import click
import jsonata

DEFAULT_INPUT_FILE = "Input/NCT01750580_limited_tagged_resp.json"
TRUNCATE_AT = 250


def _encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


@click.command(
    name="jsonata-query",
    help=(
        "Evaluate a JSONata EXPRESSION and return the actual result. "
        "Large arrays/objects are JSON-encoded and truncated to the first "
        f"{TRUNCATE_AT} characters — use jsonata-inspect to explore structure "
        "and narrow down your expression.\n\n"
        "If EXPRESSION is omitted it is read from stdin."
    ),
)
@click.argument("expression", required=False, default=None)
@click.option(
    "--file", "-f",
    "input_file",
    default=DEFAULT_INPUT_FILE,
    show_default=True,
    help="Path to the JSON input file.",
)
@click.option(
    "--json", "-j",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as machine-readable JSON envelope (useful for LLMs).",
)
def query_command(expression: str | None, input_file: str, as_json: bool):
    # ---- Read expression ----
    if expression is None:
        if sys.stdin.isatty():
            click.echo("Enter JSONata expression (press Enter then Ctrl-D):")
        expression = sys.stdin.read().strip()

    if not expression:
        click.echo("ERROR: no JSONata expression provided.", err=True)
        sys.exit(1)

    # ---- Load JSON file ----
    file_path = Path(input_file)
    if not file_path.exists():
        click.echo(f"ERROR: input file not found: {file_path}", err=True)
        sys.exit(1)

    with file_path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    # ---- Evaluate JSONata ----
    try:
        expr = jsonata.Jsonata(expression)
        result = expr.evaluate(data)
    except Exception as exc:
        payload = {
            "status": "error",
            "expression": expression,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        if as_json:
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(f"[ERROR] {type(exc).__name__}: {exc}", err=True)
        sys.exit(1)

    # ---- Encode result ----
    if isinstance(result, str):
        encoded = result
    else:
        encoded = _encode(result)
    truncated = len(encoded) > TRUNCATE_AT

    hint = None
    if truncated:
        hint = (
            f"Result truncated at {TRUNCATE_AT} chars "
            f"(full result is {len(encoded)} chars). "
            "Be more specific in your expression, or use "
            "`jsonata-inspect` to explore the structure first:\n"
            f"  venv/bin/python -m app.command.jsonata_inspect \"{expression}\""
        )

    preview = encoded[:TRUNCATE_AT] + ("…" if truncated else "")

    # ---- Output ----
    if as_json:
        output = {
            "status": "ok",
            "expression": expression,
            "input_file": str(file_path),
            "result_type": (
                "null" if result is None
                else "array" if isinstance(result, list)
                else "object" if isinstance(result, dict)
                else "boolean" if isinstance(result, bool)
                else "number" if isinstance(result, (int, float))
                else "string"
            ),
            "result_full_length": len(encoded),
            "truncated": truncated,
            "result": preview,
        }
        if hint:
            output["hint"] = hint
        click.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        click.echo("")
        click.echo(f"  Expression : {expression}")
        click.echo(f"  Input file : {file_path}")
        click.echo("")
        click.echo(preview)
        click.echo("")
        if hint:
            click.echo(f"⚠️  {hint}")
            click.echo("")


if __name__ == "__main__":
    query_command()

