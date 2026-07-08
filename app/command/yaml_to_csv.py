"""
app/command/yaml_to_csv.py

CLI command: merge all YAML mapping files from app/config/mappings/
into a single Map/USDM2FHIR.csv file.

Usage:
    venv/bin/python -m app.command.yaml_to_csv
    venv/bin/python -m app.command.yaml_to_csv --mappings-dir app/config/mappings --output Map/USDM2FHIR.csv
"""

import csv
import glob
import os
import sys

import click
import yaml


HEADER = [
    "Item",
    "USDM JSONata path",
    "FHIR resourceType",
    "FHIR path",
    "FHIR Index level",
    "USDM class",
    "USDM attribute",
]


@click.command("yaml-to-csv")
@click.option(
    "--mappings-dir",
    default="app/config/mappings",
    show_default=True,
    help="Directory containing *.yaml mapping files (sorted by filename).",
)
@click.option(
    "--output",
    default="Map/USDM2FHIR.csv",
    show_default=True,
    help="Destination CSV file.",
)
def yaml_to_csv(mappings_dir: str, output: str) -> None:
    """Merge all YAML mapping files into a single USDM2FHIR.csv."""

    yaml_files = sorted(glob.glob(os.path.join(mappings_dir, "*.yaml")))

    if not yaml_files:
        click.echo(f"⚠️  No YAML files found in '{mappings_dir}'", err=True)
        sys.exit(1)

    rows: list[list[str]] = []

    for yaml_file in yaml_files:
        with open(yaml_file, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        if not data or "mappings" not in data:
            click.echo(f"  ⚠  Skipping {yaml_file} (no 'mappings' key)", err=True)
            continue

        for mapping in data["mappings"]:
            # Strip trailing newline that YAML block scalars add
            usdm_path = str(mapping.get("usdm_path", "")).strip()

            row = [
                str(mapping.get("item", "")),
                usdm_path,
                str(mapping.get("fhir_resource", "")),
                str(mapping.get("fhir_path", "")),
                str(mapping.get("fhir_index", "")),
                str(mapping.get("usdm_class", "")),
                str(mapping.get("usdm_attribute", "")),
            ]
            rows.append(row)

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    with open(output, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)

    click.echo(
        f"✅  {output} generated — "
        f"{len(yaml_files)} YAML files → {len(rows)} mapping rows"
    )


if __name__ == "__main__":
    yaml_to_csv()

