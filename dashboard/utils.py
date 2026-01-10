"""TODO: Add module description."""
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from devops_collector.config import settings

def get_engine():
    """Returns a SQLAlchemy engine using the project settings."""
    return create_engine(settings.database.uri)

@st.cache_data(ttl=1)
def run_query(query: str):
    """Runs a SQL query and returns a pandas DataFrame, with caching."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def set_page_config():
    """Standardizes page configuration for the dashboard."""
    st.set_page_config(page_title='DevOps Intelligence Dashboard', page_icon='🚀', layout='wide', initial_sidebar_state='expanded')
    st.markdown("\n        <style>\n        .main {\n            background-color: #0e1117;\n        }\n        .stMetric {\n            background-color: #1e2130;\n            padding: 15px;\n            border-radius: 10px;\n            border: 1px solid #3d4455;\n        }\n        h1, h2, h3 {\n            color: #ffffff;\n            font-family: 'Outfit', sans-serif;\n        }\n        </style>\n    ", unsafe_allow_html=True)