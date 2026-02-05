import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from quantum_solver import generate_scenarios, pareto_front

# ---------- Page config ----------
st.set_page_config(
    page_title="Quantum HR Workforce Optimizer (PEO Demo)",
    page_icon="🧠",
    layout="wide",
)

# ---------- Simple CSS for a polished look ----------
st.markdown("""
<style>
/* App background gradient */
[data-testid="stAppViewContainer"]{
  background: radial-gradient(circle at 15% 20%, rgba(88,101,242,0.10), transparent 35%),
              radial-gradient(circle at 80% 10%, rgba(0,184,255,0.10), transparent 40%),
              radial-gradient(circle at 60% 80%, rgba(0,255,163,0.08), transparent 45%),
              linear-gradient(180deg, rgba(255,255,255,0.85), rgba(255,255,255,0.92));
}
[data-testid="stHeader"]{
  background: rgba(255,255,255,0.0);
}
.big-title {
  font-size: 2.2rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.subtle {
  color: rgba(0,0,0,0.62);
}
.kpi {
  border-radius: 18px;
  padding: 14px 14px;
  background: rgba(255,255,255,0.75);
  border: 1px solid rgba(0,0,0,0.07);
  box-shadow: 0 8px 26px rgba(0,0,0,0.05);
}
.badge {
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(0,0,0,0.10);
  background: rgba(255,255,255,0.75);
  font-size: 0.85rem;
}
hr {
  margin-top: 0.2rem;
  margin-bottom: 1rem;
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,0,0,0.15), transparent);
}
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
left, right = st.columns([3,2])
with left:
    st.markdown('<div class="big-title">🧠 Quantum HR Workforce Optimizer</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle">A playful, hands-on demo for PEO-style workforce planning — inspired by quantum optimization (QUBO-like) thinking.</div>', unsafe_allow_html=True)
    st.markdown('<span class="badge">PEO • Workforce Planning</span> <span class="badge">Quantum-inspired Optimization</span> <span class="badge">Interactive & Shareable</span>', unsafe_allow_html=True)
with right:
    st.markdown('<div class="kpi">', unsafe_allow_html=True)
    st.caption("Live demo knobs (change these and re-run)")
    st.markdown("**Tip:** For LinkedIn, screen-share this and ask viewers to choose the weights in chat.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr/>", unsafe_allow_html=True)

# ---------- Sidebar controls ----------
st.sidebar.title("⚙️ Controls")
st.sidebar.caption("Tune the scenario universe. Then click **Run Optimizer**.")

client_growth = st.sidebar.slider("Client growth / contraction (%)", -20, 30, 10, 1)
target_total = st.sidebar.slider("Target total headcount (FTE-equivalent)", 50, 300, 140, 5)

# Cost assumptions
st.sidebar.subheader("Cost assumptions (annual, USD)")
ft_cost = st.sidebar.number_input("Full-time cost per head", min_value=40000, max_value=240000, value=98000, step=1000)
pt_cost = st.sidebar.number_input("Part-time cost per head", min_value=20000, max_value=140000, value=52000, step=1000)
ct_cost = st.sidebar.number_input("Contractor cost per head", min_value=40000, max_value=260000, value=125000, step=1000)

# Risk parameters
st.sidebar.subheader("Compliance / risk parameters")
state_risk = st.sidebar.select_slider("State complexity factor", options=["Low", "Medium", "High"], value="Medium")
state_risk_map = {"Low": 0.6, "Medium": 1.0, "High": 1.5}
risk_factor = state_risk_map[state_risk]

benefit_richness = st.sidebar.slider("Benefits richness", 0.0, 1.0, 0.55, 0.05)
policy_strictness = st.sidebar.slider("Policy strictness", 0.0, 1.0, 0.60, 0.05)

# Objective weights
st.sidebar.subheader("Objective weights")
w_cost = st.sidebar.slider("Weight: Cost", 0.0, 3.0, 1.0, 0.05)
w_risk = st.sidebar.slider("Weight: Risk", 0.0, 3.0, 1.2, 0.05)
w_ret = st.sidebar.slider("Weight: Retention", 0.0, 3.0, 1.0, 0.05)

# Search / solver controls
st.sidebar.subheader("Solver controls")
num_samples = st.sidebar.slider("Scenario samples", 300, 4000, 1600, 100)
seed = st.sidebar.number_input("Random seed", 1, 99999, 2026, 1)
show_pareto = st.sidebar.checkbox("Show Pareto front (tradeoff set)", value=True)

run = st.sidebar.button("🚀 Run Optimizer", use_container_width=True)

# ---------- Defaults on first load ----------
if "df" not in st.session_state:
    st.session_state.df = None
if "best" not in st.session_state:
    st.session_state.best = None
if "energy" not in st.session_state:
    st.session_state.energy = None

def _run():
    df, best, energy = generate_scenarios(
        target_total=target_total,
        growth_pct=client_growth,
        cost_full_time=ft_cost,
        cost_part_time=pt_cost,
        cost_contractor=ct_cost,
        benefit_richness=benefit_richness,
        policy_strictness=policy_strictness,
        risk_factor=risk_factor,
        w_cost=w_cost,
        w_risk=w_risk,
        w_ret=w_ret,
        n=num_samples,
        seed=int(seed),
    )
    st.session_state.df = df
    st.session_state.best = best
    st.session_state.energy = energy

if run:
    _run()

# Auto-run once so page isn't empty
if st.session_state.df is None:
    _run()

df = st.session_state.df
best = st.session_state.best
energy = st.session_state.energy

# ---------- KPIs ----------
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown('<div class="kpi">', unsafe_allow_html=True)
    st.metric("Best Scenario Score", f"{best['score']:.3f}")
    st.caption("Lower is better (cost + risk - retention)")
    st.markdown('</div>', unsafe_allow_html=True)
with k2:
    st.markdown('<div class="kpi">', unsafe_allow_html=True)
    st.metric("Annual Cost", f"${best['cost']:,.0f}")
    st.caption("Estimated total labor cost")
    st.markdown('</div>', unsafe_allow_html=True)
with k3:
    st.markdown('<div class="kpi">', unsafe_allow_html=True)
    st.metric("Risk Index", f"{best['risk']:.2f}")
    st.caption("Higher = riskier (compliance + churn pressure)")
    st.markdown('</div>', unsafe_allow_html=True)
with k4:
    st.markdown('<div class="kpi">', unsafe_allow_html=True)
    st.metric("Retention Score", f"{best['retention']:.2f}")
    st.caption("Higher = better (benefits + stability)")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr/>", unsafe_allow_html=True)

# ---------- Tabs ----------
tab1, tab2, tab3 = st.tabs(["📈 Tradeoff Map", "🧩 Best Mix Breakdown", "🧪 How the Optimizer Thinks"])

with tab1:
    st.subheader("Tradeoff Map: Cost vs Risk (colored by Retention)")
    plot_df = df.copy()
    if show_pareto:
        pf = pareto_front(plot_df, minimize_cols=["cost","risk"], maximize_cols=["retention"])
        plot_df["is_pareto"] = plot_df.index.isin(pf.index)
    else:
        plot_df["is_pareto"] = False

    fig = px.scatter(
        plot_df,
        x="cost",
        y="risk",
        color="retention",
        size="fte",
        hover_data=["ft","pt","ct","score"],
        symbol="is_pareto",
        title="Each dot is a possible workforce future. Explore the frontier.",
    )
    # highlight best
    fig.add_trace(go.Scatter(
        x=[best["cost"]],
        y=[best["risk"]],
        mode="markers+text",
        text=["BEST"],
        textposition="top center",
        marker=dict(size=14, symbol="star"),
        name="Best"
    ))
    fig.update_layout(height=520, margin=dict(l=10,r=10,t=60,b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.caption("Tip: On LinkedIn, ask viewers to choose weights, then re-run live and watch the BEST star jump.")

with tab2:
    st.subheader("Best Workforce Mix")
    c1, c2 = st.columns([2,3])

    with c1:
        mix = pd.DataFrame({
            "Type": ["Full-time", "Part-time", "Contractor"],
            "Headcount": [best["ft"], best["pt"], best["ct"]],
        })
        bar = px.bar(mix, x="Type", y="Headcount", title="Headcount by worker type")
        bar.update_layout(height=380, margin=dict(l=10,r=10,t=60,b=10))
        st.plotly_chart(bar, use_container_width=True)

        st.markdown("**Operational notes**")
        st.write(
            f"- Target FTE: **{target_total}** → Achieved: **{best['fte']:.1f}**\n"
            f"- Growth shift applied: **{client_growth}%**\n"
            f"- State complexity: **{state_risk}**\n"
        )

    with c2:
        st.subheader("Scenario leaderboard (top 10)")
        cols = ["score","cost","risk","retention","fte","ft","pt","ct"]
        st.dataframe(df.sort_values("score").head(10)[cols], use_container_width=True, height=380)

        st.subheader("Pareto options (if enabled)")
        if show_pareto:
            st.dataframe(
                pareto_front(df, minimize_cols=["cost","risk"], maximize_cols=["retention"])
                .sort_values(["cost","risk"])
                .head(15)[cols],
                use_container_width=True,
                height=250
            )
        else:
            st.info("Enable Pareto front in the sidebar to see the tradeoff set.")

with tab3:
    st.subheader("How it works (executive-friendly)")
    st.write("""
**Quantum-inspired** doesn’t require quantum hardware.  
We borrow the *idea* of exploring many candidate solutions and quickly moving toward low-energy (better) outcomes.

In this demo, each workforce plan is a vector:

- **ft** = full-time headcount  
- **pt** = part-time headcount  
- **ct** = contractor headcount

We score plans using:

**score = w_cost · cost + w_risk · risk − w_ret · retention + penalties**

Then we do a light **simulated annealing**-style search to “cool” toward better outcomes.
""")

    st.subheader("Energy trace (search cooling)")
    e = pd.DataFrame({"step": np.arange(len(energy)), "energy": energy})
    line = px.line(e, x="step", y="energy", title="Lower energy = better scenario")
    line.update_layout(height=420, margin=dict(l=10,r=10,t=60,b=10))
    st.plotly_chart(line, use_container_width=True)

    st.caption("For LinkedIn: explain that this is the same optimization class used in QUBO formulations that quantum annealers and QAOA target.")

st.markdown("<hr/>", unsafe_allow_html=True)

with st.expander("📥 Export results (CSV)"):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download scenarios.csv", data=csv, file_name="scenarios.csv", mime="text/csv")

st.caption("Disclaimer: This is a synthetic demo for education and thought leadership. No real employee data is used.")
