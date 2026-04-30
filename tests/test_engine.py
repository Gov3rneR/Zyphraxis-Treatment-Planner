"""
tests/test_engine.py — Zyphraxis unit tests

Run with:
    pytest tests/ -v
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from med_brain_v6 import (
    MedBrainV6,
    _apply_patient,
    _combine_risk,
    _combine_effectiveness,
    _confidence,
    _filter_eligible,
    TREATMENT_CATALOGUE,
)

def make_engine():
    return MedBrainV6()

class TestApplyPatient:
    def test_no_profile_returns_same(self):
        t = TREATMENT_CATALOGUE[0]
        assert _apply_patient(t, None) is t

    def test_does_not_mutate_original(self):
        t = TREATMENT_CATALOGUE[0].copy()
        original_risk = t["base_risk"]
        _apply_patient(t, {"age": 70, "stage": 3, "frailty": 0.2})
        assert t["base_risk"] == original_risk

    def test_elderly_increases_risk(self):
        t = TREATMENT_CATALOGUE[0]
        young   = _apply_patient(t, {"age": 40, "stage": 1, "frailty": 0.0})
        elderly = _apply_patient(t, {"age": 80, "stage": 1, "frailty": 0.0})
        assert elderly["base_risk"] > young["base_risk"]

    def test_high_stage_increases_risk(self):
        t = TREATMENT_CATALOGUE[0]
        s1 = _apply_patient(t, {"age": 50, "stage": 1, "frailty": 0.0})
        s4 = _apply_patient(t, {"age": 50, "stage": 4, "frailty": 0.0})
        assert s4["base_risk"] > s1["base_risk"]

    def test_risk_clamped(self):
        t = TREATMENT_CATALOGUE[0]
        r = _apply_patient(t, {"age": 99, "stage": 4, "frailty": 5.0})
        assert r["base_risk"] <= 0.99

class TestMathHelpers:
    def test_combine_risk_higher_than_either(self):
        assert _combine_risk(0.1, 0.2) > max(0.1, 0.2)

    def test_combine_effectiveness_higher(self):
        assert _combine_effectiveness(0.5, 0.5) > 0.5

    def test_confidence_same_scores(self):
        assert _confidence(100.0, 100.0) == pytest.approx(0.0, abs=1e-6)

    def test_confidence_negative_scores_in_range(self):
        c = _confidence(-800.0, -600.0)
        assert 0.0 <= c <= 1.0

class TestFilterEligible:
    def test_no_human_excludes_requires_human(self):
        eligible = _filter_eligible(TREATMENT_CATALOGUE, human_use=False)
        for t in eligible:
            assert not t["requires_human"]

    def test_human_use_includes_all(self):
        assert len(_filter_eligible(TREATMENT_CATALOGUE, True)) == len(TREATMENT_CATALOGUE)

class TestMedBrainV6:
    def test_invalid_zero_window(self):
        assert make_engine().run_planner(0)["status"] == "INVALID_INPUT"

    def test_success_basic(self):
        r = make_engine().run_planner(960)
        assert r["status"] == "success"
        assert len(r["plan"]) >= 1

    def test_risk_within_threshold(self):
        r = make_engine().run_planner(960, max_risk=0.25)
        assert r["metrics"]["risk_score"] <= 0.25

    def test_confidence_in_range(self):
        r = make_engine().run_planner(960)
        if r["status"] == "success":
            assert 0 <= r["metrics"]["confidence"] <= 1

    def test_no_path_tight(self):
        r = make_engine().run_planner(1, max_risk=0.001)
        assert r["status"] == "NO_PATH"

    def test_no_human_use(self):
        r = make_engine().run_planner(960, human_use=False)
        if r["status"] == "success":
            plan_ids = {s["treatment_id"] for s in r["plan"]}
            for t in TREATMENT_CATALOGUE:
                if t["requires_human"]:
                    assert t["id"] not in plan_ids

    def test_no_duplicate_modalities(self):
        r = make_engine().run_planner(960)
        if r["status"] == "success" and len(r["plan"]) > 1:
            modalities = [s["modality"] for s in r["plan"]]
            assert len(modalities) == len(set(modalities))

    def test_deterministic(self):
        r1 = make_engine().run_planner(720)
        r2 = make_engine().run_planner(720)
        assert r1["status"] == r2["status"]
        if r1["status"] == "success":
            assert r1["plan"] == r2["plan"]

    def test_plan_step_keys(self):
        r = make_engine().run_planner(960)
        if r["status"] == "success":
            for step in r["plan"]:
                for key in ("treatment_id", "treatment_name", "duration_h", "modality"):
                    assert key in step
