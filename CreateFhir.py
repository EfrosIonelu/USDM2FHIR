import json
import ast
from unittest import result
import jsonata
import pandas as pd
import re
from collections.abc import Iterable
from copy import deepcopy
import ResolveTags

_QUOTED_STR_RE = re.compile(r"""
    (?:
        '([^']*)'          # group 1: single-quoted literal
      | "([^"]*)"          # group 2: double-quoted literal
      | \.([A-Za-z_]\w*)   # group 3: bare identifier after dot
    )
""", re.VERBOSE)
    

def get_USDM_info(MapFile,USDMFile):
    # Get the mapping information from csv Mapping file based on the USDM mapping
    df = pd.read_csv(MapFile)
    
    with open(USDMFile, 'r') as file:
        data=json.load (file)
        ResultMap=[]
        RowIds=[]
        
        for i, row in df.iterrows():
            USDM_Path= df.iloc[i, 1]     
            USDM_Result=Parse_jsonata(codeSnip=USDM_Path,data=data,i=i)
            #if i == 86:
            #        print(f"Row {i}: USDM_Path='{USDM_Path}' -> USDM_Result='{USDM_Result}'"   )
            #print(f"Row {i}: USDM_Path='{USDM_Path}' -> USDM_Result='{USDM_Result}'"   )
            if USDM_Result is None: USDM_Result = " "
            if USDM_Result != " ":
                try:
                    x=json.loads(USDM_Result)
                except json.JSONDecodeError:
                    try:
                        x = ast.literal_eval(USDM_Result)
                       # print(f"Warning: Row {i} parsed via ast.literal_eval instead of JSON.")
                        
                    except (ValueError, SyntaxError):
                        print(f"Warning: Could not parse row {i} at all, copied directly.")
                        print(f"USDM_Result: {USDM_Result}")
                        
                    
                FHIR_resourcename= df.iloc[i, 2]
                FHIR_path= df.iloc[i, 3]
                FHIR_group= df.iloc[i, 4]
                #print(FHIR_group)

                if isinstance(x, dict):
                    x = [x]
                elif isinstance(x, str):
                    x = [{"0": x}]  # wrap string
                elif isinstance(x, list):
                    if all(isinstance(elem, str) for elem in x):
                        x = [{str(i): elem} for i, elem in enumerate(x)]
                
                for cell in x:
                    # extract the first key from the dict (value between brackets)
                    
                    try:
                        cell_id = next(iter(cell.keys()))
                    except StopIteration:
                        cell_id = None
                    if cell_id is not None:
                        if cell_id not in RowIds:
                            RowIds.append(cell_id)
                        if (USDM_Path.find('criterionItem') != -1 or USDM_Path.find('objectives') != -1) and USDM_Path.find('text') != -1:
                            cell[cell_id] = ResolveTags.ResolveTag(cell[cell_id], data)
                        try:
                            ResultMap.append((cell_id, FHIR_path, FHIR_group, cell[cell_id],FHIR_resourcename))
                        except Exception as e:
                            print(f"Error occurred while processing row {i}")
                            print(f"cell_id: {cell_id}, FHIR_path: {FHIR_path}, FHIR_group: {FHIR_group}, FHIR_resourcename: {FHIR_resourcename}")
                        
    return ResultMap, RowIds
            
def Parse_jsonata(codeSnip,data,i=0):
        if codeSnip is None:
            result = " "
        else:
            try:
                expr = jsonata.Jsonata(codeSnip)
                result = expr.evaluate(data)  
                #if i == 86:
                #    print(f"Row {i}: -> Result: {codeSnip} -> {result}")
            except:
                result=" "
                print(f"Error in expression {codeSnip}")
        if result is None: result = " "
        result= str(result)
        if result == "": result = " "
        if result == "{}": result = " "
        if result == "[]": result = " "
        # if result[0] == "[" and result[-1] == "]":
        #    result = result[1:-1]
        if result.find('name="') != -1:
             result0 = escapeTagRef(result)
        else:
             result0 = result
        return result0

def escapeTagRef(result):
    res = result
    # 1) Keep only the JSON part (optional, if you know there's extra text after ])
    json_part = res[:res.rfind(']') + 1]
    # 2) Escape the inner quotes in the HTML attributes (name="...") ONLY inside the JSON
    #    This changes name="indic_1"  ->  name=\"indic_1\"
    fixed = re.sub(r'name="([^"]+)"', r'name=\\"\1\\"', json_part)
    return fixed

