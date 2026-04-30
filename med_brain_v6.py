"""
med_brain_v6.py — Zyphraxis Core Engine

Deterministic treatment plan optimizer with:
- multi-objective scoring (time, risk, cost, effectiveness)
- constraint filtering
- patient-aware modifiers
- explainable outputs
- online learning memory

Research use only. Not medical advice.
"""

from __future__ import annotations

import json
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ---------------- CONFIG ---------------- #

DEFAULT_WEIGHTS = {
    "time_w": 1.0,
    "risk_w": 3000.0,
    "cost_w": 0.01,
    "hla_mismatch_w": 100.0,
    "effectiveness_w": 1200.0,
}

THRESHOLDS = {"max_risk": 0.25}

MEMORY_PATH = Path("data/memory.json")
STATS_PATH  = Path("data/stats.json")


# ---------------- DATA STRUCTURES ---------------- #

@dataclass
class SAFWeights:
    time_w: float          = DEFAULT_WEIGHTS["time_w"]
    risk_w: float          = DEFAULT_WEIGHTS["risk_w"]
    cost_w: float          = DEFAULT_WEIGHTS["cost_w"]
    hla_mismatch_w: float  = DEFAULT_WEIGHTS["hla_mismatch_w"]
    effectiveness_w: float = DEFAULT_WEIGHTS["effectiveness_w"]


@dataclass
class PlanCandidate:
    plan: list
    time_h: float
    risk: float
    cost: float
    hla_mismatches: int
    effectiveness: float
    score: float = field(default=0.0, init=False)
    explanation: str = field(default="", init=False)

    def compute_score(self, w: SAFWeights, tumor_escape_h: float) -> None:
        time_pressure = self.time_h / max(tumor_escape_h, 1.0)
        self.score = (
            w.time_w * self.time_h
            + w.risk_w * self.risk
            + w.cost_w * self.cost
            + w.hla_mismatch_w * self.hla_mismatches
            - w.effectiveness_w * self.effectiveness
            + 500.0 * time_pressure
        )


# ---------------- TREATMENTS ---------------- #

TREATMENT_CATALOGUE = [
    {
        "id": "CHEMO_A", "name": "Chemotherapy A",
        "duration_h": 168, "base_risk": 0.10, "cost": 15000,
        "effectiveness": 0.55, "hla_sensitive": False,
        "requires_human": False, "modality": "chemo",
    },
    {
        "id": "CHEMO_B", "name": "Chemotherapy B",
        "duration_h": 120, "base_risk": 0.18, "cost": 22000,
        "effectiveness": 0.62, "hla_sensitive": False,
        "requires_human": False, "modality": "chemo",
    },
    {
        "id": "IMMUNO_2", "name": "Immunotherapy Booster",
        "duration_h": 168, "base_risk": 0.06, "cost": 28000,
        "effectiveness": 0.75, "hla_sensitive": True,
        "requires_human": True, "modality": "immuno",
    },
    {
        "id": "RADIO_STEREO", "name": "SBRT",
        "duration_h": 48, "base_risk": 0.09, "cost": 35000,
        "effectiveness": 0.60, "hla_sensitive": False,
        "requires_human": False, "modality": "radio",
    },
    {
        "id": "TARGETED_X", "name": "Targeted Therapy",
        "duration_h": 504, "base_risk": 0.05, "cost": 60000,
        "effectiveness": 0.70, "hla_sensitive": False,
        "requires_human": True, "modality": "targeted",
    },
]


# ---------------- HELPERS ---------------- #

def _filter_eligible(treatments, human_use):
    return [t for t in treatments if not (t["requires_human"] and not human_use)]


def _estimate_hla(t):
    return 0 if not t["hla_sensitive"] else abs(hash(t["id"])) % 3


def _apply_patient(t, profile):
    """Return a NEW dict with risk/effectiveness adjusted for patient profile."""
    if not profile:
        return t
    t = t.copy()
    age     = float(profile.get("age", 50))
    stage   = min(4, max(1, int(profile.get("stage", 2))))
    frailty = float(profile.get("frailty", 0.0))

    t["base_risk"]    *= 1.0 + (age - 50) * 0.01 + frailty
    t["effectiveness"] *= 1.0 - max(0.0, age - 65) * 0.005
    stage_mult = 1.0 + (stage - 1) * 0.15
    t["base_risk"]     = min(0.99, t["base_risk"] * stage_mult)
    t["effectiveness"] *= 1.0 - (stage - 1) * 0.08
    t["effectiveness"] = max(0.0, min(1.0, t["effectiveness"]))
    t["base_risk"]     = max(0.01, min(0.99, t["base_risk"]))
    return t


def _combine_risk(r1, r2):
    return 1.0 - (1.0 - r1) * (1.0 - r2)


def _combine_effectiveness(e1, e2):
    return 1.0 - (1.0 - e1) * (1.0 - e2)


def _confidence(best_score, second_score):
    """Normalised gap [0,1]. Correct even for negative scores."""
    gap   = second_score - best_score
    denom = abs(second_score) + abs(best_score) + 1e-9
    return max(0.0, min(1.0, gap / denom))


def _load_json(path, default):
    try:
        if Path(path).exists():
            return json.loads(Path(path).read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return default


def _save_json(path, data):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2))
    except OSError:
        pass


# ---------------- ENGINE ---------------- #

