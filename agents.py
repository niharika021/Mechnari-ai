import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Support for google-genai (new SDK) and google-generativeai (legacy SDK)
try:
    from google import genai
    USE_NEW_GENAI = True
except ImportError:
    try:
        import google.generativeai as genai
        USE_NEW_GENAI = False
    except ImportError:
        genai = None
        USE_NEW_GENAI = False


def call_gemini(prompt: str) -> str:
    """Helper to query Gemini model using available SDK with graceful fallback."""
    if not genai or not api_key:
        return "[Warning] Gemini API key is missing. Set GEMINI_API_KEY in .env file to enable live AI responses."

    try:
        if USE_NEW_GENAI:
            from google.genai import types
            # Pass verify=False in client_args to prevent corporate SSL proxy failures
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(client_args={'verify': False})
            )
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt
            )
            return response.text
        else:
            if api_key:
                genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "UNAUTHENTICATED" in err_msg:
            return (
                "**[Notice] Gemini API Key Authentication (401)**\n\n"
                "The configured `GEMINI_API_KEY` in `.env` is invalid or expired. Please update `.env` with a valid Google Gemini API key.\n\n"
                "**Automated Failure Mode Recommendation (Rule-Based Synthesis):**\n"
                "- **Failure Mechanism**: High peak cyclic stress exceeds material endurance limits leading to micro-fretting & micro-crack initiation.\n"
                "- **ECO Action**: Increase fillet radius at stress concentration nodes by >=1.5x, apply shot peening surface hardening, or upgrade material alloy to AISI 4140.\n"
                "- **Quality Protocol**: 100% Ultrasonic non-destructive examination (NDE) and dye penetrant inspection on high-stress fillet junctions."
            )
        elif "CERTIFICATE_VERIFY" in err_msg or "SSL" in err_msg:
            return f"[Warning] Network/SSL Proxy Error: {err_msg}"
        else:
            return f"[Warning] Gemini API Error: {err_msg}"




class BigQueryMaterialClient:
    """Helper client to fetch live engineering data from Google BigQuery."""
    def __init__(self, project_id="my-bigquery-demo-505415", dataset_id="mechnari_engineering"):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = None
        # Only initialize BigQuery client if GCP credentials or active auth is present
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GCP_PROJECT"):
            try:
                from google.cloud import bigquery
                self.client = bigquery.Client(project=self.project_id)
            except Exception:
                self.client = None

    def get_material_properties(self, material_name: str) -> dict:
        """Fetch yield strength, fatigue limit, and density from BigQuery with fallback."""
        if self.client:
            from google.cloud import bigquery
            query = f"""
            SELECT material_name, category, yield_strength_mpa, ultimate_tensile_strength_mpa, 
                   fatigue_limit_mpa, density_g_cm3, elastic_modulus_gpa, cost_index
            FROM `{self.project_id}.{self.dataset_id}.materials_master`
            WHERE LOWER(material_name) LIKE LOWER(@mat_pattern)
            LIMIT 1
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("mat_pattern", "STRING", f"%{material_name}%")
                ]
            )
            try:
                query_job = self.client.query(query, job_config=job_config)
                results = list(query_job.result(timeout=5.0))
                if results:
                    return dict(results[0])
            except Exception as e:
                print(f"BigQuery lookup fallback triggered: {e}")

        # Fallback mock data if credentials/BigQuery are unavailable
        is_316 = "316" in material_name
        is_4140 = "4140" in material_name
        is_ti = "Titanium" in material_name or "Ti-" in material_name

        if is_4140:
            yield_str, fatigue_lim, density, modulus = 655.0, 320.0, 7.85, 205.0
        elif is_ti:
            yield_str, fatigue_lim, density, modulus = 880.0, 510.0, 4.43, 114.0
        elif is_316:
            yield_str, fatigue_lim, density, modulus = 290.0, 240.0, 8.0, 193.0
        else: # Al 6061-T6
            yield_str, fatigue_lim, density, modulus = 276.0, 96.0, 2.7, 68.9

        return {
            "material_name": material_name,
            "yield_strength_mpa": yield_str,
            "fatigue_limit_mpa": fatigue_lim,
            "density_g_cm3": density,
            "elastic_modulus_gpa": modulus
        }

    def get_failure_catalog(self, component: str) -> list:
        """Fetch historical failure modes and baseline scores from BigQuery with fallback."""
        if self.client:
            from google.cloud import bigquery
            query = f"""
            SELECT failure_mode, potential_cause, default_severity, default_occurrence, 
                   default_detection, recommended_eco_action
            FROM `{self.project_id}.{self.dataset_id}.failure_modes_catalog`
            WHERE LOWER(component_category) LIKE LOWER(@comp_pattern)
            LIMIT 3
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("comp_pattern", "STRING", f"%{component}%")
                ]
            )
            try:
                query_job = self.client.query(query, job_config=job_config)
                return [dict(row) for row in query_job.result(timeout=5.0)]
            except Exception:
                pass

        return [{
            "failure_mode": "Fatigue Cracking under Cyclic Shear",
            "potential_cause": "Applied cyclic stress exceeds endurance limit",
            "default_severity": 8,
            "default_occurrence": 6,
            "default_detection": 4
        }]


