"""
Mechnari.ai - Multi-Agent DFMEA Risk Copilot Engine
=====================================================
Specialized Multi-Agent architecture for complex manufacturing systems (e.g., 1,000+ part agricultural & heavy tractors).

Agents:
1. Structure & Function Agent: Ingests package BOMs and assigns context-specific mechanical functions.
2. Failure & RAG Retrieval Agent: Matches components against historical tractor field issues (8D logs, warranty reports).
3. Deterministic Risk Engine: Computes RPN = Severity (S) x Occurrence (O) x Detection (D) and tags outliers.
4. Mitigation Agent: Synthesizes specific, practical Engineering Action Items for critical risks (RPN >= 200 or S >= 9).
"""

import os
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
# SAMPLE HEAVY TRACTOR SUBSYSTEM BOM PACKAGES & HISTORICAL 8D RAG CATALOG
# =====================================================================

HEAVY_TRACTOR_BOM_PACKAGES: Dict[str, List[Dict[str, Any]]] = {
    "Fuel Routing Package (1,000+ HP Tractor)": [
        {
            "part_id": "TR-FL-101",
            "part_name": "High-Pressure Fuel Rail Hose",
            "subsystem": "Fuel Delivery",
            "material": "NBR/PVC Inner, High-Tenacity Aramid Braid, EPDM Cover",
            "operating_temp_c": 120,
            "operating_pressure_bar": 15.0
        },
        {
            "part_id": "TR-FL-102",
            "part_name": "Constant-Tension Spring Hose Clamp",
            "subsystem": "Fuel Retaining",
            "material": "51CrV4 Spring Steel (Zinc-Nickel Plated)",
            "operating_temp_c": 110,
            "clamping_force_n": 850
        },
        {
            "part_id": "TR-FL-103",
            "part_name": "Fuel Filter Cast Mounting Bracket",
            "subsystem": "Structural Support",
            "material": "ADC12 Die-Cast Aluminum",
            "vibration_g_rms": 18.5,
            "mass_kg": 2.4
        },
        {
            "part_id": "TR-FL-104",
            "part_name": "Quick-Connect Nylon Fuel Line Fitting",
            "subsystem": "Fuel Coupler",
            "material": "PA66-GF30 (30% Glass Fiber Reinforced Nylon)",
            "operating_temp_c": 95,
            "operating_pressure_bar": 8.0
        }
    ],
    "AC Routing Package (Cab Climate Subsystem)": [
        {
            "part_id": "TR-AC-201",
            "part_name": "HVAC Refrigerant Suction Hose Assembly",
            "subsystem": "Refrigerant Loop",
            "material": "PA/IIR Barrier Hose with Crimp Sleeves",
            "operating_temp_c": 135,
            "operating_pressure_bar": 28.0
        },
        {
            "part_id": "TR-AC-202",
            "part_name": "Swaged Aluminum Condenser Line Tube",
            "subsystem": "Refrigerant Line",
            "material": "Alloy 3003-H14 Aluminum",
            "operating_temp_c": 105,
            "vibration_freq_hz": 65
        },
        {
            "part_id": "TR-AC-203",
            "part_name": "AC Compressor Cast Iron Mount Bracket",
            "subsystem": "Engine Bay Structural",
            "material": "Ductile Iron GGG40",
            "vibration_g_rms": 22.0,
            "mass_kg": 5.8
        },
        {
            "part_id": "TR-AC-204",
            "part_name": "HNBR O-Ring Refrigerant Joint Seal",
            "subsystem": "Sealing Interface",
            "material": "Hydrogenated Nitrile Rubber (HNBR 70 Shore A)",
            "operating_temp_c": 140,
            "operating_pressure_bar": 28.0
        }
    ],
    "Hydraulic Steering & Implement Package": [
        {
            "part_id": "TR-HYD-301",
            "part_name": "Steering Cylinder High-Pressure Flex Hose",
            "subsystem": "Hydraulic Power",
            "material": "Four-Spiral Steel Wire Reinforced Synthetic Rubber (SAE 100R15)",
            "operating_temp_c": 125,
            "operating_pressure_bar": 350.0
        },
        {
            "part_id": "TR-HYD-302",
            "part_name": "Steering Arm Forged Steel Bracket",
            "subsystem": "Chassis Steering Linkage",
            "material": "Forged AISI 4140 Quenched & Tempered",
            "peak_load_kn": 120.0,
            "mass_kg": 14.2
        },
        {
            "part_id": "TR-HYD-303",
            "part_name": "Steel Hydraulic Swivel Bulkhead Adapter",
            "subsystem": "Hydraulic Fitting",
            "material": "Free-Cutting Carbon Steel 11SMn30 (Zinc Plated)",
            "operating_pressure_bar": 350.0
        }
    ]
}

