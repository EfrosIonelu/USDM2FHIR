PYTHON = venv/bin/python
PIP = venv/bin/pip
IMAGE_NAME = usdm2fhir
REGISTRY = ghcr.io/efrosionelu/usdm2fhir
PORT = 8000

.PHONY: setup execute_example run docker-build docker-run docker-stop docker-push

setup:
	python3 -m venv venv
	$(PIP) install -r requirements.txt
	@echo "✅ venv creat si dependentele instalate! Ruleaza: source venv/bin/activate"

execute_example:
	$(PYTHON) CreateFhir.py --map Map/USDM2FHIR.csv --usdm Input/NCT01750580_limited_tagged_resp.json --output Output/MyNewFile_2.json

run:
	$(PYTHON) -m uvicorn main:app --reload --host 0.0.0.0 --port $(PORT)

docker-build:
	docker build -t $(IMAGE_NAME) .

docker-run:
	docker run --rm -p $(PORT):8000 --name $(IMAGE_NAME) $(IMAGE_NAME)

docker-stop:
	docker stop $(IMAGE_NAME)

docker-push:
	docker build -t $(REGISTRY):latest .
	docker push $(REGISTRY):latest

