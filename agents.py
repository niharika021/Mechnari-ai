"""
Mechnari.ai - Multi-Agent DFMEA Risk Copilot Engine
=====================================================
Specialized Multi-Agent architecture for complex manufacturing systems (e.g., 1,000+ part agricultural & heavy tractors).

Reads structured mock CSV datasets:
1. data/bom_package_hierarchy.csv (50 parts across 5 system packages)
2. data/material_master.csv (50 engineering specs)
3. data/historical_field_issues.csv (50 historical 8D warranty RAG entries)
"""

import os
import csv
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MechnariAgents")

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Gemini SDK Setup with graceful fallback support
try:
    from google import genai
    from google.genai import types
    USE_NEW_GENAI = True
except ImportError:
    try:
        import google.generativeai as genai
        USE_NEW_GENAI = False
    except ImportError:
        genai = None
        USE_NEW_GENAI = False


def call_gemini(prompt: str, system_instruction: Optional[str] = None) -> str:
    """Queries Google Gemini model using google-genai or google.generativeai with corporate SSL fallback."""
    if not genai or not API_KEY:
        logger.warning("Gemini API key not found. Utilizing rule-based engineering synthesis.")
        return ""

    try:
        if USE_NEW_GENAI:
            client = genai.Client(
                api_key=API_KEY,
                http_options=types.HttpOptions(client_args={'verify': False})
            )
            config = types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=system_instruction
            ) if system_instruction else types.GenerateContentConfig(temperature=0.2)
            
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=config
            )
            return response.text.strip()
        else:
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_instruction)
            response = model.generate_content(prompt)
            return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API invocation exception: {e}")
        return ""


# =====================================================================
# DYNAMIC CSV DATASET LOADERS (50 PARTS ACROSS 3 CSV FILES)
# =====================================================================

