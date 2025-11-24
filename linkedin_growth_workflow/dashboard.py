import streamlit as st
import json
import os
import pandas as pd
from linkedin_agents import Orchestrator, Memory, LinkedInConnector

# Page Config
st.set_page_config(
    page_title="LinkedIn Agent Command Center",
    page_icon="🚀",
    layout="wide"
)

# Title
st.title("🚀 LinkedIn Growth Agent: Command Center")

# Sidebar
st.sidebar.header("Controls")
if st.sidebar.button("Run Workflow Now 🤖"):
    with st.spinner("Agents are working... check terminal for details..."):
        try:
            orch = Orchestrator()
            orch.run_workflow()
            st.success("Workflow completed! Check LinkedIn.")
        except Exception as e:
            st.error(f"Workflow failed: {e}")

# --- Memory Viewer ---
st.header("🧠 Agent Memory (Critic Rules)")
try:
    memory = Memory()
    rules = memory.get_rules()
    if rules:
        st.info(f"The agents have learned {len(rules)} rules from feedback.")
        
        # Display as a clean list
        for i, rule in enumerate(rules, 1):
            st.markdown(f"**{i}.** {rule}")
    else:
        st.warning("No rules learned yet. Run the bot to generate feedback.")
except Exception as e:
    st.error(f"Could not load memory: {e}")

# --- Analytics Section (Placeholder for now) ---
st.header("📊 Performance Analytics")
st.markdown("*(Connects to LinkedIn API to fetch real-time stats)*")

# Mock Data for Visualization
mock_data = {
    "Post Date": ["2025-11-20", "2025-11-21", "2025-11-22", "2025-11-23", "2025-11-24"],
    "Topic": ["AI Agents", "LLM OS", "Prompt Engineering", "Multi-Agent Systems", "Chatbots Dead"],
    "Likes": [12, 45, 32, 89, 15],
    "Comments": [2, 8, 5, 12, 3],
    "Views": [450, 1200, 890, 2500, 600]
}
df = pd.DataFrame(mock_data)

# Metrics Row
col1, col2, col3 = st.columns(3)
col1.metric("Total Views (Last 5 Posts)", f"{df['Views'].sum()}", "+12%")
col2.metric("Avg Likes", f"{df['Likes'].mean():.1f}", "+5%")
col3.metric("Engagement Rate", "3.8%", "+0.5%")

# Charts
st.subheader("Engagement Trends")
st.line_chart(df.set_index("Post Date")[["Likes", "Comments"]])

st.subheader("Recent Posts Data")
st.dataframe(df)

# --- Logs / Status ---
st.header("📝 System Logs")
if os.path.exists("linkedin_growth_workflow.log"):
    with open("linkedin_growth_workflow.log", "r") as f:
        logs = f.readlines()[-20:] # Last 20 lines
        st.code("".join(logs))
else:
    st.markdown("No log file found (logging might not be enabled in script).")
