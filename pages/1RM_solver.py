import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="1RM Solver", layout="centered")

st.title("🏋️ 1RM Solver")
st.write("Dual-mode: Estimate from performance or Calculate from target.")

# Tabs
tab1, tab2 = st.tabs(["📊 Estimate 1RM", "🎯 Calculate Load"])

# --- Tab 1: Estimate 1RM ---
with tab1:
    st.subheader("Estimate 1RM from Current Performance")
    col1, col2 = st.columns(2)
    with col1:
        w_act = st.number_input("Weight (kg)", min_value=0.0, value=50.0, step=2.5, key="w1")
    with col2:
        r_act = st.number_input("Reps", min_value=1, max_value=30, value=10, key="r1")
    
    # O'Conner Formula: 1RM = Weight * (1 + 0.025 * Reps)
    est_1rm = w_act * (1 + 0.025 * r_act)
    
    st.success(f"Estimated 1RM: **{est_1rm:.2f} kg**")

# --- Tab 2: Calculate Load ---
with tab2:
    st.subheader("Target Load Calculation")
    # Use estimated 1RM from Tab 1 as default
    target_1rm = st.number_input("Current 1RM (kg)", min_value=0.0, value=est_1rm, step=2.5, key="t1")
    
    st.write("---")
    st.write(f"💡 **Rep-Based Load Chart (Base: {target_1rm:.2f} kg)**")
    st.caption("Estimated weight for each rep range (2 reps and above).")

    # Data generation (Starting from 2 reps to 12 reps)
    data = []
    for r in range(2, 13):
        # Formula: Weight = 1RM / (1 + 0.025 * Reps)
        w = target_1rm / (1 + 0.025 * r)
        # Intensity (%) = (w / target_1rm) * 100
        intensity = (w / target_1rm) * 100
        data.append({
            "Target Reps": f"{r} reps",
            "Weight (kg)": f"{w:.2f} kg",
            "Intensity (%)": f"{intensity:.1f} %"
        })

    # Display as Table
    df = pd.DataFrame(data)
    st.table(df)

    st.write("---")
    # Individual Calculator
    st.subheader("Quick Simulation")
    target_reps = st.slider("Target Reps", 2, 20, 10)
    calc_weight = target_1rm / (1 + 0.025 * target_reps)
    st.info(f"Target Weight: **{calc_weight:.2f} kg** for **{target_reps} reps**")

st.write("---")
st.caption("Formula: O'Conner's Formula")