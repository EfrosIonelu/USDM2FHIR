"""
jsonata_inspect.py
------------------
CLI command that evaluates a JSONata expression against a JSON file and returns
structured metadata about the result (type, length, keys, sample …).

Designed to be called by LLMs or humans from the terminal.

Usage examples
--------------
# Expression passed as argument
python -m app.command.jsonata_inspect "study.studyTitle"

# Expression piped / typed interactively
echo "study.versions[0].studyDesigns" | python -m app.command.jsonata_inspect

# Custom input file
python -m app.command.jsonata_inspect "study" --file Input/CDISC_Pilot_Study_v4_FIXED.json

# Machine-readable JSON output (good for LLMs)
python -m app.command.jsonata_inspect "study.versions" --json
"""

import json
import sys
from pathlib import Path
from typing import Any

import click
import jsonata

DEFAULT_INPUT_FILE = "Input/NCT01750580_limited_tagged_resp.json"

# Maximum number of items shown in the sample for arrays / object keys
SAMPLE_SIZE = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _describe(value: Any) -> dict:
    """Return a metadata dict that describes *value* at a glance."""
    info: dict = {}

    if value is None:
        info["type"] = "null"
        return info

    if isinstance(value, bool):
        info["type"] = "boolean"
        info["value"] = value
        return info

    if isinstance(value, (int, float)):
        info["type"] = "number"
        info["value"] = value
        return info

    if isinstance(value, str):
        info["type"] = "string"
        info["length"] = len(value)
        info["value"] = value if len(value) <= 200 else value[:200] + "…"
        return info

    if isinstance(value, list):
        info["type"] = "array"
        info["length"] = len(value)
        if value:
            # Describe the types of items
            item_types = list({type(v).__name__ for v in value[:50]})
            info["item_types"] = item_types
            # Sample: first SAMPLE_SIZE items (trimmed if large)
            sample = []
            for item in value[:SAMPLE_SIZE]:
                if isinstance(item, dict):
                    sample.append({k: "…" for k in list(item.keys())[:10]})
                else:
                    sample.append(item)
            info["sample"] = sample
        return info

    if isinstance(value, dict):
        keys = list(value.keys())
        info["type"] = "object"
        info["key_count"] = len(keys)
        info["keys"] = keys[:50]  # up to 50 top-level keys
        # For each key show the type of its value
        info["key_types"] = {
            k: _type_name(value[k]) for k in keys[:50]
        }
        return info

    # Fallback
    info["type"] = type(value).__name__
    info["repr"] = repr(value)[:300]
    return info


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return f"array[{len(value)}]"
    if isinstance(value, dict):
        return f"object({len(value)} keys)"
    return type(value).__name__


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command(
    name="jsonata-inspect",
    help=(
        "Evaluate a JSONata EXPRESSION against a JSON file and print metadata "
        "about the result (type, length, keys, sample …).\n\n"
        "If EXPRESSION is omitted, it is read from stdin."
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
    help="Output result metadata as machine-readable JSON (useful for LLMs).",
)
@click.option(
    "--raw", "-r",
    "show_raw",
    is_flag=True,
    default=False,
    help="Also print the raw JSONata result (may be very long).",
)
def inspect_command(expression: str | None, input_file: str, as_json: bool, show_raw: bool):
    # ---- Read expression ----
    if expression is None:
        if sys.stdin.isatty():
            click.echo("Enter JSONata expression (press Enter then Ctrl-D / Ctrl-Z):")
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
        error_info = {
            "status": "error",
            "expression": expression,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        if as_json:
            click.echo(json.dumps(error_info, indent=2))
        else:
            click.echo(f"[ERROR] {type(exc).__name__}: {exc}", err=True)
        sys.exit(1)

    # ---- Build metadata ----
    meta = _describe(result)
    meta["expression"] = expression
    meta["input_file"] = str(file_path)
    meta["status"] = "ok"

    # ---- Output ----
    if as_json:
        click.echo(json.dumps(meta, indent=2, ensure_ascii=False))
    else:
        click.echo("")
        click.echo(f"  Expression : {expression}")
        click.echo(f"  Input file : {file_path}")
        click.echo(f"  Status     : ok")
        click.echo("")
        click.echo(f"  Type       : {meta.get('type')}")

        t = meta.get("type")
        if t == "array":
            click.echo(f"  Length     : {meta.get('length')}")
            click.echo(f"  Item types : {meta.get('item_types')}")
            click.echo(f"  Sample     :")
            for i, item in enumerate(meta.get("sample", [])):
                click.echo(f"    [{i}] {item}")

        elif t == "object":
            click.echo(f"  Keys ({meta.get('key_count')})  :")
            for k, v_type in meta.get("key_types", {}).items():
                click.echo(f"    {k!r:40s}  → {v_type}")

        elif t == "string":
            click.echo(f"  Length     : {meta.get('length')}")
            click.echo(f"  Value      : {meta.get('value')}")

        elif t in ("number", "boolean"):
            click.echo(f"  Value      : {meta.get('value')}")

        elif t == "null":
            click.echo("  (result is null / no match)")

        click.echo("")

    if show_raw:
        click.echo("--- RAW RESULT ---")
        click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# Entry-point when run as  python -m app.command.jsonata_inspect
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    inspect_command()

