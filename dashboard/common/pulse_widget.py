
import streamlit as st
import datetime
from sqlalchemy import text
from dashboard.common.db import get_db_engine

def render_pulse_widget(user_email: str = "anonymous"):
    """Renders the DevEx Pulse widget in the sidebar.
    
    Args:
        user_email (str): The email of the current user. In a real app,
                          this comes from OAuth/SSO session state.
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 😊 DevEx Pulse")
    st.sidebar.caption("How was your developer experience today?")

    # Simple session state key for "submitted today"
    today_str = datetime.date.today().isoformat()
    state_key = f"pulse_submitted_{today_str}_{user_email}"

    if st.session_state.get(state_key):
        st.sidebar.success("Thanks for your feedback! 🚀")
        return

    # 1. Feedback Faces
    # Mapping: 😞=1, 🙁=2, 😐=3, 🙂=4, 😀=5
    feedback = st.sidebar.feedback("faces")

    if feedback is not None:
        # Convert index (0-4) to score (1-5)
        score = feedback + 1
        
        # 2. Save to DB
        try:
            engine = get_db_engine()
            with engine.connect() as conn:
                # Basic upsert logic (for simplicity, just insert logic here)
                # In prod: Check if record exists for (user, date) and update
                conn.execute(
                    text("""
                    INSERT INTO satisfaction_records (user_email, score, date, created_at, updated_at)
                    VALUES (:email, :score, :date, :now, :now)
                    """),
                    {
                        "email": user_email,
                        "score": score,
                        "date": datetime.date.today(),
                        "now": datetime.datetime.now()
                    }
                )
                conn.commit()
                
            st.session_state[state_key] = True
            st.sidebar.success("Recorded! Have a great day.")
            # Rerun to update any charts listening to this data
            st.rerun()
            
        except Exception as e:
            st.sidebar.error(f"Failed to save: {e}")
