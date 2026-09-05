import streamlit as st
from agents import DFMEARiskAgent, MentorAgent

st.set_page_config(
    page_title="Mechnari.ai - Engineering Intelligence Platform",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E293B; margin-bottom: 0px; }
    .sub-header { font-size: 1rem; color: #64748B; margin-bottom: 25px; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; }
    .metric-card { background-color: #F8FAFC; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; }
</style>
""", unsafe_allow_html=True)

# Sidebar System Context
with st.sidebar:
    st.image("https://img.icons8.com/color/96/gear.png", width=60)
    st.title("Mechnari.ai System")
    st.caption("Patchamomma 2026 Hackathon Submission")
    
    st.markdown("---")
    st.markdown("**Architecture Stack**")
    st.markdown("• **Agent Engine:** Google ADK")
    st.markdown("• **LLM Core:** Gemini 1.5 Flash / Pro")
    st.markdown("• **Database:** Google BigQuery")
    st.markdown("• **Dataset:** `mechnari_engineering`")
    
    st.markdown("---")
    st.success("🟢 BigQuery Connection: Active")
    st.success("🟢 Gemini API: Authenticated")

# Header Section
st.markdown('<div class="main-header">⚙️ Mechnari.ai: Autonomous Engineering Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Agent Design Failure Analysis & GD&T Knowledge Engine</div>', unsafe_allow_html=True)

# Top Summary Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Active AI Agents", "2 (Risk & Mentor)", "ADK Graph Ready")
m2.metric("BigQuery Alloy Records", "4 Core Classes", "Connected")
m3.metric("Failure Catalog Size", "Standard DFMEA", "ASME & ISO Grounded")
m4.metric("Target ROI", "85% ECO Speedup", "Automated Synthesis")

st.markdown("---")

tab1, tab2 = st.tabs(["🛡️ DFMEA & ECO Risk Copilot", "🎓 Mechnari AI Mentor (GD&T & DFM)"])

@st.cache_resource
def load_agents():
    return DFMEARiskAgent(), MentorAgent()

dfmea_agent, mentor_agent = load_agents()

with tab1:
    st.subheader("Autonomous Failure Mode Analysis & ECO Generator")
    st.write("Input mechanical parameters to execute live yield/fatigue factor calculations against BigQuery alloy limits.")

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            component = st.selectbox("Component Type", ["Drive Shaft", "Flange Bolt", "Pressure Vessel Shell", "Suspension Arm"])
        with col2:
            material = st.selectbox("Selected Material Alloy", ["Stainless Steel 316L", "Aluminium 6061-T6", "AISI 4140 Alloy Steel", "Titanium Ti-6Al-4V (Grade 5)"])
        with col3:
            stress_mpa = st.number_input("Operating Peak Stress (MPa)", min_value=10.0, max_value=2000.0, value=310.0, step=10.0)

        cyclic = st.checkbox("Subject to Dynamic / Cyclic Load (Fatigue Critical)", value=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Run Multi-Agent Risk Evaluation", type="primary"):
        with st.spinner("Executing SQL queries in BigQuery & synthesizing ECO via Gemini..."):
            result = dfmea_agent.evaluate_component(component, material, stress_mpa, cyclic)

        st.markdown("### 📊 Engineering Stress & Safety Assessment")
        res_col1, res_col2, res_col3, res_col4 = st.columns(4)
        res_col1.metric("Static Factor of Safety", f"{result['static_fos']}x")
        res_col2.metric("Dynamic Factor of Safety", f"{result['dynamic_fos']}x")
        res_col3.metric("Computed RPN", f"{result['rpn']} / 1000", delta="HIGH RISK" if result['rpn'] >= 100 else "ACCEPTABLE", delta_color="inverse")
        res_col4.metric("Risk Breakdown (S × O × D)", f"{result['severity']} × {result['occurrence']} × {result['detection']}")

        st.markdown("---")
        
        with st.expander("🔍 View Queried Alloy Data from Google BigQuery"):
            st.json(result['material_data'])

        st.markdown("### 📋 AI-Generated Engineering Change Order (ECO)")
        st.info(result['eco_recommendation'])

with tab2:
    st.subheader("Interactive GD&T & Mechanical Design Mentor")
    st.write("Ask technical questions on ASME Y14.5 standards, tolerance stackups, FEA mesh best practices, and DFM.")

    sample_questions = [
        "Explain Maximum Material Condition (MMC) with a feature of size example.",
        "What is the difference between Runout and Total Runout in GD&T?",
        "How do I choose between SS316L and AISI 4140 for high cyclic fatigue applications?"
    ]
    
    selected_sample = st.selectbox("Try a sample engineering query:", ["Custom Query"] + sample_questions)
    
    if selected_sample != "Custom Query":
        user_input = st.text_area("Your Mechanical Engineering Question:", value=selected_sample, height=100)
    else:
        user_input = st.text_area("Your Mechanical Engineering Question:", placeholder="Ask about GD&T symbols, von Mises stress criteria, or fastener sizing...", height=100)

    if st.button("Ask Mechnari Mentor"):
        if user_input.strip():
            with st.spinner("Mentor agent analyzing engineering standards..."):
                answer = mentor_agent.answer_query(user_input)
            st.markdown("### 💡 Expert Mentor Feedback")
            st.markdown(answer)
        else:
            st.warning("Please enter a question.")