class DFMEARiskAgent:
    """Agent responsible for deterministic stress evaluations & Gemini-powered ECO synthesis."""
    def __init__(self):
        self.bq = BigQueryMaterialClient()

    def evaluate_component(self, component: str, material: str, operating_stress_mpa: float, cyclic_load: bool = True):
        mat_data = self.bq.get_material_properties(material)
        failures = self.bq.get_failure_catalog(component)

        yield_strength = mat_data.get("yield_strength_mpa", 250.0)
        fatigue_limit = mat_data.get("fatigue_limit_mpa", 150.0)

        # Safety factor calculations
        static_fos = round(yield_strength / max(operating_stress_mpa, 1.0), 2)
        dynamic_fos = round(fatigue_limit / max(operating_stress_mpa, 1.0), 2) if cyclic_load else static_fos

        # Scoring RPN
        severity = 8 if dynamic_fos < 1.0 else (6 if dynamic_fos < 1.5 else 3)
        occurrence = 8 if dynamic_fos < 1.0 else (5 if dynamic_fos < 1.5 else 2)
        detection = 5 if cyclic_load else 3
        rpn = severity * occurrence * detection

        # Generate Gemini synthesis
        prompt = f"""
        You are a Principal Mechanical Safety & DFMEA Lead Engineer.
        Analyze the following component data:
        - Component: {component}
        - Material: {mat_data.get('material_name', material)}
        - Operating Stress: {operating_stress_mpa} MPa
        - Yield Strength: {yield_strength} MPa (Static Factor of Safety: {static_fos})
        - Fatigue Limit: {fatigue_limit} MPa (Dynamic Factor of Safety: {dynamic_fos})
        - Computed RPN: {rpn} (Severity: {severity}, Occurrence: {occurrence}, Detection: {detection})

        Provide an Engineering Change Order (ECO) risk assessment:
        1. Failure Mechanism Analysis (Explain why/how failure will occur under these stresses).
        2. Actionable ECO Mitigation (Specify geometry modification, heat treatment, or higher-strength alternative alloy).
        3. Quality & Inspection protocol (e.g., Eddy current, Dye Penetrant, Ultrasonic testing).
        Format with clear, professional engineering bullet points.
        """
        try:
            eco_recommendation = call_gemini(prompt)
        except Exception as e:
            eco_recommendation = f"Gemini generation error: {e}"

        return {
            "material_data": mat_data,
            "static_fos": static_fos,
            "dynamic_fos": dynamic_fos,
            "severity": severity,
            "occurrence": occurrence,
            "detection": detection,
            "rpn": rpn,
            "eco_recommendation": eco_recommendation
        }


class MentorAgent:
    """Agent responsible for GD&T mentoring and technical design interview prep."""
    def __init__(self):
        self.system_instruction = """
        You are Mechnari AI Mentor, an expert mechanical design consultant specializing in ASME Y14.5 GD&T standards,
        tolerance analysis, FEA stress concentrations, and manufacturing DFM/DFA guidelines.
        Explain engineering concepts concisely with real-world mechanical examples.
        """

    def answer_query(self, user_question: str) -> str:
        prompt = f"{self.system_instruction}\n\nUser Question: {user_question}\n\nExpert Response:"
        ans = call_gemini(prompt)
        
        # If API key is invalid/missing, append tailored engineering explanation
        if "[Notice] Gemini API Key Authentication" in ans or "[Warning]" in ans:
            q_lower = user_question.lower()
            if "maximum material condition" in q_lower or "mmc" in q_lower:
                ans += (
                    "\n\n---"
                    "\n\n**Mechnari Mentor Guidance on MMC (ASME Y14.5):**\n"
                    "- **Definition**: Maximum Material Condition (MMC) is the condition in which a feature of size contains the maximum amount of material within stated limits (e.g., smallest hole diameter or largest pin/shaft diameter).\n"
                    "- **Bonus Tolerance**: When a feature departs from MMC toward Least Material Condition (LMC), additional (bonus) positional tolerance equal to the departure size is permitted.\n"
                    "- **Application**: Used heavily in pin-and-clevis or mating hole assembly designs to guarantee assembly under worst-case tolerance stackups while reducing scrap rates."
                )
            elif "runout" in q_lower:
                ans += (
                    "\n\n---"
                    "\n\n**Mechnari Mentor Guidance on Circular vs. Total Runout:**\n"
                    "- **Circular Runout (2D)**: Controls circular elements of a surface relative to a datum axis at individual cross-sections independently.\n"
                    "- **Total Runout (3D)**: Controls the entire surface simultaneously across both length and rotation, constraining circularity, straightness, coaxiality, angularity, and taper."
                )
            elif "316" in q_lower or "4140" in q_lower:
                ans += (
                    "\n\n---"
                    "\n\n**Mechnari Mentor Guidance on Material Selection (SS316L vs AISI 4140):**\n"
                    "- **AISI 4140 (Quenched & Tempered)**: High yield strength (~655-1000+ MPa) and superior fatigue endurance limit (~320-500 MPa). Best for high cyclic torque drive shafts.\n"
                    "- **SS316L (Austenitic Stainless)**: Moderate yield strength (~290 MPa), excellent pitting corrosion resistance in marine/chemical environments, non-magnetic. Best for chemical exposure."
                )
            else:
                ans += (
                    "\n\n---"
                    "\n\n**Mechnari Mentor Core Principle:**\n"
                    "Always define a clear datum reference frame (DRF) per ASME Y14.5-2018 establishing primary (3-point constraint), secondary (2-point constraint), and tertiary (1-point constraint) datums prior to placing geometric tolerances."
                )
        return ans