import json
import ast
import os
import re
from copy import deepcopy
from datetime import date

import pandas as pd

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from CreateFhir import (
    Parse_jsonata,
    explode_result_map,
    create_fhir_resource,
)
import ResolveTags

DEFAULT_MAP_FILE = "Map/USDM2FHIR.csv"


def _get_usdm_info_from_data(map_file: str, data: dict):
    """Same logic as get_USDM_info but accepts data as dict (no file I/O for USDM)."""
    df = pd.read_csv(map_file)
    result_map = []
    row_ids = []

    for i, row in df.iterrows():
        usdm_path = df.iloc[i, 1]
        usdm_result = Parse_jsonata(codeSnip=usdm_path, data=data, i=i)
        if usdm_result is None:
            usdm_result = " "
        if usdm_result != " ":
            try:
                x = json.loads(usdm_result)
            except json.JSONDecodeError:
                try:
                    x = ast.literal_eval(usdm_result)
                except (ValueError, SyntaxError):
                    continue  # skip — x would retain previous iteration's value

            fhir_resourcename = df.iloc[i, 2]
            fhir_path = df.iloc[i, 3]
            fhir_group = df.iloc[i, 4]

            if isinstance(x, dict):
                x = [x]
            elif isinstance(x, str):
                x = [{"0": x}]
            elif isinstance(x, list):
                if all(isinstance(elem, str) for elem in x):
                    x = [{str(j): elem} for j, elem in enumerate(x)]

            for cell in x:
                try:
                    cell_id = next(iter(cell.keys()))
                except StopIteration:
                    cell_id = None
                if cell_id is not None:
                    if cell_id not in row_ids:
                        row_ids.append(cell_id)
                    if (
                        (usdm_path.find('criterionItem') != -1 or usdm_path.find('objectives') != -1)
                        and usdm_path.find('text') != -1
                    ):
                        try:
                            cell[cell_id] = ResolveTags.ResolveTag(cell[cell_id], data)
                        except Exception:
                            pass
                    try:
                        result_map.append((cell_id, fhir_path, fhir_group, cell[cell_id], fhir_resourcename))
                    except Exception:
                        pass

    return result_map, row_ids


def _build_fhir_resources(result_map: list, row_ids: list, resource_id: str, version: str, updated: str) -> dict:
    """Build FHIR resources dict entirely in memory."""
    meta = {"id": resource_id, "versionId": version, "lastUpdated": updated}
    resources = []

    study_map = [item for item in result_map if item[4] == "ResearchStudy"]
    resources.append(create_fhir_resource(study_map, row_ids, "ResearchStudy", meta))

    main_group_map = [item for item in result_map if item[4] == "Group-all"]
    resources.append(create_fhir_resource(main_group_map, row_ids, "Group", meta))

    study_group_map = [item for item in result_map if item[4] == "Group"]
    for row_id in row_ids:
        sub = [item for item in study_group_map if item[0] == row_id]
        if sub:
            resources.append(create_fhir_resource(sub, row_ids, "Group", meta))

    location_map = [item for item in result_map if item[4] == "Location"]
    for row_id in row_ids:
        sub = [item for item in location_map if item[0] == row_id]
        if sub:
            resources.append(create_fhir_resource(sub, row_ids, "Location", meta))

    ev_map = [item for item in result_map if item[4] == "EvidenceVariable"]
    for row_id in row_ids:
        sub = [item for item in ev_map if item[0] == row_id]
        if sub:
            resources.append(create_fhir_resource(sub, row_ids, "EvidenceVariable", meta))

    research_studies = [r for r in resources if r.get("resourceType") == "ResearchStudy"]
    contained_candidates = [r for r in resources if r.get("resourceType") != "ResearchStudy"]

    if research_studies and contained_candidates:
        main_rs = research_studies[0]
        existing = main_rs.get("contained", [])
        existing.extend(deepcopy(contained_candidates))
        main_rs["contained"] = existing

    if len(research_studies) == 1:
        return research_studies[0]

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": r} for r in research_studies],
    }


def transform_usdm_to_fhir(
    usdm_data: dict,
    map_file: str = DEFAULT_MAP_FILE,
    resource_id: str = "123",
    version: str = "1",
    updated: str = None,
) -> dict:
    """Transform a USDM JSON dict into a FHIR resource dict. No file I/O."""
    if updated is None:
        updated = date.today().isoformat() + "T00:00:00Z"

    result_map, row_ids = _get_usdm_info_from_data(map_file, usdm_data)
    result_map = explode_result_map(result_map)
    return _build_fhir_resources(result_map, row_ids, resource_id, version, updated)

