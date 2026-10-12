# AI-Assisted API Test Automation Framework

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![pytest](https://img.shields.io/badge/pytest-7.4+-green.svg)](https://pytest.org/)
[![API Tests](https://github.com/raissazhang0108-droid/api-automation-framework/actions/workflows/tests.yml/badge.svg)](https://github.com/raissazhang0108-droid/api-automation-framework/actions)

A Python / pytest framework for API testing. It uses an LLM to draft test cases from an API spec, runs them with `requests` + pytest, and suggests fixes for failing tests. All suggested fixes are meant to be reviewed by a human before they are applied.

The included example targets the public [Swagger Petstore](https://petstore.swagger.io/) API, so you can run everything without access to any private system.

<!-- TODO: add a screenshot of a real HTML or Allure report here -->
<!-- TODO: add the GitHub Actions status badge once the workflow is in place -->

## Features

**Test generation (LLM-assisted)**
- Providers: Ollama (local), OpenAI, DeepSeek
- Test types: positive, negative, boundary, security
- Output: ready-to-run pytest files, driven by JSON test data

**Failure triage and fix suggestions**
- Analyzes failed tests and proposes fix strategies with a confidence score
- Interactive mode (default recommendation): you confirm each change
- Automatic mode: applies changes without confirmation, so use it only on throwaway data
- Rule-based fallback when no LLM is available
- Backs up original files and writes a fix analysis report

**Framework basics**
- Multi-environment config (dev / test / prod) via YAML
- Test data loader and selector (filter by tag, priority, category, environment)
- HTTP client with timeout and retry, plus auth and file-upload helpers
- Reports: pytest-html and Allure

## Project structure

```
api-automation-framework/
├── ai_agent/        # LLM providers (Ollama, OpenAI, DeepSeek), case generator, test fixer
├── core/            # HTTP client with retry, auth manager, file uploader
├── config/          # Settings and environments.yaml
├── test_data/       # Loader, selector, per-environment data (e.g. dev/petstore)
├── test_cases/      # conftest.py and generated test_*.py files
├── utils/           # Assertions, logging, reporting helpers
├── prompts/         # Prompt templates: positive, negative, boundary, security
├── specs/           # API specs (example: petstore)
├── tools/           # CLI: generate_cases.py, intelligent_fix.py, run_tests.py
└── reports/         # HTML reports, Allure results, fix analysis
```

## Quick start

Requirements: Python 3.10+. Optional: Ollama for local models, or an OpenAI / DeepSeek API key.

```bash
git clone https://github.com/raissazhang0108-droid/api-automation-framework.git
cd api-automation-framework

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then add your own keys; never commit .env
```

### 1. Generate test cases

```bash
python tools/generate_cases.py generate \
  --provider ollama \
  --model llama3.2 \
  --spec-file specs/petstore/POST__pet.json \
  --type positive \
  --count 10
```

### 2. Run tests with a report

```bash
pytest --env=dev test_cases/test_post_pet_positive.py -v \
  --html=reports/html/report.html --self-contained-html
```

### 3. Review failures and fix suggestions

```bash
python tools/intelligent_fix.py \
  --test-file test_cases/test_post_pet_positive.py \
  --provider ollama --interactive
```

## Example: negative tests against Petstore

```bash
python tools/generate_cases.py generate \
  --spec-file specs/petstore/POST__pet.json --type negative --count 5

pytest test_cases/test_post_pet_negative.py -v
# FAILED TC-NEG-001: expected 400, got 200
# FAILED TC-NEG-002: expected 400, got 200
```

Here the API accepted input that the test expects it to reject. Before accepting any suggested fix, decide what the failure means:

- If the spec says the input must be rejected, this is a **defect in the API**. Keep the test, record the defect, and do not change the expected result to make the test pass.
- If the spec is silent or the test expectation was wrong, update the expectation, and ideally clarify the spec.

The fixer suggests a repair strategy with a confidence score. It does not know your business rules, which is why interactive review is the recommended mode.

## Fix suggestion output

```json
{
  "failure_type": "status_mismatch",
  "root_cause": "API accepted data that the test expects to be rejected",
  "fix_strategies": [
    {"strategy": "convert_test_type", "confidence": 0.95,
     "description": "Convert to positive test case"},
    {"strategy": "update_expectation", "confidence": 0.7,
     "description": "Update expected status code"}
  ],
  "recommended_strategy": 0
}
```

Note: a high confidence score means the model is confident about the *mechanical* fix, not that the fix is *correct* from a product point of view.

## Configuration

`config/environments.yaml`:

```yaml
dev:
  api:
    base_url: https://petstore.swagger.io/v2
    timeout: 30
    retry_count: 3
test:
  api:
    base_url: https://test-api.example.com
    timeout: 60
```

Providers:

```bash
# Local model
ollama pull llama3.2 && ollama serve

# OpenAI (put the key in .env, which is git-ignored)
OPENAI_API_KEY=your-key-here
```

## Selecting test data

```python
from test_data.selector import select

cases = (
    select()
    .from_category("pet")
    .with_tags(["positive"])
    .with_priority([0, 1])
    .for_environment()
    .get()
)
```

```python
import pytest
from test_data.selector import select

@pytest.mark.parametrize("test_case", select().from_category("pet").with_tags(["positive"]).get())
def test_api(api_client, test_case):
    response = api_client.request(
        test_case.api.method.value, test_case.api.endpoint, json=test_case.data
    )
    assert response.status_code == test_case.expected.status_code
```

## Running tests

```bash
pytest --env=dev -v                       # everything
pytest --env=dev -m smoke -v              # by marker
pytest --env=dev --alluredir=reports/allure-results && allure serve reports/allure-results
```

## CLI reference

```bash
python tools/generate_cases.py generate --provider {ollama|openai|deepseek} --model MODEL \
  --spec-file PATH --type {positive|negative|boundary|security|all} --count N --output-dir DIR

python tools/intelligent_fix.py --test-file FILE --provider {ollama|openai|deepseek} \
  --model MODEL {--interactive|--auto} --env {dev|test|prod}

python tools/run_tests.py run --env {dev|test|prod} --test-dir DIR --markers "smoke and p0" --parallel
```

## Security tests

Generated security cases cover SQL injection, NoSQL injection, XSS, path traversal, command injection, and authorization bypass. Run them only against systems you are authorized to test. The Petstore demo API is intended for this kind of practice.

## Roadmap

- [ ] GitHub Actions workflow running the suite on every push
- [ ] Docker image
- [ ] GraphQL support

## Author

Raissa Zhang, QA engineer. raissazhang0108@gmail.com
