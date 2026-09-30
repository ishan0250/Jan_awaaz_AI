"""
app.py
Jan-Awaaz AI - Main Entry Point & Global Styling.
"""

import streamlit as st
from data_store.db import init_db

# Page Setup
st.set_page_config(
    page_title="Jan-Awaaz AI | Civic Grievance Portal",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database Schema
init_db()

# Global Custom CSS for Visual Polish
st.markdown("""
<style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #f8fafc;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white !important;
        font-weight: 700;
        margin: 0;
        font-size: 2.2rem;
    }
    .main-header p {
        color: #e2e8f0;
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
    }

    /* Metric Card Styling */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }

    /* Status Badges */
    .badge-overdue {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #fca5a5;
    }
    .badge-pending {
        background-color: #fef3c7;
        color: #92400e;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #fde68a;
    }
    .badge-closed {
        background-color: #dcfce7;
        color: #166534;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #86efac;
    }

    /* Container Card Polish */
    .card-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# Main Banner
st.markdown("""
<div class="main-header">
    <h1>🏛️ Jan-Awaaz AI</h1>
    <p>Multimodal Civic Grievance Redressal & Priority Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)

st.success("✅ System operational. Use the left sidebar navigation to access Citizen Portal, Command Center, or Verification Portal.")