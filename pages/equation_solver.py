import streamlit as st
from sympy import sympify, solve, symbols, Eq, lambdify
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Numerical Solver Pro", layout="wide")

st.title("📐 Interactive Solver & Grapher")
st.caption("TI-89 Logic with Dynamic History & Visualization")

# --- Session State ---
if 'eq_history' not in st.session_state:
    st.session_state.eq_history = []
if 'current_sols' not in st.session_state:
    st.session_state.current_sols = []

# --- Layout ---
col_in, col_gr = st.columns([1, 2], gap="large")

with col_in:
    st.subheader("Define Equation")
    left_side = st.text_input("Left Side (f(x))", value="x**2 - 4*x")
    st.markdown("<h3 style='text-align: center;'>=</h3>", unsafe_allow_html=True)
    right_side = st.text_input("Right Side (g(x))", value="5")
    
    target_var = st.text_input("Variable", value="x")
    solve_btn = st.button("SOLVE & PLOT", width='stretch', type="primary")

    if solve_btn:
        try:
            var = symbols(target_var)
            lhs = sympify(left_side)
            rhs = sympify(right_side)
            equation = Eq(lhs, rhs)
            sols = solve(equation, var)
            
            if sols:
                st.session_state.current_sols = sols
                res_str = f"{left_side} = {right_side} → {target_var} = {sols}"
                st.session_state.eq_history.insert(0, res_str)
            else:
                st.session_state.current_sols = []
        except:
            st.error("Syntax Error: Check your format (e.g., 2*x)")

    # --- Refined Result Area ---
    if st.session_state.current_sols:
        st.write("---")
        st.markdown("<p style='color: #888; font-size: 0.9rem; letter-spacing: 0.1rem;'>RESULT ANALYSIS</p>", unsafe_allow_html=True)
        
        for i, s in enumerate(st.session_state.current_sols):
            try:
                val = float(s) if s.is_real else s
                formatted_val = f"{val:,.4f}" if isinstance(val, float) else str(val)
                
                st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #1a1a1a 0%, #0d2b24 100%);
                        padding: 20px;
                        border-radius: 8px;
                        border: 1px solid #00aa88;
                        margin-bottom: 15px;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                        text-align: center;
                    ">
                        <div style="color: #00aa88; font-size: 0.8rem; margin-bottom: 5px;">ROOT {i+1} ({target_var})</div>
                        <div style="color: #e0e0e0; font-size: 2.8rem; font-weight: 300; font-family: monospace;">{formatted_val}</div>
                    </div>
                """, unsafe_allow_html=True)
            except:
                st.info(f"{target_var} = {s}")

with col_gr:
    if st.session_state.current_sols:
        try:
            s_floats = [float(s) for s in st.session_state.current_sols if s.is_real]
            margin = max(abs(max(s_floats) - min(s_floats)), 4) if s_floats else 10
            x_range = np.linspace(min(s_floats)-margin, max(s_floats)+margin, 400)
            
            f_lhs = lambdify(symbols(target_var), sympify(left_side), "numpy")
            f_rhs = lambdify(symbols(target_var), sympify(right_side), "numpy")
            y_lhs = f_lhs(x_range)
            y_rhs = f_rhs(x_range) if isinstance(f_rhs(x_range), np.ndarray) else np.full_like(x_range, f_rhs(x_range))

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_range, y=y_lhs, name="f(x)", line=dict(color='#00FFCC', width=3)))
            fig.add_trace(go.Scatter(x=x_range, y=y_rhs, name="g(x)", line=dict(color='#FF4B4B', dash='dash')))
            for s in s_floats:
                fig.add_trace(go.Scatter(x=[s], y=[f_lhs(s)], mode='markers', marker=dict(color='white', size=12, symbol='circle-open', line=dict(width=3)), name=f'Sol: {s:.3f}'))
            fig.update_layout(template="plotly_dark", hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig, width='stretch')
        except:
            st.info("Input a valid equation to see the graph.")