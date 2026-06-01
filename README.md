# USDM 2 FHIR Tool

This tool picks up a study design in USDM format and transforms it into a FHIR StudyDefinition and corresponding Group maps.
The tool must be seen as an example and starting point. The mappings stored as JSONata queries in the map directory can be adjusted according to the FHIR resource needs.

An example file in USDM format with corresponding expectedResponse extensions is available in the Input directory. 

The tool can be invoked by running the following command:

python CreateFhir.py --map Map/USDM2FHIR.csv --usdm Input/NCT01750580_limited_tagged_resp.json --output Output/MyNewFile.json