def load_bom_packages_from_csv() -> Dict[str, List[Dict[str, Any]]]:
    """Loads part hierarchy from data/bom_package_hierarchy.csv grouped by system_package."""
    file_path = os.path.join("data", "bom_package_hierarchy.csv")
    packages: Dict[str, List[Dict[str, Any]]] = {}

    if os.path.exists(file_path):
        try:
            with open(file_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pkg = row.get("system_package", "General Routings")
                    part_item = {
                        "part_id": row.get("part_id"),
                        "part_name": row.get("item_reference"),
                        "subsystem": pkg,
                        "material": row.get("material_type"),
                        "elementary_function": row.get("elementary_function")
                    }
                    if pkg not in packages:
                        packages[pkg] = []
                    packages[pkg].append(part_item)

            # Add an 'All Subsystem Packages (50 Parts)' aggregated option
            all_parts = []
            for pkg_name, parts in packages.items():
                all_parts.extend(parts)
            packages["Complete Heavy Tractor Subsystem (50 Parts Master BOM)"] = all_parts
            return packages
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")

    # Fallback default if CSV is missing
    return {
        "Fuel Routings": [
            {
                "part_id": "TR-FL-001",
                "part_name": "Hose 3: Fuel Cooler Supply Line",
                "subsystem": "Fuel Routings",
                "material": "Nitrile Rubber NBR with Aramid Braid",
                "elementary_function": "Transport fuel around circuit without thermal leaks"
            }
        ]
    }


def load_historical_rag_from_csv() -> Dict[str, Dict[str, Any]]:
    """Loads historical field issue 8D RAG dataset from data/historical_field_issues.csv keyed by part_id."""
    file_path = os.path.join("data", "historical_field_issues.csv")
    rag_map: Dict[str, Dict[str, Any]] = {}

    if os.path.exists(file_path):
        try:
            with open(file_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pid = row.get("part_id")
                    rag_map[pid] = {
                        "historical_grounding": f"8D Report #{pid}-8D: Historical warranty log indicates '{row.get('failure_mode')}' cause by {row.get('potential_cause')}.",
                        "failure_mode": row.get("failure_mode"),
                        "potential_cause": row.get("potential_cause"),
                        "base_severity": int(row.get("historical_severity", 5)),
                        "base_occurrence": int(row.get("historical_occurrence", 5)),
                        "base_detection": int(row.get("historical_detection", 5)),
                        "recommended_action": row.get("recommended_action")
                    }
            return rag_map
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")

    return {}


def load_material_master_from_csv() -> Dict[str, Dict[str, Any]]:
    """Loads material properties and specifications from data/material_master.csv keyed by part_id."""
    file_path = os.path.join("data", "material_master.csv")
    mat_map: Dict[str, Dict[str, Any]] = {}

    if os.path.exists(file_path):
        try:
            with open(file_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pid = row.get("part_id")
                    mat_map[pid] = {
                        "yield_strength_mpa": float(row.get("yield_strength_mpa", 200)),
                        "max_temp_limit_c": float(row.get("max_temp_limit_c", 120)),
                        "elastomeric_rating": row.get("elastomeric_rating"),
                        "drawing_spec_ref": row.get("drawing_spec_ref")
                    }
            return mat_map
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")

    return {}


# Load CSV datasets at startup
HEAVY_TRACTOR_BOM_PACKAGES = load_bom_packages_from_csv()
HISTORICAL_8D_WARRANTY_RAG = load_historical_rag_from_csv()
MATERIAL_MASTER = load_material_master_from_csv()


# =====================================================================
# AGENT CLASS IMPLEMENTATIONS
# =====================================================================

class StructureFunctionAgent:
    """Agent 1: Ingests package BOMs and assigns context-specific mechanical functions."""
    
    def process(self, part_data: Dict[str, Any], package_name: str) -> str:
        # Check if function is pre-defined in CSV
        if part_data.get("elementary_function"):
            return part_data["elementary_function"]

        part_name = part_data.get("part_name", "")
        material = part_data.get("material", "")
        subsystem = part_data.get("subsystem", "")

        prompt = f"""
        You are a Principal Mechanical Packaging Engineer specializing in heavy agricultural tractor design.
        Assign a concise, technical primary mechanical function for this component in the context of the package '{package_name}'.
        Component Name: {part_name}
        Subsystem: {subsystem}
        Material / Specs: {material}
        Output ONLY a 1-sentence engineering function description.
        """
        ai_function = call_gemini(prompt, system_instruction="You assign precise mechanical functions for agricultural tractor engineering components.")
        if ai_function:
            return ai_function

        # Deterministic Rule-Based Fallback
        if "Hose" in part_name:
            return f"Contains and routes pressurized fluid within the {subsystem} while dampening multi-axis chassis vibration."
        elif "Clamp" in part_name:
            return f"Maintains constant radial sealing force across the hose-barb interface throughout thermal expansion cycles."
        elif "Bracket" in part_name or "Mount" in part_name:
            return f"Secures component assembly to chassis structural frame under 20G peak shock loads."
        else:
            return f"Performs structural load transmission and fluid containment within the {subsystem} assembly."


class FailureRAGAgent:
    """Agent 2: Matches components against historical tractor field issues (8D logs, warranty reports)."""

    def process(self, part_id: str, part_name: str) -> Dict[str, Any]:
        record = HISTORICAL_8D_WARRANTY_RAG.get(part_id)
        if record:
            return record

        # Dynamic RAG match fallback for custom parts
        prompt = f"""
        You are a Heavy Equipment Reliability & Quality Engineer.
        Generate historical field failure grounding for this component:
        Part ID: {part_id}
        Part Name: {part_name}

        Return JSON format with keys:
        - "historical_grounding": A realistic 8D report or warranty claim reference.
        - "failure_mode": Potential failure mode.
        - "potential_cause": Root cause failure mechanism.
        - "base_severity": Integer 1-10.
        - "base_occurrence": Integer 1-10.
        - "base_detection": Integer 1-10.
        - "recommended_action": Suggested engineering action.
        """
        raw = call_gemini(prompt)
        if raw and "{" in raw:
            try:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                return json.loads(raw[start:end])
            except Exception:
                pass

        return {
            "historical_grounding": f"8D Report #{part_id}-8D: Field warranty logs indicate localized stress concentration risks under field torsional shock loads.",
            "failure_mode": "Mechanical Fatigue & Line Wear",
            "potential_cause": "High cyclic mechanical stress exceeding component fatigue limits.",
            "base_severity": 7,
            "base_occurrence": 5,
            "base_detection": 4,
            "recommended_action": "Add protective chafing sleeve and relocate away from heat sources."
        }


class DeterministicRiskEngine:
    """Agent 3: Computes RPN = Severity (S) x Occurrence (O) x Detection (D) and categorizes risk."""

    def compute_risk(self, severity: int, occurrence: int, detection: int) -> Dict[str, Any]:
        s = max(1, min(10, int(severity)))
        o = max(1, min(10, int(occurrence)))
        d = max(1, min(10, int(detection)))
        rpn = s * o * d

        # Critical risk rule: RPN >= 200 OR Severity >= 9
        is_critical = (rpn >= 200) or (s >= 9)
        
        if is_critical:
            risk_category = "🔴 CRITICAL OUTLIER"
        elif rpn >= 100:
            risk_category = "🟠 HIGH RISK"
        elif rpn >= 50:
            risk_category = "🟡 MEDIUM RISK"
        else:
            risk_category = "🟢 LOW RISK"

        return {
            "severity": s,
            "occurrence": o,
            "detection": d,
            "rpn": rpn,
            "is_critical": is_critical,
            "risk_category": risk_category
        }


class MitigationAgent:
    """Agent 4: Generates specific, practical Engineering Action Items for high-risk items (RPN >= 200 or S >= 9)."""

    def process(self, part_data: Dict[str, Any], failure_data: Dict[str, Any], risk_data: Dict[str, Any]) -> str:
        s = risk_data["severity"]
        rpn = risk_data["rpn"]
        is_critical = risk_data["is_critical"]
        part_id = part_data.get("part_id", "")
        part_name = part_data.get("part_name", "")
        material = part_data.get("material", "")
        failure_mode = failure_data.get("failure_mode", "")
        cause = failure_data.get("potential_cause", "")
        rec_action = failure_data.get("recommended_action", "")

        # For low / medium risks (< 200 RPN and S < 9), return standard baseline validation
        if not is_critical:
            return f"Standard Quality Control: Retain baseline material ({material}). Conduct standard production line leak & dimension check."

        # High risk / Critical Outlier -> Use CSV recommendation if available or query Gemini
        if rec_action:
            base_action = f"• **Action Directives**: {rec_action}\n"
        else:
            base_action = ""

        prompt = f"""
        You are a Principal Engineering Specialist in Agricultural Tractor Reliability.
        Generate specific, practical Engineering Action Items for a critical DFMEA risk.
        DO NOT generate generic formal ECO paperwork boilerplate. Give 3 bulleted actionable design engineering directives:
        - Material compound / alloy upgrades
        - Geometry redesign directives
        - Validation test mandates

        Component: {part_name} (Part ID: {part_id})
        Current Material: {material}
        Failure Mode: {failure_mode}
        Potential Cause: {cause}
        Severity: {s}/10 | Computed RPN: {rpn}
        Historical Recommendation: {rec_action}
        """
        ai_mitigation = call_gemini(prompt)
        if ai_mitigation:
            return base_action + ai_mitigation

        # Rule-based fallback for critical action items
        return (
            base_action +
            "• **Design Directive**: Determine final placement of line; add protective silicone fiberglass chafing sleeve.\n"
            "• **Material Upgrade**: Upgrade inner elastomeric liner to high-temp FKM Fluoroelastomer.\n"
            "• **Validation Mandate**: Mandate 1,000-hour impulse pressure shock test at 135°C under 20G RMS shaker vibration."
        )


# =====================================================================
# MULTI-AGENT ORCHESTRATOR PIPELINE
# =====================================================================

class DFMEAMultiAgentOrchestrator:
    """Orchestrates the 4 agents across a given heavy tractor subsystem BOM package."""

    def __init__(self):
        self.struct_agent = StructureFunctionAgent()
        self.rag_agent = FailureRAGAgent()
        self.risk_engine = DeterministicRiskEngine()
        self.mitigation_agent = MitigationAgent()

    def run_pipeline(self, package_name: str, bom_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        logger.info(f"Executing Multi-Agent DFMEA Pipeline on package: {package_name} ({len(bom_list)} components)")

        for part in bom_list:
            part_id = part.get("part_id", "TR-GEN-00")
            part_name = part.get("part_name", "Component")

            # Agent 1: Assign Contextual Mechanical Function
            function_desc = self.struct_agent.process(part, package_name)

            # Agent 2: Historical Field RAG Match (8D reports, warranty logs)
            rag_data = self.rag_agent.process(part_id, part_name)

            # Agent 3: Deterministic Risk Engine Scoring (RPN = S x O x D)
            sev = rag_data.get("base_severity", 5)
            occ = rag_data.get("base_occurrence", 5)
            det = rag_data.get("base_detection", 5)
            risk_data = self.risk_engine.compute_risk(sev, occ, det)

            # Agent 4: Practical Engineering Mitigation Generation
            action_items = self.mitigation_agent.process(part, rag_data, risk_data)

            # Fetch Material Spec Reference
            mat_info = MATERIAL_MASTER.get(part_id, {})
            drawing_ref = mat_info.get("drawing_spec_ref", "ES-GENERIC")

            # Assemble complete DFMEA record row
            row = {
                "part_id": part_id,
                "part_name": part_name,
                "subsystem": part.get("subsystem", "Tractor Subsystem"),
                "material": part.get("material", "Standard Alloy"),
                "drawing_spec_ref": drawing_ref,
                "function": function_desc,
                "potential_failure_mode": rag_data.get("failure_mode", "Mechanical Fatigue"),
                "potential_cause": rag_data.get("potential_cause", "Cyclic vibration & stress"),
                "severity": risk_data["severity"],
                "occurrence": risk_data["occurrence"],
                "detection": risk_data["detection"],
                "rpn": risk_data["rpn"],
                "risk_category": risk_data["risk_category"],
                "is_critical": risk_data["is_critical"],
                "historical_grounding": rag_data.get("historical_grounding", "N/A"),
                "action_items": action_items,
                "approval_status": "🔴 Needs Executive Review" if risk_data["is_critical"] else "⏳ Pending Batch Sign-Off"
            }
            results.append(row)

        return results


# Global convenience function
def analyze_bom_package(package_name: str) -> List[Dict[str, Any]]:
    bom_list = HEAVY_TRACTOR_BOM_PACKAGES.get(package_name, [])
    orchestrator = DFMEAMultiAgentOrchestrator()
    return orchestrator.run_pipeline(package_name, bom_list)