HISTORICAL_8D_WARRANTY_RAG: Dict[str, Dict[str, Any]] = {
    "TR-FL-101": {
        "historical_grounding": "8D Report #8D-TR-2024-88: B10 field failures at 450 operating hours due to bio-diesel permeation and thermal hardening near turbo heat shield.",
        "failure_mode": "Thermal Degradation & Micro-Cracking of Outer Cover",
        "potential_cause": "Radiant heat exposure exceeding 115°C continuous thermal ceiling combined with biodiesel chemical swelling.",
        "base_severity": 9,
        "base_occurrence": 7,
        "base_detection": 4
    },
    "TR-FL-102": {
        "historical_grounding": "Warranty Log #WAR-2023-1402: Cold-weather diesel weeping in Northern European field trials below -15°C.",
        "failure_mode": "Joint Relaxation & Low-Temperature Fuel Weeping",
        "potential_cause": "Hose rubber cold compression set exceeding clamp expansion range during thermal cycling.",
        "base_severity": 6,
        "base_occurrence": 5,
        "base_detection": 3
    },
    "TR-FL-103": {
        "historical_grounding": "8D Report #8D-TR-2023-19: Resonant fatigue cracking along secondary mounting boss observed under 18G chassis shaker testing.",
        "failure_mode": "Structural Fatigue Fracture at Mounting Boss Fillet",
        "potential_cause": "First structural bending mode (145 Hz) aligns with diesel engine 2nd order harmonic vibration.",
        "base_severity": 8,
        "base_occurrence": 6,
        "base_detection": 5
    },
    "TR-FL-104": {
        "historical_grounding": "Quality Claim #QC-2024-512: Retainer latch tab embrittlement under prolonged UV and road salt exposure.",
        "failure_mode": "Retaining Latch Fracture & Hose Disengagement",
        "potential_cause": "Glass-fiber orientation anisotropy creating notch sensitivity at locking latch hinge root.",
        "base_severity": 9,
        "base_occurrence": 4,
        "base_detection": 6
    },
    "TR-AC-201": {
        "historical_grounding": "Warranty Log #WAR-2024-041: Refrigerant leak R134a/R1234yf at aluminum crimp fitting collar after 600 hours high-vibration tilling.",
        "failure_mode": "Freon Leakage at Crimp Sleeve Interface",
        "potential_cause": "Relative axial movement between ferrule crimp and rubber barrier under engine engine shake.",
        "base_severity": 7,
        "base_occurrence": 6,
        "base_detection": 5
    },
    "TR-AC-202": {
        "historical_grounding": "Field Quality Incident #FQ-2023-90: Fretting abrasion pinhole leak against engine frame rail.",
        "failure_mode": "Wall Abrasion & Pinhole Refrigerant Discharge",
        "potential_cause": "Inadequate clearance (<15mm) to chassis frame rail allowing intermittent contact during high-torque chassis twist.",
        "base_severity": 5,
        "base_occurrence": 5,
        "base_detection": 4
    },
    "TR-AC-203": {
        "historical_grounding": "8D Report #8D-TR-2024-104: Heavy casting fracture at lower compressor bolt eyelet on rough terrain transport.",
        "failure_mode": "Brittle Fatigue Fracture at Fastener Lug",
        "potential_cause": "Shrinkage porosity in casting combined with cantilevered AC compressor inertia load during field bumps.",
        "base_severity": 8,
        "base_occurrence": 5,
        "base_detection": 4
    },
    "TR-AC-204": {
        "historical_grounding": "Warranty Log #WAR-2023-311: O-ring compression set extrusion under 140°C peak soak temperature.",
        "failure_mode": "Seal Extrusion & HVAC Refrigerant Loss",
        "potential_cause": "Soak temperature exceeding HNBR continuous rating during post-shutdown heat soak in enclosed engine compartment.",
        "base_severity": 6,
        "base_occurrence": 4,
        "base_detection": 3
    },
    "TR-HYD-301": {
        "historical_grounding": "8D Report #8D-TR-2024-210: Catastrophic hydraulic burst under 420 bar pressure spike during rapid loader bucket drop.",
        "failure_mode": "Outer Wire Braid Burst & High-Pressure Hydraulic Oil Spray",
        "potential_cause": "Transient hydraulic shock wave exceeding hose impulse fatigue rating (SAE 100R15 500k cycle limit).",
        "base_severity": 10,
        "base_occurrence": 5,
        "base_detection": 4
    },
    "TR-HYD-302": {
        "historical_grounding": "Field Quality Incident #FQ-2024-02: Micro-fretting wear on kingpin tapered bore.",
        "failure_mode": "Bore Fretting & Steering Play Accumulation",
        "potential_cause": "Insufficient surface hardness (HRC < 35) on bore inner surface allowing fretting micro-motion under cyclic steering torque.",
        "base_severity": 8,
        "base_occurrence": 4,
        "base_detection": 5
    },
    "TR-HYD-303": {
        "historical_grounding": "Warranty Log #WAR-2023-889: Thread stripping during high-torque assembly at dealership service.",
        "failure_mode": "Thread Shear & Fitting Disconnection",
        "potential_cause": "Over-torquing beyond 60 Nm combined with low shear strength of free-cutting carbon steel.",
        "base_severity": 7,
        "base_occurrence": 3,
        "base_detection": 2
    }
}