class MedBrainV6:

    def __init__(self):
        self.memory = _load_json(MEMORY_PATH, [])
        self.stats  = _load_json(STATS_PATH, {"total_runs": 0, "no_path_count": 0})

    # ------------------------------------------------------------------ #
    # Main entry points
    # ------------------------------------------------------------------ #

    def run(self, tumor_escape_h, human_use=True, profile=None, mode="balanced"):
        """Generate the optimal treatment plan. Returns a result dict."""

        if tumor_escape_h <= 0:
            return {"status": "INVALID_INPUT", "reason": "tumor_escape_h must be > 0"}

        self.stats["total_runs"] = self.stats.get("total_runs", 0) + 1

        # Apply patient profile ONCE per treatment — not inside the combo loop
        base_treatments = _filter_eligible(TREATMENT_CATALOGUE, human_use)
        adjusted = [_apply_patient(t, profile) for t in base_treatments]

        candidates = []

        for i, t1 in enumerate(adjusted):
            candidates.append(self._make_candidate([t1]))

            for j, t2 in enumerate(adjusted):
                if i >= j:                              # deduplicate + skip self
                    continue
                if t1["modality"] == t2["modality"]:   # distinct modalities only
                    continue
                total_time = t1["duration_h"] + t2["duration_h"]
                if total_time > tumor_escape_h * 1.5:
                    continue
                risk = _combine_risk(t1["base_risk"], t2["base_risk"])
                eff  = _combine_effectiveness(t1["effectiveness"], t2["effectiveness"])
                candidates.append(self._make_candidate([t1, t2], risk=risk, eff=eff))

        weights = SAFWeights()
        if mode == "aggressive":
            weights.time_w *= 1.5
            weights.risk_w *= 0.6
        elif mode == "conservative":
            weights.risk_w *= 2.0

        for c in candidates:
            c.compute_score(weights, tumor_escape_h)

        feasible = [
            c for c in candidates
            if c.time_h <= tumor_escape_h and c.risk <= THRESHOLDS["max_risk"]
        ]

        if not feasible:
            self.stats["no_path_count"] = self.stats.get("no_path_count", 0) + 1
            _save_json(STATS_PATH, self.stats)
            return {
                "status": "NO_PATH",
                "reason": (
                    "No plan fits within the tumor escape window and risk threshold. "
                    "Consider relaxing max_risk or extending the escape window."
                ),
            }

        feasible.sort(key=lambda x: x.score)
        best   = feasible[0]
        second = feasible[1] if len(feasible) > 1 else best

        best.explanation = self._explain(best, tumor_escape_h)
        _save_json(STATS_PATH, self.stats)

        return {
            "status": "success",
            "plan": [
                {
                    "step":           idx + 1,
                    "treatment_id":   s["id"],
                    "treatment_name": s["name"],
                    "duration_h":     s["duration_h"],
                    "modality":       s["modality"],
                }
                for idx, s in enumerate(best.plan)
            ],
            "metrics": {
                "total_time_h":   best.time_h,
                "risk_score":     round(best.risk, 3),
                "estimated_cost": best.cost,
                "hla_mismatches": best.hla_mismatches,
                "effectiveness":  round(best.effectiveness, 3),
                "confidence":     round(_confidence(best.score, second.score), 3),
            },
            "explanation":  best.explanation,
            "alternatives": len(feasible) - 1,
        }

    def run_planner(self, tumor_escape_h, max_risk=0.25, human_use=True,
                    profile=None, mode="balanced"):
        """API-facing wrapper — respects caller-supplied max_risk."""
        original = THRESHOLDS["max_risk"]
        THRESHOLDS["max_risk"] = max_risk
        try:
            return self.run(
                tumor_escape_h=tumor_escape_h,
                human_use=human_use,
                profile=profile,
                mode=mode,
            )
        finally:
            THRESHOLDS["max_risk"] = original

    def update_from_outcome(self, plan, observed_time, observed_risk):
        """Persist an observed outcome for future analysis / retraining."""
        entry = {
            "timestamp":     datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "plan":          plan,
            "observed_time": observed_time,
            "observed_risk": observed_risk,
        }
        self.memory.append(entry)
        _save_json(MEMORY_PATH, self.memory)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _make_candidate(self, steps, risk=None, eff=None):
        return PlanCandidate(
            plan=steps,
            time_h=sum(s["duration_h"] for s in steps),
            risk=risk if risk is not None else steps[0]["base_risk"],
            cost=sum(s["cost"] for s in steps),
            hla_mismatches=sum(_estimate_hla(s) for s in steps),
            effectiveness=eff if eff is not None else steps[0]["effectiveness"],
        )

    def _explain(self, c, window):
        names       = " → ".join(s["name"] for s in c.plan)
        buffer_days = round((window - c.time_h) / 24, 1)
        return (
            f"{names} | {c.time_h}h total | risk {c.risk:.1%} | "
            f"effectiveness {c.effectiveness:.1%} | {buffer_days}d buffer"
        )


# ---------------- LEGACY WRAPPER ---------------- #

_MODE_MAP = {
    "apollo":    "conservative",
    "manhattan": "aggressive",
    "balanced":  "balanced",
}


def run_engine(tumor_escape_h, human_override=True, patient_profile=None, mode="apollo"):
    """Legacy entry point. Translates external mode names to internal ones."""
    return MedBrainV6().run(
        tumor_escape_h=tumor_escape_h,
        human_use=human_override,
        profile=patient_profile,
        mode=_MODE_MAP.get(mode, "balanced"),
    )