def parse_semicolon_list_safe(s, drop_empty: bool = True):
    if s is None:
        return []
    s = str(s)
    parts = [p.strip() for p in s.split(";")]
    return [p for p in parts if p] if drop_empty else parts

def head_through_class(src: str, class_name: str) -> str:
    """
    Return the substring of `src` from the beginning up to and including
    the first path segment that matches class_name.
    
    Examples:
      head_through_class("identifier.use", "identifier") -> "identifier"
      head_through_class("characteristic.code.coding", "characteristic") -> "characteristic"
      head_through_class("a.b.c", "b") -> "a.b"
    """
    parts = src.split('.')
    for i, part in enumerate(parts):
        if part == class_name:
            return '.'.join(parts[:i + 1])
    return src  # class_name not found, return full path

def jsonpath_contains_class(path: str, class_name: str) -> bool:
    """
    Return True if `class_name` appears as a string literal or a bare identifier
    segment in the JSONPath-like expression `path`. Case-sensitive.
    Examples:
      $.items[?(@.type=='Foo')]
      $.schema.classes[?(@.name=="Bar")]
      $.Foo.methods[0]
    """
    target = class_name
    for m in _QUOTED_STR_RE.finditer(path):
        s = next(g for g in m.groups() if g is not None)
        if s == target:
            return True
    return False

def create_fhir_resource(ResultMap, RowIds, resource_type, data):
    # Get the mapping information from csv Mapping file based on the USDM mapping
    # save the corresponding information to the FHIR message
    fhir_resource = {
        "resourceType": resource_type,
        "id": data.get("id"),
        "meta": {
            "versionId": data.get("versionId"),
            "lastUpdated": data.get("lastUpdated")
        },        
    }    
    ResultMap = sorted(ResultMap, key=lambda t: (t[1], t[0]))
    pairs=[]
    group=""
    path=""
    cell_id_to_idx = {}
    idx=0
    id_level={}
    subdef={}
    prev_cell_id = ""
    for m in range(20): # support up to 20 levels of subgrouping
        id_level[m]=0
        subdef[m]=""
    for cell_id, fhir_path, fhir_group, value, fhir_resourcename in ResultMap:
        subgroup=parse_semicolon_list_safe(fhir_group)
        fhir_path_idx=fhir_path
        for m in range(len(subgroup)):
            sg=subgroup[m]
            if m==0: 
                sub_path=head_through_class(fhir_path, sg)
                lookup_key = (sub_path, cell_id)
                #if sg=="characteristic":
                #    print(cell_id, lookup_key,value)
                    
                # based id no per cell id, but on the subgrouping, so that all paths with the same subgrouping get the same index
                if cell_id != prev_cell_id:
                    if lookup_key in cell_id_to_idx:
                        idx = cell_id_to_idx[lookup_key]
                    elif sg == group:
                        idx+=1
                    else:
                        idx=0
                    group=sg
                    path=fhir_path
                    cell_id_to_idx[lookup_key] = idx  # remember first one
                elif fhir_path == path and len(subgroup) == 1:
                    idx+=1
                # lower level value - no increase in index, but reset to 0 if subgrouping changes
                elif fhir_path != path and lookup_key in cell_id_to_idx:
                    idx = cell_id_to_idx[lookup_key]
                    path=fhir_path
                elif fhir_path != path:
                    idx=0
                    group=sg
                    path=fhir_path
                
                id_level[0]=idx 
                
            else:
               # print (sg, subdef[m], id_level[m])
                if subdef[m] != sg or cell_id != prev_cell_id:
                    id_level[m]=0 
                    subdef[m]=sg
                else:
                    id_level[m]=id_level[m]+1    
                #print (sg, subdef[m], id_level[m])
                            
            try:
               # if len(subgroup) > 1: 
                   # print("before:", m, cell_id, idx, id_level[m], fhir_path_idx)
                fhir_path_idx=add_index_path_by_name(fhir_path_idx, sg, id_level[m], 0)
               # if len(subgroup) > 1: 
               #     print("after:", fhir_path_idx)
            except:
                fhir_path_idx=fhir_path_idx # No array path, use as is
        prev_cell_id = cell_id
        if value is not None and value != "[]" and value != "{}" and value != " " and value != "":
            pairs.append((fhir_path_idx, value))

    x = paths_to_json(pairs)
    fhir_resource.update(x)
    return fhir_resource

def create_fhir_output_old(fhir_resources, output_file="file.json"):
    # Wrap in FHIR Bundle container
    entries = [{"resource": res} for res in fhir_resources]

    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": entries
    }
    
    json.dump(fhir_bundle, open(output_file, "w"), indent=2)
    print(f"FHIR bundle saved to {output_file}")

