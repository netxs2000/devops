import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from devops_collector.config import settings

def get_engine():
    """Returns a SQLAlchemy engine using the project settings."""
    return create_engine(settings.database.uri)

@st.cache_data(ttl=600)
def run_query(query: str):
    """Runs a SQL query and returns a pandas DataFrame, with caching."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def set_page_config():
    """Standardizes page configuration for the dashboard."""
    st.set_page_config(
        page_title="DevOps Intelligence Dashboard",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Custom CSS for Premium Look
    st.markdown("""
        <style>
        .main {
            background-color: #0e1117;
        }
        .stMetric {
            background-color: #1e2130;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #3d4455;
        }
        h1, h2, h3 {
            color: #ffffff;
            font-family: 'Outfit', sans-serif;
        }
        </style>
    """, unsafe_allow_html=True)
