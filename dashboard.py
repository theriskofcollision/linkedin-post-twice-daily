import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
# Note: Orchestrator is imported lazily when needed to avoid loading on every page view

# Page Config
st.set_page_config(
    page_title="LinkedIn Growth Machine",
    page_icon="📈",
    layout="wide"
)

# --- Helper Functions ---
def load_memory():
    try:
        with open("memory.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"rules": [], "history": []}

# --- Main Layout ---
st.title("📈 LinkedIn Growth Machine: Command Center")

# Load Data
data = load_memory()
history = data.get("history", [])
latest_pack = data.get("latest_comment_pack", None)

# --- Top Section: The Networker (Comment Pack) ---
st.header("🤝 The Networker: Daily Comment Pack")
if latest_pack:
    st.success("New Comment Strategy Available!")
    with st.expander("View Comment Pack (Copy-Paste these!)", expanded=True):
        st.markdown(latest_pack)
else:
    st.info("No comment pack generated yet. Run the workflow to get one.")

st.divider()

# --- Middle Section: Analytics ---
st.header("📊 Performance Analytics")

if history:
    # Convert history to DataFrame
    df_data = []
    for entry in history:
        df_data.append({
            "Date": entry.get("date", "Unknown"),
            "Topic": entry.get("topic", "Unknown"),
            "Vibe": entry.get("vibe", "Unknown"),
            "Likes": entry.get("stats", {}).get("likes", 0),
            "Comments": entry.get("stats", {}).get("comments", 0)
        })
    
    df = pd.DataFrame(df_data)
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    total_likes = df["Likes"].sum()
    total_comments = df["Comments"].sum()
    top_vibe = df.groupby("Vibe")["Likes"].sum().idxmax() if not df.empty else "N/A"
    
    col1.metric("Total Likes", total_likes)
    col2.metric("Total Comments", total_comments)
    col3.metric("🏆 Best Vibe", top_vibe)
    
    # Charts
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Engagement over Time")
        if not df.empty:
            st.line_chart(df.set_index("Date")[["Likes", "Comments"]])
            
    with c2:
        st.subheader("Vibe Performance")
        if not df.empty:
            vibe_stats = df.groupby("Vibe")[["Likes", "Comments"]].sum().reset_index()
            fig = px.bar(vibe_stats, x="Vibe", y="Likes", color="Vibe", title="Likes by Persona")
            st.plotly_chart(fig)

    # Raw Data
    with st.expander("Raw Post History"):
        st.dataframe(df)

else:
    st.warning("No post history found. The bot needs to run a few times to gather data.")

st.divider()

# --- Bottom Section: Controls & Memory ---
c_left, c_right = st.columns([1, 2])

with c_left:
    st.header("🤖 Controls")
    
    # Warning about running manually
    st.warning("⚠️ Running manually may conflict with scheduled GitHub Actions runs.")
    
    # Confirmation checkbox
    confirm = st.checkbox("I understand the risks")
    
    if st.button("Run Workflow Now (Manual Trigger)", disabled=not confirm):
        with st.spinner("Agents are working... this may take several minutes..."):
            try:
                # Lazy import to avoid loading on every page view
                from linkedin_agents import Orchestrator
                orch = Orchestrator()
                orch.run_workflow()
                st.success("✅ Workflow completed! Refresh page to see results.")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Workflow failed: {e}")

with c_right:
    st.header("🧠 Critic Memory")
    rules = data.get("rules", [])
    if rules:
        st.write(f"The Critic has learned **{len(rules)} rules** to improve future content:")
        for rule in rules:
            st.markdown(f"- {rule}")
    else:
        st.info("No rules learned yet.")