def create_fhir_output(fhir_resources, output_file="file.json"):
    """
    fhir_resources: list of FHIR resources (dicts)
      resourceType ∈ {"ResearchStudy", "Location", "Group", ...}
    All Location and Group resources are moved into the `contained` array
    of the first ResearchStudy in the list. All resources (including that
    ResearchStudy) are still present as top‑level bundle entries.
    """
    # Separate resources by type
    research_studies = [r for r in fhir_resources
                        if r.get("resourceType") == "ResearchStudy"]
    contained_candidates = [r for r in fhir_resources
                            if r.get("resourceType") != "ResearchStudy"]
    # If there is at least one ResearchStudy, attach contained resources
    if research_studies and contained_candidates:
        main_rs = research_studies[0]  # pick the first; adjust if needed
        # Ensure we don't mutate the original list (optional)
        main_rs = main_rs  # already a dict; fine to mutate if you want
        # Initialize / extend contained
        existing_contained = main_rs.get("contained", [])
        # You may want deep copies so changes to contained don't affect originals
        existing_contained.extend(deepcopy(contained_candidates))
        main_rs["contained"] = existing_contained
    # Build bundle entries from (possibly modified) list
    entries = [{"resource": res} for res in research_studies]
    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": entries
    }
    with open(output_file, "w") as f:
        json.dump(fhir_bundle, f, indent=2)
    print(f"FHIR bundle saved to {output_file}")

def create_fhir_resources(result_map, row_ids,output_file="file.json"):
    StudyDef_map = [item for item in result_map if item[4] == "ResearchStudy"]
    MyResources=[]
    MyResource=create_fhir_resource(
        StudyDef_map,
        row_ids,
        "ResearchStudy",
        {
            "id": args.id,
            "versionId": args.version,
            "lastUpdated": args.updated
        }
    )
    MyResources.append(MyResource)
    MainGroup_map = [item for item in result_map if item[4] == "Group-all"]
    MyResource=create_fhir_resource(
        MainGroup_map,
        row_ids,
        "Group",
        {   "versionId": args.version,
            "lastUpdated": args.updated
        }
    )
    MyResources.append(MyResource)
    StudyGroup_map = [item for item in result_map if item[4] == "Group"]
    for i in row_ids:
        StudySubGroup_map = [item for item in StudyGroup_map if item[0]==i]
        if StudySubGroup_map != []:
            MyResource=create_fhir_resource(
            StudySubGroup_map,
            row_ids,
            "Group",
                {
                    "versionId": args.version,
                    "lastUpdated": args.updated
                }
                 )
            
            MyResources.append(MyResource)
    Location_map = [item for item in result_map if item[4] == "Location"]
    for i in row_ids:
        StudySubGroup_map = [item for item in Location_map if item[0]==i]
        if StudySubGroup_map != []:
            MyResource=create_fhir_resource(
            StudySubGroup_map,
            row_ids,
            "Location",
                {
                    "versionId": args.version,
                    "lastUpdated": args.updated
                }
                 )
            
            MyResources.append(MyResource)

    create_fhir_output(MyResources, output_file=output_file)

def add_index_path_by_name(fhir_path: str, segment_name: str, idx: int, occurrence: int = 0) -> str:
    """
    Insert '[idx]' into a FHIR path at the given segment name.
    Parameters:
      fhir_path: e.g. "code.coding.display"
      segment_name: e.g. "coding" (the segment to index)
      idx: e.g. 0  (the index to insert)
      occurrence: which occurrence to target if the name appears multiple times (0-based)
    Example:
      fhir_path = "code.coding.display"
      segment_name = "coding"
      idx = 0
      -> "code.coding[0].display"
    If segment_name appears multiple times:
      fhir_path = "a.b.c.b.d"
      segment_name = "b"
      occurrence = 1  # second 'b'
      -> "a.b.c.b[IDX].d"
    """
    parts = fhir_path.split(".")
    # Find indices where the segment name matches exactly
    matches = [i for i, p in enumerate(parts) if p == segment_name]
    if not matches:
        raise ValueError(f"segment_name '{segment_name}' not found in path '{fhir_path}'")
    if occurrence < 0 or occurrence >= len(matches):
        raise ValueError(f"occurrence {occurrence} out of range for segment_name '{segment_name}' "
                         f"(found {len(matches)} occurrence(s))")
    seg_idx = matches[occurrence]
    # Build the new path with the indexed segment
    parts[seg_idx] = f"{parts[seg_idx]}[{idx}]"
    return ".".join(parts)

