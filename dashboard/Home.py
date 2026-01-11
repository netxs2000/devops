import streamlit as st
from PIL import Image
import os

# Page Configuration
st.set_page_config(
    page_title="DevOps Intelligence Platform",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-family: 'Outfit', sans-serif;
        color: #FFFFFF;
        text-align: center;
        padding: 2rem 0;
    }
    .sub-header {
        font-family: 'Inter', sans-serif;
        color: #B0B0B0;
        text-align: center;
        margin-bottom: 3rem;
    }
    .card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        text-align: center;
        transition: transform 0.2s;
    }
    .card:hover {
        transform: scale(1.02);
        border-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 class='main-header'>🚀 DevOps Intelligence Platform</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Enterprise-Grade Engineering Analytics & Value Stream Management</p>", unsafe_allow_html=True)

# Main Dashboard Content
st.info("👋 Welcome! Select a module from the sidebar to begin your analytics journey.")

# Overview Columns
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class='card'>
        <h3>📊 DORA Metrics</h3>
        <p>Track Deployment Frequency, Lead Time, Failure Rate, and MTTR.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class='card'>
        <h3>🌊 Flow Metrics</h3>
        <p>Analyze Value Stream Flow Velocity, Efficiency, and Load.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class='card'>
        <h3>🤝 SPACE Framework</h3>
        <p>Measure Developer Satisfaction, Performance, and Activity.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption("Powered by Antigravity Agentic Coding • v4.1.0")
