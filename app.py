import streamlit as st
import pandas as pd
import json
from agents import (
    HEAVY_TRACTOR_BOM_PACKAGES,
    DFMEAMultiAgentOrchestrator,
    DeterministicRiskEngine
)

# Set page configuration with Titanium Dark theme
st.set_page_config(
    page_title="Mechnari.ai - Heavy Tractor Multi-Agent DFMEA Copilot",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Titanium & Modern Engineering Palette)
st.markdown("""
    <style>
    .main {
        background-color: #0E1117;
        color: #E0E6ED;
    }
    .stAppHeader {
        background-color: #161B22;
    }
    .metric-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .critical-banner {
        background-color: #3D0C11;
        border-left: 6px solid #F85149;
        padding: 16px;
        border-radius: 6px;
        margin-bottom: 20px;
    }
    .approval-banner {
        background-color: #0D2D1B;
        border-left: 6px solid #3FB950;
        padding: 16px;
        border-radius: 6px;
        margin-bottom: 20px;
    }
    .stButton>button {
        font-weight: 600;
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)


# Initialize Session State
if "dfmea_data" not in st.session_state:
    st.session_state.dfmea_data = []

if "selected_package" not in st.session_state:
    st.session_state.selected_package = list(HEAVY_TRACTOR_BOM_PACKAGES.keys())[0]

if "batch_approved" not in st.session_state:
    st.session_state.batch_approved = False


# =====================================================================
# SIDEBAR CONTROLS & BOM INGESTION
# =====================================================================
st.sidebar.image("https://img.icons8.com/color/96/tractor.png", width=70)
st.sidebar.title("⚙️ Mechnari.ai")
st.sidebar.caption("Multi-Agent DFMEA Copilot for Heavy Manufacturing (1,000+ Part Systems)")

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Subsystem Package Ingestion")

package_options = list(HEAVY_TRACTOR_BOM_PACKAGES.keys())
selected_pkg = st.sidebar.selectbox(
    "Select Heavy Tractor Subsystem Package:",
    package_options,
    index=0
)

col_sidebar1, col_sidebar2 = st.sidebar.columns(2)
run_btn = col_sidebar1.button("🚀 Run Analysis", type="primary", use_container_width=True)
reset_btn = col_sidebar2.button("🔄 Reset", use_container_width=True)

if reset_btn:
    st.session_state.dfmea_data = []
    st.session_state.batch_approved = False
    st.rerun()

# Automatically run pipeline on startup or selection change
if run_btn or not st.session_state.dfmea_data or st.session_state.selected_package != selected_pkg:
    st.session_state.selected_package = selected_pkg
    orchestrator = DFMEAMultiAgentOrchestrator()
    bom_list = HEAVY_TRACTOR_BOM_PACKAGES[selected_pkg]
    with st.spinner("🤖 Multi-Agent Pipeline Analyzing Package (Structure -> Failure RAG -> Risk Engine -> Mitigation)..."):
        st.session_state.dfmea_data = orchestrator.run_pipeline(selected_pkg, bom_list)
        st.session_state.batch_approved = False

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Active Multi-Agent Pipeline")
st.sidebar.markdown("""
1. **Structure & Function Agent**: Contextual mechanical function mapping.
2. **Failure RAG Agent**: Historical 8D & warranty log matcher.
3. **Deterministic Risk Engine**: RPN = S x O x D calculation.
4. **Mitigation Agent**: Actionable practical engineering directives.
""")


# =====================================================================
# MAIN DASHBOARD HEADER & EXECUTIVE METRICS
# =====================================================================
st.title("⚙️ Mechnari.ai - Multi-Agent DFMEA Risk Copilot")
st.markdown(f"**Current Subsystem:** `{st.session_state.selected_package}` | **System Context:** Heavy Agricultural Tractor (1,000+ Parts)")

dfmea_records = st.session_state.dfmea_data
df = pd.DataFrame(dfmea_records) if dfmea_records else pd.DataFrame()

if not df.empty:
    total_parts = len(df)
    critical_count = len(df[df["is_critical"] == True])
    high_count = len(df[(df["rpn"] >= 100) & (df["is_critical"] == False)])
    low_med_count = total_parts - critical_count

    # KPI Metrics Banner
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Components Analyzed", total_parts)
    with m2:
        st.metric("🔴 Critical Risk Outliers", critical_count, delta="Requires Executive Sign-Off" if critical_count > 0 else "Clear", delta_color="inverse")
    with m3:
        st.metric("🟡 Low / Medium Risk Items", low_med_count)
    with m4:
        approved_count = len(df[df["approval_status"].str.contains("Approved")])
        st.metric("Executive Approvals", f"{approved_count} / {total_parts}")

    st.markdown("---")

    # =====================================================================
    # MANAGEMENT-BY-EXCEPTION VIEW & BATCH APPROVAL
    # =====================================================================
    st.subheader("🛡️ Management-by-Exception Executive Control")
    st.caption("Lead engineers review critical outliers while batch-approving routine low/medium risk components in 1 click.")

    c_left, c_right = st.columns([2, 1])

    with c_left:
        st.markdown(f"""
        <div class="critical-banner">
            <h4>🔴 High-Risk Outlier Flagged: {critical_count} Component(s) Require Direct Review</h4>
            <p>Components with <b>RPN &ge; 200</b> or <b>Severity &ge; 9</b> are automatically isolated from batch approval. Practical engineering action directives have been generated below.</p>
        </div>
        """, unsafe_allow_html=True)

    with c_right:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ Batch Approve Low/Medium Risk Items (< 200 RPN)", type="primary", use_container_width=True):
            for row in st.session_state.dfmea_data:
                if not row["is_critical"]:
                    row["approval_status"] = "✅ Batch Approved by Lead Engineer"
            st.session_state.batch_approved = True
            st.success(f"Successfully batch-approved {low_med_count} low/medium risk component(s)!")
            st.rerun()

    # Display Critical Outliers Cards
    critical_df = df[df["is_critical"] == True]
    if not critical_df.empty:
        st.markdown("### 🚨 Critical Outlier Deep-Dive & Practical Action Items")
        for idx, row in critical_df.iterrows():
            with st.expander(f"🔴 Part ID: {row['part_id']} - {row['part_name']} | RPN: {row['rpn']} (S:{row['severity']}, O:{row['occurrence']}, D:{row['detection']})", expanded=True):
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    st.markdown(f"**Function:** {row['function']}")
                    st.markdown(f"**Material:** `{row['material']}`")
                    st.markdown(f"**Potential Failure Mode:** {row['potential_failure_mode']}")
                    st.markdown(f"**Potential Cause:** {row['potential_cause']}")
                    st.warning(f"**Historical 8D Grounding:**\n{row['historical_grounding']}")
                with col_b:
                    st.markdown("##### 🛠️ AI-Generated Practical Engineering Action Directives:")
                    st.markdown(row["action_items"])
                    
                    st.markdown("---")
                    btn_col1, btn_col2 = st.columns(2)
                    if btn_col1.button(f"✅ Approve Action Plan ({row['part_id']})", key=f"app_{row['part_id']}"):
                        for item in st.session_state.dfmea_data:
                            if item["part_id"] == row["part_id"]:
                                item["approval_status"] = "✅ Executive Approved"
                        st.success(f"Approved {row['part_id']}")
                        st.rerun()

    st.markdown("---")

    # =====================================================================
    # STRUCTURED DFMEA DATA TABLE
    # =====================================================================
    st.subheader("📊 Complete DFMEA Engineering Matrix")
    
    # Filter controls
    filter_col1, filter_col2 = st.columns([2, 2])
    with filter_col1:
        risk_filter = st.selectbox(
            "Filter Matrix View by Risk Category:",
            ["All Records", "Critical Outliers Only (RPN >= 200 or S >= 9)", "Medium Risk Only", "Approved Only"]
        )

    # Filter logic
    display_df = df.copy()
    if risk_filter == "Critical Outliers Only (RPN >= 200 or S >= 9)":
        display_df = display_df[display_df["is_critical"] == True]
    elif risk_filter == "Medium Risk Only":
        display_df = display_df[display_df["risk_category"].str.contains("MEDIUM")]
    elif risk_filter == "Approved Only":
        display_df = display_df[display_df["approval_status"].str.contains("Approved")]

    # Select columns to render in structured table
    table_columns = [
        "part_id", "part_name", "function", "potential_failure_mode",
        "severity", "occurrence", "detection", "rpn",
        "risk_category", "historical_grounding", "action_items", "approval_status"
    ]
    
    table_df = display_df[table_columns].rename(columns={
        "part_id": "Part ID",
        "part_name": "Component Name",
        "function": "Mechanical Function",
        "potential_failure_mode": "Potential Failure Mode",
        "severity": "S",
        "occurrence": "O",
        "detection": "D",
        "rpn": "RPN",
        "risk_category": "Risk Status",
        "historical_grounding": "Historical Field Grounding (8D)",
        "action_items": "Generated Action Items",
        "approval_status": "Approval Status"
    })

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "RPN": st.column_config.NumberColumn("RPN", format="%d"),
            "S": st.column_config.NumberColumn("S", format="%d"),
            "O": st.column_config.NumberColumn("O", format="%d"),
            "D": st.column_config.NumberColumn("D", format="%d"),
            "Generated Action Items": st.column_config.TextColumn("Generated Action Items", width="large"),
            "Historical Field Grounding (8D)": st.column_config.TextColumn("Historical Field Grounding (8D)", width="medium"),
        }
    )

    # Export capability
    csv_bytes = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Complete DFMEA Matrix (CSV)",
        data=csv_bytes,
        file_name=f"Mechnari_DFMEA_{st.session_state.selected_package.replace(' ', '_')}.csv",
        mime="text/csv"
    )

else:
    st.info("Select a subsystem package from the sidebar and click **Run Analysis** to execute the multi-agent DFMEA pipeline.")