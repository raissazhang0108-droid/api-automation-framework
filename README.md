# AI-Powered API Test Automation Framework

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![pytest](https://img.shields.io/badge/pytest-7.4+-green.svg)](https://pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An enterprise-grade API test automation framework powered by AI that automatically generates test cases, intelligently fixes failures, and provides comprehensive reporting.

## 🌟 Key Features

### 🤖 AI-Driven Test Generation
- **Multiple AI Providers**: Supports Ollama, OpenAI, and DeepSeek
- **Comprehensive Test Types**:
  - ✅ Positive tests for happy path validation
  - ❌ Negative tests for error handling
  - 📏 Boundary tests for edge cases
  - 🔒 Security tests for vulnerability detection
- **Auto-generated Test Files**: Creates pytest-compatible test files automatically

### 🔧 Intelligent Test Fixing ⭐
- **AI Failure Analysis**: Understands why tests fail
- **Smart Fix Suggestions**: Provides multiple repair strategies with confidence scores
- **Auto-repair**: Automatically updates test data based on actual API behavior
- **Detailed Reports**: Generates comprehensive fix analysis reports

### 📊 Rich Reporting
- **HTML Reports**: Beautiful, self-contained test reports
- **Allure Integration**: Enterprise-grade test reporting
- **Custom Styling**: Tailored report layouts with environment info

### 🎯 Flexible Architecture
- **Multi-environment Support**: dev, test, prod configurations
- **Dynamic Data Selection**: Powerful test data filtering
- **Modular Design**: Easy to extend and customize

---

## 📁 Project Structure
```
api-automation-framework/
├── ai_agent/                    # AI agent modules
│   ├── base_agent.py           # Base AI agent
│   ├── ollama_agent.py         # Ollama implementation
│   ├── openai_agent.py         # OpenAI implementation
│   ├── deepseek_agent.py       # DeepSeek implementation
│   ├── case_generator.py       # Test case generator
│   └── test_fixer_agent.py     # Intelligent test fixer ⭐
│
├── core/                        # Core functionality
│   ├── http_client.py          # HTTP client with retry
│   ├── auth_manager.py         # Authentication manager
│   └── file_uploader.py        # File upload handler
│
├── config/                      # Configuration
│   ├── settings.py             # Settings manager
│   └── environments.yaml       # Environment configs
│
├── test_data/                   # Test data
│   ├── loader.py               # Data loader
│   ├── selector.py             # Data selector
│   └── dev/petstore/           # Environment-specific data
│
├── test_cases/                  # Test cases
│   ├── conftest.py             # Pytest configuration
│   └── test_*.py               # Auto-generated tests
│
├── utils/                       # Utilities
│   ├── assertions.py           # Assertion helpers
│   ├── logger.py               # Logging utilities
│   └── reporter.py             # Reporting tools
│
├── prompts/                     # AI prompt templates
│   ├── positive_cases.txt      # Positive test prompts
│   ├── negative_cases.txt      # Negative test prompts
│   ├── boundary_cases.txt      # Boundary test prompts
│   └── security_cases.txt      # Security test prompts
│
├── specs/                       # API specifications
│   └── petstore/               # Example: Petstore API
│
├── tools/                       # CLI tools
│   ├── generate_cases.py      # Test generation tool
│   ├── intelligent_fix.py     # AI-powered test fixer ⭐
│   └── run_tests.py           # Test runner
│
└── reports/                     # Test reports
    ├── html/                   # HTML reports
    ├── allure-results/         # Allure data
    └── fix_analysis.md         # Fix analysis reports
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip or poetry
- (Optional) Ollama for local AI
- (Optional) OpenAI API key

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/api-automation-framework.git
cd api-automation-framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Basic Usage

#### 1. Generate Test Cases
```bash
# Generate positive test cases
python tools/generate_cases.py generate \
  --provider ollama \
  --model llama3.2 \
  --spec-file specs/petstore/POST__pet.json \
  --type positive \
  --count 10

# Output:
# ✅ Generated 10 test cases
# ✅ Test file created: test_cases/test_post_pet_positive.py
```

#### 2. Run Tests
```bash
# Run tests with HTML report
pytest --env=dev test_cases/test_post_pet_positive.py -v \
  --html=reports/html/report.html \
  --self-contained-html

# Open report
open reports/html/report.html
```

#### 3. Intelligent Fix (if failures occur)
```bash
# Analyze and fix failed tests with AI
python tools/intelligent_fix.py \
  --test-file test_cases/test_post_pet_positive.py \
  --provider ollama

# Interactive mode - choose fix strategies
# Or use --auto for automatic fixing
```

---

## 💡 Complete Workflow Example

### Scenario: Testing Petstore API
```bash
# Step 1: Generate negative tests (expect failures)
python tools/generate_cases.py generate \
  --spec-file specs/petstore/POST__pet.json \
  --type negative \
  --count 5

# Step 2: Run tests
pytest test_cases/test_post_pet_negative.py -v

# Output:
# ❌ FAILED: TC-NEG-001 - Expected 400, got 200
# ❌ FAILED: TC-NEG-002 - Expected 400, got 200

# Step 3: Intelligent fix
python tools/intelligent_fix.py \
  --test-file test_cases/test_post_pet_negative.py

# AI Analysis:
# 📋 TC-NEG-001: "Empty data should return 400"
#    Root cause: API accepted invalid data
#    🌟 Strategy: Convert to positive test (95% confidence)
#    
# Fix applied: 400 → 200, tags: negative → positive

# Step 4: Re-run tests
pytest test_cases/test_post_pet_negative.py -v
# ✅ All tests passed!
```

---

## 🤖 Intelligent Test Fixing System

This is the **core innovation** of the framework.

### How It Works

1. **Automatic Failure Detection**
   - Runs pytest and captures failure information
   - Extracts error details and response data

2. **AI Deep Analysis**
```json
   {
     "failure_type": "status_mismatch",
     "root_cause": "API accepted data that should be rejected",
     "fix_strategies": [
       {
         "strategy": "convert_test_type",
         "confidence": 0.95,
         "description": "Convert to positive test case"
       },
       {
         "strategy": "update_expectation",
         "confidence": 0.7,
         "description": "Update expected status code"
       }
     ],
     "recommended_strategy": 0
   }
```

3. **Smart Fix Suggestions**
   - Multiple repair strategies ranked by confidence
   - Considers business context and API behavior
   - Provides detailed reasoning for each suggestion

4. **Automatic Application**
   - Updates test data files
   - Backs up original files
   - Re-runs tests to verify fixes
   - Generates fix analysis reports

### Modes

- **Interactive**: Manual confirmation for each fix
- **Automatic**: Fully automated repair
- **Rule-based**: Fallback when AI is unavailable

---

## 🔧 Configuration

### Environment Configuration

Edit `config/environments.yaml`:
```yaml
dev:
  api:
    base_url: https://api.example.com
    timeout: 30
    retry_count: 3
  auth:
    type: bearer
    token_endpoint: /auth/login
  features:
    debug_mode: true

test:
  api:
    base_url: https://test-api.example.com
    timeout: 60
  # ... more configs

prod:
  api:
    base_url: https://api.example.com
    timeout: 120
  # ... more configs
```

### AI Provider Setup

#### Using Ollama (Local)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull model
ollama pull llama3.2

# Start service
ollama serve
```

#### Using OpenAI
```bash
# Set API key in .env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Use in commands
python tools/generate_cases.py generate \
  --provider openai \
  --model gpt-4 \
  --spec-file specs/api.json
```

---

## 📚 Advanced Features

### Custom Test Data Selection
```python
from test_data.selector import select

# Select by tags
cases = select().with_tags(["smoke", "p0"]).get()

# Select by priority
cases = select().with_priority(0).get()

# Select by environment
cases = select().for_environment("prod").get()

# Chain selectors
cases = (
    select()
    .from_category("user")
    .with_tags(["positive"])
    .with_priority([0, 1])
    .for_environment()
    .get()
)
```

### Dynamic Test Parametrization
```python
import pytest
from test_data.selector import select

@pytest.mark.parametrize(
    "test_case",
    select().from_category("pet").with_tags(["positive"]).get()
)
def test_api(api_client, test_case):
    response = api_client.request(
        test_case.api.method.value,
        test_case.api.endpoint,
        json=test_case.data
    )
    assert response.status_code == test_case.expected.status_code
```

### Custom AI Prompts

Create your own prompt templates in `prompts/`:
```text
prompts/
├── positive_cases.txt
├── negative_cases.txt
├── boundary_cases.txt
├── security_cases.txt
└── custom_cases.txt  # Your custom prompts
```

---

## 🧪 Testing
```bash
# Run all tests
pytest --env=dev -v

# Run specific test file
pytest --env=dev test_cases/test_api.py -v

# Run with markers
pytest --env=dev -m smoke -v

# Generate HTML report
pytest --env=dev -v \
  --html=reports/html/report.html \
  --self-contained-html

# Generate Allure report
pytest --env=dev --alluredir=reports/allure-results
allure serve reports/allure-results
```

---

## 📖 CLI Reference

### Generate Test Cases
```bash
python tools/generate_cases.py generate \
  --provider {ollama|openai|deepseek} \
  --model MODEL_NAME \
  --spec-file PATH_TO_SPEC \
  --type {positive|negative|boundary|security|all} \
  --count COUNT \
  --output-dir OUTPUT_DIR
```

### Intelligent Fix
```bash
python tools/intelligent_fix.py \
  --test-file TEST_FILE_PATH \
  --provider {ollama|openai|deepseek} \
  --model MODEL_NAME \
  {--interactive|--auto} \
  --env {dev|test|prod}
```

### Run Tests
```bash
python tools/run_tests.py run \
  --env {dev|test|prod} \
  --test-dir TEST_DIR \
  --markers "smoke and p0" \
  --parallel
```

---

## 🎨 Report Customization

Customize HTML reports in `test_cases/conftest.py`:
```python
def pytest_html_report_title(report):
    """Custom report title"""
    report.title = "My API Test Report"

def pytest_html_results_summary(prefix, summary, postfix):
    """Custom summary section"""
    # Add custom content
    pass
```

---

## 🔒 Security Testing

The framework includes built-in security test generation:
```bash
# Generate security tests
python tools/generate_cases.py generate \
  --type security \
  --spec-file specs/api.json

# Tests include:
# - SQL Injection
# - NoSQL Injection
# - XSS Attacks
# - Path Traversal
# - Command Injection
# - Authorization Bypass
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run linters
flake8 .
black .
mypy .

# Run tests
pytest tests/ -v
```

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [pytest](https://pytest.org/) - Testing framework
- [Ollama](https://ollama.ai/) - Local AI inference
- [OpenAI](https://openai.com/) - AI capabilities
- [Allure](https://docs.qameta.io/allure/) - Test reporting

---

## 📧 Contact

- **Author**: Raissa Zhang
- **Email**: raissazhang0108@gmail.com
---

## 🗺️ Roadmap

- [ ] Support for GraphQL APIs
- [ ] Integration with CI/CD platforms (Jenkins, GitLab CI, GitHub Actions)
- [ ] Performance testing capabilities
- [ ] API mocking support
- [ ] Real-time test monitoring dashboard
- [ ] Multi-language support for reports
- [ ] Docker containerization
- [ ] Cloud deployment support

---

## ⭐ Star History

If you find this project helpful, please consider giving it a star! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/api-automation-framework&type=Date)](https://star-history.com/#yourusername/api-automation-framework&Date)

---

**Made with ❤️ and 🤖 AI**

*Elevating API testing from automation to intelligence*
```

---

## 额外文件

### LICENSE (MIT)
```
MIT License

Copyright (c) 2024 Raissa

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
