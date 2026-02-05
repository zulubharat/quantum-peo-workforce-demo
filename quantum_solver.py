from __future__ import annotations
import math
import random
import pandas as pd

def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(x)))

def _compute_metrics(ft: int, pt: int, ct: int,
                     target_total: int,
                     growth_pct: int,
                     cost_full_time: float,
                     cost_part_time: float,
                     cost_contractor: float,
                     benefit_richness: float,
                     policy_strictness: float,
                     risk_factor: float):
    """
    Synthetic metric model (PEO flavored):
    - FTE: FT = 1.0, PT = 0.5, Contractor = 1.0
    - Cost: linear with headcount + small nonlinear overhead
    - Risk: increases with contractors + state complexity; decreases with strict policies
    - Retention: increases with benefits and FT share; decreases with contractor share
    """
    fte = ft * 1.0 + pt * 0.5 + ct * 1.0

    # Growth shifts target slightly (simulate new client demand)
    effective_target = target_total * (1.0 + growth_pct / 100.0)

    # Cost: add a small overhead for coordination complexity (nonlinear)
    base_cost = ft * cost_full_time + pt * cost_part_time + ct * cost_contractor
    overhead = (0.000004 * (ft + pt + ct) ** 2) * base_cost
    cost = base_cost + overhead

    # Risk: contractors elevate compliance variance; strict policies reduce it
    contractor_ratio = ct / max(1, (ft + pt + ct))
    risk = risk_factor * (0.65 + 1.35 * contractor_ratio) * (1.2 - 0.7 * policy_strictness)

    # Retention: benefits + FT share help, contractors reduce stability
    ft_ratio = ft / max(1, (ft + pt + ct))
    retention = (0.7 + 1.6 * benefit_richness) * (0.65 + 0.9 * ft_ratio) * (1.0 - 0.55 * contractor_ratio)

    # Penalty if FTE deviates from effective target
    fte_gap = abs(fte - effective_target)
    penalty = (fte_gap ** 2) * 0.06  # quadratic penalty

    return {
        "ft": ft, "pt": pt, "ct": ct,
        "fte": fte,
        "effective_target": effective_target,
        "cost": cost,
        "risk": risk,
        "retention": retention,
        "penalty": penalty
    }

def _score(m, w_cost: float, w_risk: float, w_ret: float) -> float:
    # Normalize cost for scoring stability
    cost_scaled = m["cost"] / 1_000_000.0  # in millions
    return w_cost * cost_scaled + w_risk * m["risk"] - w_ret * m["retention"] + (m["penalty"] / 100.0)

def generate_scenarios(
    target_total: int,
    growth_pct: int,
    cost_full_time: float,
    cost_part_time: float,
    cost_contractor: float,
    benefit_richness: float,
    policy_strictness: float,
    risk_factor: float,
    w_cost: float,
    w_risk: float,
    w_ret: float,
    n: int = 1500,
    seed: int = 2026,
):
    """
    Generate a pool of random + annealed scenarios, return:
      - df of scenarios
      - best scenario dict
      - energy trace
    """
    rng = random.Random(seed)

    # initial guess around target
    ft = int(target_total * 0.60)
    pt = int(target_total * 0.25)
    ct = max(0, int(target_total * 0.15))

    # annealing parameters
    T0 = 2.0
    Tmin = 0.05
    steps = max(400, int(n * 0.35))
    energy_trace = []

    def propose(ft, pt, ct):
        # small local move
        delta_ft = rng.randint(-6, 6)
        delta_pt = rng.randint(-10, 10)
        delta_ct = rng.randint(-6, 6)
        return (
            _clamp_int(ft + delta_ft, 0, target_total * 3),
            _clamp_int(pt + delta_pt, 0, target_total * 3),
            _clamp_int(ct + delta_ct, 0, target_total * 3),
        )

    # keep a set of scenarios
    rows = []

    # random spray (diversity)
    for _ in range(max(200, int(n * 0.50))):
        r_ft = rng.randint(0, target_total * 2)
        r_pt = rng.randint(0, target_total * 2)
        r_ct = rng.randint(0, target_total * 2)
        m = _compute_metrics(
            r_ft, r_pt, r_ct,
            target_total, growth_pct,
            cost_full_time, cost_part_time, cost_contractor,
            benefit_richness, policy_strictness, risk_factor
        )
        sc = _score(m, w_cost, w_risk, w_ret)
        rows.append({**m, "score": sc})

    # annealing search (exploitation)
    current = _compute_metrics(
        ft, pt, ct,
        target_total, growth_pct,
        cost_full_time, cost_part_time, cost_contractor,
        benefit_richness, policy_strictness, risk_factor
    )
    current_energy = _score(current, w_cost, w_risk, w_ret)

    for i in range(steps):
        # temperature schedule
        T = max(Tmin, T0 * (1 - i / steps))
        p_ft, p_pt, p_ct = propose(current["ft"], current["pt"], current["ct"])
        cand = _compute_metrics(
            p_ft, p_pt, p_ct,
            target_total, growth_pct,
            cost_full_time, cost_part_time, cost_contractor,
            benefit_richness, policy_strictness, risk_factor
        )
        cand_energy = _score(cand, w_cost, w_risk, w_ret)

        accept = False
        if cand_energy < current_energy:
            accept = True
        else:
            # metropolis criterion
            prob = math.exp(-(cand_energy - current_energy) / max(1e-9, T))
            if rng.random() < prob:
                accept = True

        if accept:
            current, current_energy = cand, cand_energy

        energy_trace.append(current_energy)
        rows.append({**current, "score": current_energy})

    # keep only n best-ish diverse points
    df = pd.DataFrame(rows).drop_duplicates(subset=["ft","pt","ct"])
    df = df.sort_values("score").head(max(n, 600)).reset_index(drop=True)

    best = df.iloc[0].to_dict()
    return df, best, energy_trace

def pareto_front(df, minimize_cols=None, maximize_cols=None):
    minimize_cols = minimize_cols or []
    maximize_cols = maximize_cols or []

    # Convert maximize to minimize by negating
    work = df.copy()
    for c in maximize_cols:
        work[c] = -work[c]

    # Simple O(n^2) pareto for demo-sized df
    idxs = []
    vals = work[minimize_cols + maximize_cols].values
    for i in range(len(work)):
        dominated = False
        for j in range(len(work)):
            if i == j:
                continue
            # j dominates i if <= in all and < in at least one
            if (vals[j] <= vals[i]).all() and (vals[j] < vals[i]).any():
                dominated = True
                break
        if not dominated:
            idxs.append(i)
    return df.iloc[idxs]
