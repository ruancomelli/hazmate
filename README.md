# Hazmat Detection System - MercadoLibre GenAI Challenge

![Project Hero](assets/hero.png)

<div align="center">
  <h1>Hazmate</h1>
  <p>Your AI-powered hazmat detection teammate.</p>

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

**🎯 Take-Home Challenge Solution for GenAI Software Engineer Position**  
**📋 Full Technical Report**: [REPORT.md](REPORT.md)  
**🔗 Predictions**: [Google Drive CSV](https://drive.google.com/file/d/1d7pFJNltG0GuLHyaE-UGXxPfXY7zwdKQ/view?usp=sharing)

---

## 🚀 Challenge Overview

MercadoLibre faces a critical logistics challenge: **not all products can be shipped through their standard network**. Items containing hazardous materials (Hazmat) require special handling, but this information isn't structured in their systems. The challenge was to build an AI system that can:

- **Classify products as Hazmat or non-Hazmat** from unstructured data (titles, descriptions, attributes)
- **Provide clear explanations** for each classification decision
- **Design a production-ready architecture** that can scale to millions of products
- **Demonstrate accuracy** on real MercadoLibre product data

## 🏆 Key Achievements

✅ **100,000 Real Products Collected** - Successfully gathered diverse product data from MercadoLibre's API  
✅ **97.3% Accuracy on Hazmat Items** - Achieved high precision on definitive hazmat items without fine-tuning  
✅ **Smart Evaluation Strategy** - Used MercadoLibre's own attributes as ground truth labels  
✅ **RAG Enhancement** - Implemented knowledge base for domain-specific examples  
✅ **Complete Documentation** - Professional technical report with architecture diagrams

## 🛠️ Technical Stack

- **🧠 AI Models**: Model-agnostic, though tested with Gemini 2.5 Flash Lite
- **🔍 RAG**: ChromaDB + LangChain for knowledge base retrieval
- **🔐 Authentication**: OAuth 2.0 with automatic token refresh
- **⚡ Framework**: PydanticAI for structured outputs, FastAPI-style async
- **📊 Data Processing**: Async batch processing with parallel execution
- **🎨 CLI**: Rich terminal UI with progress tracking and tables

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+** (managed with [uv](https://docs.astral.sh/uv/))
- **API Keys**: Google, OpenAI, or Anthropic (depending on model choice)
- **MercadoLibre App**: Client ID and secret for data collection

### Installation

```bash
# Clone the repository
git clone https://github.com/ruancomelli/hazmate.git
cd hazmate

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify uv installation
uv --version
```

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required for data collection:
CLIENT_ID=your_mercadolibre_client_id
CLIENT_SECRET=your_mercadolibre_client_secret
REDIRECT_URL=https://wealthy-optionally-anemone.ngrok-free.app/callback

# Required for classification (choose one or more):
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### OAuth Setup (for Data Collection)

```bash
# Terminal 1: Start the OAuth redirect server
uv run -m hazmate.redirect_server

# Terminal 2: Expose server with ngrok
bash scripts/start_ngrok.sh
```

## 🎯 Usage Examples

### 1. **Quick Classification Demo**

```bash
# Basic hazmat classification
uv run examples/agents/agent.py basic-usage -m "google-gla:gemini-2.5-flash-lite-preview-06-17"

# RAG-enhanced classification
uv run examples/agents/agent.py rag-usage -m "openai:gpt-4o-mini"

# Compare both approaches
uv run examples/agents/agent.py compare-agents -m "google-gla:gemini-2.5-flash-lite-preview-06-17"
```

### 2. **Data Collection**

```bash
# Collect 1,000 balanced samples (good for testing)
uv run -m hazmate.input_datasets \
    --target-size 1000 \
    --goal balance \
    --output-name "sample_dataset.jsonl"

# Collect 100,000 items (full dataset)
uv run -m hazmate.input_datasets \
    --target-size 100_000 \
    --goal speed \
    --output-name "full_dataset.jsonl"
```

### 3. **Batch Classification**

```bash
# Classify products with basic LLM
uv run -m hazmate.agent \
    -m "google-gla:gemini-2.5-flash-lite-preview-06-17" \
    -i "data/inputs/sample_dataset.jsonl" \
    -o "data/predictions/sample_predictions.jsonl" \
    --batch-size 50 \
    --parallel-batches 5

# Convert to CSV format
uv run scripts/convert_jsonl_to_csv.py \
    "data/predictions/sample_predictions.jsonl" \
    "data/predictions/sample_predictions.csv"
```

### 4. **Evaluation**

```bash
# Generate ground truth from product attributes
uv run scripts/filter_hazmat_items.py \
    -i "data/inputs/sample_dataset.jsonl" \
    -o "data/ground_truth/hazmat_items.jsonl"

# Evaluate predictions accuracy
uv run scripts/evaluate_on_hazmat.py \
    -g "data/ground_truth/hazmat_items.jsonl" \
    -p "data/predictions/sample_predictions.jsonl" \
    --detailed
```

## 📚 Documentation

- **[📋 Technical Report](REPORT.md)** - Complete methodology, architecture, and results
- **[🎯 Examples](examples/)** - Hands-on demonstrations of all features
- **[🔧 Scripts](scripts/)** - Utility tools for data processing and evaluation

---

**Built with ❤️ and ☕ by [Ruan Comelli](https://github.com/ruancomelli) for MercadoLibre's GenAI Team**

_(This README was generated by AI and will be updated manually)_