# =====================================================================
# AGENT CLASS IMPLEMENTATIONS
# =====================================================================

class StructureFunctionAgent:
    """Agent 1: Ingests package BOMs and assigns context-specific mechanical functions."""
    
    def process(self, part_data: Dict[str, Any], package_name: str) -> str:
        part_name = part_data.get("part_name", "")
        material = part_data.get("material", "")
        subsystem = part_data.get("subsystem", "")

        prompt = f"""
        You are a Principal Mechanical Packaging Engineer specializing in heavy agricultural tractor design.
        Assign a concise, technical primary mechanical function for this component in the context of the package '{package_name}'.
        Component Name: {part_name}
        Subsystem: {subsystem}
        Material / Specs: {material}
        Output ONLY a 1-sentence engineering function description (e.g., 'Provides flexible pressurized fuel containment while isolating engine high-frequency vibration').
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
        elif "Fitting" in part_name or "Adapter" in part_name:
            return f"Provides quick-disconnect zero-leak fluid coupling under high operating system pressure."
        elif "Tube" in part_name:
            return f"Transfers high-pressure fluid along rigid chassis routing paths with minimal pressure drop."
        elif "Seal" in part_name or "O-Ring" in part_name:
            return f"Prevents fluid leakage across mating metal flanges under dynamic thermal expansion."
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
            "historical_grounding": f"8D Report #8D-TR-GENERIC: Field warranty logs indicate localized stress concentration risks under field torsional shock loads.",
            "failure_mode": "Mechanical Fatigue & Material Wear",
            "potential_cause": "High cyclic mechanical stress exceeding component fatigue limits.",
            "base_severity": 7,
            "base_occurrence": 5,
            "base_detection": 4
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

        # For low / medium risks (< 200 RPN and S < 9), return standard design validation note
        if not is_critical:
            return f"Standard Quality Control: Retain baseline material ({material}). Conduct standard production line leak & dimension check."

        # High risk / Critical Outlier -> Generate actionable practical engineering items
        prompt = f"""
        You are a Principal Engineering Specialist in Agricultural Tractor Reliability.
        Generate specific, practical Engineering Action Items for a critical DFMEA risk.
        DO NOT generate generic formal ECO paperwork boilerplate. Give actionable design engineering directives:
        - Material compound / alloy upgrades (e.g. upgrade NBR to FKM Fluoroelastomer, 51CrV4 to 4140 steel)
        - Geometry redesign directives (e.g. increase fillet radius from 2.0mm to 4.5mm, add isolation grommets)
        - Validation test mandates (e.g. mandatory 500-hour thermal-shaker bench test at 140°C under 20G RMS)

        Component: {part_name} (Part ID: {part_id})
        Current Material: {material}
        Failure Mode: {failure_mode}
        Potential Cause: {cause}
        Severity: {s}/10 | Computed RPN: {rpn}

        Output 3 clear, bulleted Engineering Action Directives.
        """
        ai_mitigation = call_gemini(prompt)
        if ai_mitigation:
            return ai_mitigation

        # Rule-based fallback for critical action items
        if "Hose" in part_name:
            return (
                "• **Material Upgrade**: Replace inner NBR liner with FKM Fluoroelastomer barrier rated for 150°C continuous biodiesel soak.\n"
                "• **Protection Sheathing**: Add silicone-coated fiberglass firesleeve over turbo proximity zone.\n"
                "• **Validation Mandate**: Perform 1,000-hour impulse pressure shock test at 135°C with 15G multi-axis shaker table vibration."
            )
        elif "Clamp" in part_name or "Fitting" in part_name:
            return (
                "• **Design Mod**: Implement dual-bead bead-lock retention profile on mating aluminum barb.\n"
                "• **Material Upgrade**: Upgrade spring steel plating to 316 Stainless Steel with heavy-duty constant-tension Belleville washers.\n"
                "• **Test Mandate**: Execute cold-chamber leak testing at -30°C under 30 bar pressure spikes."
            )
        elif "Bracket" in part_name:
            return (
                "• **Structural Redesign**: Increase fillet radii at boss mounting junctions from 2.0mm to 4.5mm and add 3mm stiffening gussets.\n"
                "• **Material Upgrade**: Switch from die-cast aluminum ADC12 to Ductile Iron GGG50.\n"
                "• **FEA Mandate**: Perform modal resonance avoidance FEA analysis to shift first structural mode above 220 Hz."
            )
        else:
            return (
                "• **Material Upgrade**: Upgrade base material to high-fatigue alloy (AISI 4140 Quenched & Tempered).\n"
                "• **Geometry Mod**: Add vibration-damping rubber isolation grommets at primary chassis attachment points.\n"
                "• **Validation Mandate**: Mandate 100% Ultrasonic non-destructive examination (NDE) for production lots."
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

            # Assemble complete DFMEA record row
            row = {
                "part_id": part_id,
                "part_name": part_name,
                "subsystem": part.get("subsystem", "Tractor Subsystem"),
                "material": part.get("material", "Standard Alloy"),
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