def add_index_path(fhir_path, segmentLevel, idx):
    """
    Insert '[idx]' into a FHIR path at the given segment level.
    Example:
      fhir_path = "code.coding.display"
      segmentLevel = 1   # indexing 'coding'
      idx = 0
      -> "code.coding[0].display"
    """
    parts = fhir_path.split(".")
    if segmentLevel < 0 or segmentLevel >= len(parts):
        raise ValueError("segmentLevel is out of range")
    before = parts[:segmentLevel]              # list before indexed segment
    segment = parts[segmentLevel]              # the segment we index
    after = parts[segmentLevel + 1:]           # list after indexed segment
    indexed_segment = f"{segment}[{idx}]"
    # Reassemble path
    new_parts = before + [indexed_segment] + after
    return ".".join(new_parts)


def paths_to_json(path_value_pairs: list[tuple[str, any]]) -> dict:
    """
    Transform multiple path-value pairs into a single merged JSON structure.
    Supports array notation like "coding[0].display".
    """
    def set_nested(obj, keys, value):

        for i, key in enumerate(keys[:-1]):
            next_key = keys[i + 1]
            if isinstance(next_key, int):
                if key not in obj:
                    obj[key] = []
                while len(obj[key]) <= next_key:
                    obj[key].append({})
                obj = obj[key]
            elif isinstance(key, int):
                try:
                    #print(obj)
                    #print(f"Accessing index {key} in list at path segment '{keys[i-1]}'")
                    obj = obj[key]
                except (IndexError, TypeError):
                    raise ValueError(f"Invalid index {key} for path segment '{key}'")
            else: 
                if key not in obj:
                    obj[key] = {}
                    
                obj = obj[key]
        
        final_key = keys[-1]
        if isinstance(final_key, int):
            while len(obj) <= final_key:
                obj.append(None)
            obj[final_key] = value
        else:
            obj[final_key] = value
    
    def parse_path(path: str) -> list:
        """Parse path with array notation into list of keys."""
        tokens = []
        for part in path.split('.'):
            match = re.match(r'(\w+)\[(\d+)\]', part)
            if match:
                tokens.append(match.group(1))
                tokens.append(int(match.group(2)))
            else:
                tokens.append(part)
        return tokens
    
    result = {}
    for path, value in path_value_pairs:
        keys = parse_path(path)
        set_nested(result, keys, value)
    
    return result

def explode_result_map(result_map):
    """
    Take a list of 5-tuples:
        (cell_id, target_path, target_group, value, resource)
    and expand entries where 'value' is a list
    into one tuple per item in the list.
    Dicts / scalars are kept as-is.
    """
    exploded = []
    for cell_id, target_path, target_group, value, resource in result_map:
        # case 1: value is a list -> explode
        if isinstance(value, list):
            for v in value:
                exploded.append((cell_id, target_path, target_group, v, resource))
        # OPTIONAL: if you also want to explode tuples, use:
        # elif isinstance(value, (list, tuple)):
        else:
            # scalar, dict, None, etc. -> keep as-is
            exploded.append((cell_id, target_path, target_group, value, resource))
    return exploded

#map_file = "Map/USDM2FHIR.csv"
#usdm_file = "Input/NCT01750580_limited_tagged_resp.json"

#result_map, row_ids = get_USDM_info(map_file, usdm_file)
#create_fhir_resource(result_map, row_ids, "StudyDefinition", {"id": "123", "versionId": "1", "lastUpdated": "2023-01-01T00:00:00Z"}) 

import argparse
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert USDM data to FHIR resources."
    )
    parser.add_argument(
        "--map",
        required=True,
        help="Path to the USDM→FHIR mapping CSV file."
    )
    parser.add_argument(
        "--usdm",
        required=True,
        help="Path to the input USDM JSON file."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output FHIR JSON file."
    )
    parser.add_argument(
        "--id",
        default="123",
        help="FHIR resource ID to include in output."
    )
    parser.add_argument(
        "--version",
        default="1",
        help="FHIR versionId for the meta section."
    )
    parser.add_argument(
        "--updated",
        default="2023-01-01T00:00:00Z",
        help="FHIR meta.lastUpdated timestamp."
    )
    args = parser.parse_args()
    # Run your existing logic
    result_map, row_ids = get_USDM_info(args.map, args.usdm)
    result_map = explode_result_map(result_map)
    create_fhir_resources(result_map, row_ids,args.output)
    