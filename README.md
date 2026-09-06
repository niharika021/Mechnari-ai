# ⚙️ Mechnari.ai - Enterprise AI DFMEA Risk Copilot

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-Google%20Gemini%201.5%20Flash-4285F4.svg)](https://deepmind.google/technologies/gemini/)
[![Database](https://img.shields.io/badge/Database-Google%20Cloud%20BigQuery-669DF6.svg)](https://cloud.google.com/bigquery)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Mechnari.ai** is an enterprise-grade AI DFMEA (Design Failure Mode and Effects Analysis) Risk Copilot built for complex manufacturing systems (such as 1,000+ part agricultural and heavy machinery tractors). Powered by **Google Gemini 1.5 Flash** (via `google-genai`), **Pandas**, **Streamlit**, and **Google Cloud BigQuery**, Mechnari cuts manual DFMEA processing time from **4,000+ manual engineering hours down to under 4 hours**.

---

## ⚡ Key Architecture & Features

### 1. 🧮 Deterministic Pandas Merge & RPN Calculation Engine
- **3-Way CSV Data Merge**: Automatically merges three structured local CSV datasets on `part_id`:
  - `data/bom_package_hierarchy.csv`: Systems, sub-packages, item references, elementary functions, and materials.
  - `data/material_master.csv`: Physical properties, yield strength, thermal limits, elastomeric ratings, and CNH drawing spec references.
  - `data/historical_field_issues.csv`: 8D warranty logs, failure modes, root causes, $S$, $O$, $D$, and recommended action directives.
- **Mathematical RPN Calculation**:
  $$RPN = \text{Severity (S)} \times \text{Occurrence (O)} \times \text{Detection (D)}$$
- **Deterministic Risk Tier Matrix**:
  - 🔴 **Critical Risk** ($RPN \ge 200$ or $S \ge 9$): Requires mandatory executive review.
  - 🟠 **High Risk** ($120 \le RPN < 200$): Design optimization & mitigation required.
  - 🟡 **Medium Risk** ($60 \le RPN < 120$): Process/inspection tweak suggested.
  - 🟢 **Low Risk** ($RPN < 60$): Acceptable operational margin.

### 2. 🛡️ Management-by-Exception Executive Dashboard
- **1-Click Batch Approval**: Lead engineers can batch-approve all non-critical components ($RPN < 200$) in **one click** using the `⚡ Batch Approve Low/Medium Risk Items` button.
- **Critical Outlier Isolation**: High-risk components ($RPN \ge 200$) are isolated into dedicated review cards featuring material properties, 8D warranty grounding, and AI action directives.
- **Structured Interactive Matrix**: Displaying Part ID, Package, Item Reference, Function, Material Type, Failure Mode, $S, O, D, RPN$, Risk Tier, Action Items, and Approval Status with CSV export capabilities.

### 3. 🤖 Interactive Gemini AI Copilot (`google-genai`)
- **Component Deep-Dive Q&A**: Select any component from the 50-part catalog and query Gemini 1.5 Flash: *"Why did this component receive this risk score, and what are the detailed design mitigation steps?"*
- **Practical Engineering Directives**: Generates specific material upgrades (e.g. NBR to FKM Fluoroelastomer), geometry redesigns (e.g. 4.5mm fillet radii, 3mm stiffening gussets), and validation test mandates (1,000-hour impulse shock test at 135°C under 20G RMS vibration).

---

## 🏗️ System Architecture

```mermaid
graph TD
    User([Lead Mechanical / Reliability Engineer]) <--> UIView[Streamlit Dashboard - app.py]
    
    subgraph Deterministic Data Engine (Pandas)
        CSV1[(bom_package_hierarchy.csv)] -->|Merge on part_id| MergeEngine[Pandas Inner Merge Engine]
        CSV2[(material_master.csv)] -->|Merge on part_id| MergeEngine
        CSV3[(historical_field_issues.csv)] -->|Merge on part_id| MergeEngine
        
        MergeEngine -->|Mathematical Calculation| RPNEngine[RPN Engine: S x O x D]
        RPNEngine -->|Deterministic Tiers| RiskMatrix[Risk Matrix: Critical / High / Med / Low]
    end
    
    subgraph Management-by-Exception & AI Layer (agents.py)
        RiskMatrix -->|RPN >= 200| OutlierView[Critical Outlier Isolation Cards]
        RiskMatrix -->|RPN < 200| BatchApproval[1-Click Batch Approval Engine]
        
        UIView <-->|Component Q&A Deep-Dive| GeminiSDK[Google GenAI / Gemini 1.5 Flash API]
    end
    
    subgraph Cloud Infrastructure
        GeminiSDK <-->|LLM Inference| Gemini[Google Gemini 1.5 Flash Model]
        UIView <-->|SQL DDL Schema| BigQuery[Google Cloud BigQuery]
    end
```

---

## 📦 Subsystem Packages (50-Part Master Dataset)

The repository includes 50 pre-packaged heavy agricultural tractor components across 5 major subsystem packages:

1. ⛽ **Fuel Routings** (Hoses, shutoff valves, high-pressure rail lines, clamps, filter brackets)
2. ❄️ **AC Routings** (Refrigerant suction hoses, swaged aluminum tubes, compressor brackets, HNBR O-rings)
3. 🚜 **Hydraulic Steering Routings** (High-pressure flex hoses, forged steering arms, swivel adapters, priority valves)
4. 🌡️ **Engine Cooling Routings** (Radiator hoses, expansion tank lines, thermostat clamps, turbo hard lines)
5. ⚡ **Pneumatic & Electrical Routings** (Trailer brake lines, harness conduits, battery cable clamps, ABS guards)

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python 3.10+** (Python 3.13 tested)
- **Google AI Studio API Key** ([Get key here](https://aistudio.google.com/))

### 1. Clone the Repository

```bash
git clone https://github.com/niharika021/Mechnari-ai.git
cd Mechnari-ai
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root folder:

```env
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GOOGLE_API_KEY=your_google_ai_studio_api_key_here
```

### 4. Regenerate Mock CSV Datasets (Optional)

```bash
py generate_csv_data.py
```

### 5. Launch the Streamlit Dashboard

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 📁 Repository Structure

```
Mechnari-ai/
├── README.md                   # Enterprise Project Documentation
├── .gitignore                  # Security & environment exclusion rules
├── requirements.txt            # Python dependencies (google-genai, streamlit, pandas)
├── app.py                      # Streamlit dashboard & Management-by-Exception UI
├── agents.py                   # Multi-Agent logic & Gemini AI Copilot handlers
├── generate_csv_data.py        # 50-part mock CSV dataset generator script
├── schema.sql                  # BigQuery SQL DDL schema scripts
└── data/                       # 50-part CSV Datasets
    ├── bom_package_hierarchy.csv
    ├── material_master.csv
    └── historical_field_issues.csv
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🤝 Contact & Contributions

Created with ❤️ by **Niharika Yadav** - [@niharika021](https://github.com/niharika021)  
Repository: [https://github.com/niharika021/Mechnari-ai](https://github.com/niharika021/Mechnari-ai)
