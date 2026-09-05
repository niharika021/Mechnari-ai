# ⚙️ Mechnari.ai - AI Mechanical Engineering Copilot & Mentor

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-Google%20Gemini%202.5%20Flash-4285F4.svg)](https://deepmind.google/technologies/gemini/)
[![Database](https://img.shields.io/badge/Database-Google%20Cloud%20BigQuery-669DF6.svg)](https://cloud.google.com/bigquery)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Mechnari.ai** is an agentic AI engineering workspace designed to empower mechanical engineers, DFMEA facilitators, and design teams. Powered by **Google Gemini 2.5 Flash**, **Streamlit**, and **Google Cloud BigQuery**, Mechnari features two specialized intelligent agents:

1. 🛡️ **Mechnari Copilot**: Automated DFMEA (Design Failure Mode and Effects Analysis) Risk Evaluator & Engineering Change Order (ECO) Generator.
2. 🎓 **Mechnari Mentor**: GD&T (Geometric Dimensioning and Tolerancing) Assistant & Technical Interview Practice Simulator based on ASME Y14.5 standards.

---

## 🌟 Core Features

### 🛡️ 1. DFMEA Risk Copilot (`Mechnari Copilot`)
- **Automated Risk Priority Number (RPN) Calculation**:
  $$RPN = \text{Severity (S)} \times \text{Occurrence (O)} \times \text{Detection (D)}$$
- **Dynamic Risk Severity Matrix**:
  - 🔴 **Critical Risk** ($RPN \ge 200$ or $Severity \ge 9$): Mandatory ECO triggered immediately.
  - 🟠 **High Risk** ($RPN \ge 120$): Design optimization & mitigation required.
  - 🟡 **Medium Risk** ($RPN \ge 60$): Inspection & process update suggested.
  - 🟢 **Low Risk** ($RPN < 60$): Acceptable design margin.
- **Material Limit Verification Engine**: Evaluates working stress ($\sigma_{\text{working}}$) and operating temperature ($T_{\text{operating}}$) against:
  - Yield Strength ($\sigma_y$) & Ultimate Tensile Strength ($\sigma_u$)
  - Thermal Threshold ($T_{\text{max}}$) & Endurance Limit ($\sigma_e$)
  - Required Factor of Safety ($FoS$)
- **Automated ECO Generator**: Generates formal Engineering Change Orders complete with redesign guidance, root cause failure analysis, and material selection recommendations.

### 🎓 2. AI Mechanical Mentor & Interviewer (`Mechnari Mentor`)
- **ASME Y14.5 GD&T Expert**: Instant technical explanations for Datum Reference Frames (DRF), Maximum Material Condition (MMC), Least Material Condition (LMC), Position Tolerancing, Profile of a Surface, and Total Indicated Runout (TIR).
- **Technical Mock Interview Simulator**: Select real-world engineering categories (GD&T, Strength of Materials, Thermodynamics, Manufacturing Processes, DFMEA), receive candidate response evaluation, and generate a 10-point scored evaluation report with ideal answers.

### 🗄️ 3. BigQuery Mechanical Catalog
- Structured DDL schemas (`schema.sql`) for standard aerospace, automotive, and industrial engineering materials (`materials_master`) and common mechanical failure modes (`failure_modes_catalog`).

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    User([Mechanical Engineer / User]) <--> UIView[Streamlit Web UI - app.py]
    
    subgraph Multi-Agent System (agents.py)
        UIView -->|DFMEA Risk Queries| DFMEAAgent[Mechnari Copilot Agent]
        UIView -->|GD&T & Interview Queries| MentorAgent[Mechnari Mentor Agent]
        
        DFMEAAgent -->|RPN Calculation| RPNEngine[RPN Engine: S x O x D]
        DFMEAAgent -->|Material Limit Check| MatEngine[Material Limit & FoS Evaluator]
        DFMEAAgent -->|Prompt & Context| GenAI[Google GenAI / Gemini API]
        
        MentorAgent -->|Mock Interview Grading| ScoringEngine[Evaluation & Feedback Engine]
        MentorAgent -->|Prompt & Context| GenAI
    end
    
    subgraph Cloud Infrastructure
        GenAI <-->|LLM Inference| Gemini[Google Gemini 2.5 Flash API]
        UIView <-->|SQL DDL & Catalog| BigQuery[Google Cloud BigQuery]
        BigQuery --> Table1[(materials_master)]
        BigQuery --> Table2[(failure_modes_catalog)]
    end
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python 3.10+** (Python 3.13 recommended)
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

### 3. Configure API Credentials

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GOOGLE_API_KEY=your_google_ai_studio_api_key_here
```

### 4. Setup BigQuery Schema (Optional Cloud Setup)

Run `schema.sql` in Google Cloud Console BigQuery Query Editor or via `gcloud`:

```bash
bq query --use_legacy_sql=false < schema.sql
```

### 5. Launch the Application

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 📁 Repository Structure

```
Mechnari-ai/
├── README.md          # Comprehensive Project Documentation
├── .gitignore         # Git ignore rules for security & environment files
├── requirements.txt   # Required Python dependencies
├── app.py             # Streamlit application UI & navigation
├── agents.py          # Gemini AI agent definitions & engineering logic
└── schema.sql         # BigQuery SQL DDL and sample dataset scripts
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🤝 Contact & Contributions

Created with ❤️ by **Niharika Yadav** - [@niharika021](https://github.com/niharika021)  
Repository: [https://github.com/niharika021/Mechnari-ai](https://github.com/niharika021/Mechnari-ai)
