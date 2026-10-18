"""Generate correlated prototype datasets. Not real employee data."""
from __future__ import annotations

import csv
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "datasets"
DS.mkdir(exist_ok=True)

RNG = random.Random(42)

LOW_TXT = [
    "Completed my assigned tasks and the workload feels manageable today.",
    "Had a focused morning and finished the review without extra hours.",
    "Team standup was brief and I have a clear plan for the afternoon.",
    "Energy is decent and the current sprint scope feels reasonable.",
    "Wrapped the ticket early and helped a teammate with a small question.",
    "Meetings were light and I had time to document yesterday's change.",
    "Feeling calm after a regular eight-hour day with no blockers.",
    "Priorities are clear and I do not expect to stay late tonight.",
    " Pair programming went smoothly and we closed the bug before lunch.",
    "Leave tomorrow is planned so I wrapped my handover notes today.",
]
MOD_TXT = [
    "I have several tasks today and may need some extra time this evening.",
    "Two reviews landed together so the afternoon will be tight.",
    "Deadline is tomorrow and I am slightly behind on the last test cases.",
    "Context switching between support and feature work is slowing me down.",
    "Need another hour to finish the API contract after stand-up overflow.",
    "A blocker on staging is unresolved but I have a workaround in mind.",
    "Workload is heavier than I expected this morning, still doable.",
    "Might slip one low-priority item to keep the release on track.",
    "Stand-up ran long and I lost a chunk of deep-work time.",
    "Feeling a bit stretched but the team can cover if I flag it early.",
]
HIGH_TXT = [
    "I am overloaded with multiple urgent tasks and cannot keep up with the deadlines.",
    "Three high-priority tickets landed at once and I am exhausted already.",
    "Been staying late all week and still the backlog keeps growing.",
    "I feel overwhelmed and frustrated that blockers are not getting unblocked.",
    "Cannot finish this sprint scope without weekend work which I want to avoid.",
    "Constant context switching and urgent pings are draining my focus completely.",
    "I am struggling to meet today's deadline and the next one is already overlapping.",
    "Too many tasks, too little time, and I am not sleeping well because of it.",
    "Support queue plus feature work is unsustainable this week.",
    "I told my manager I am at capacity but more work was still assigned.",
]


def clip(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def correlated_row(i: int) -> dict:
    base = RNG.uniform(0.15, 0.85)
    noise = lambda s: RNG.gauss(0, s)
    stress = clip(base * 100 + noise(8))
    workload = clip(base * 95 + noise(9) + (8 if base > 0.6 else 0))
    overtime = clip((base * 18) + noise(3), 0, 24)
    hours = clip(7.5 + base * 3.5 + noise(0.4), 5, 13)
    wlb = clip(100 - stress * 0.55 - overtime * 2 + noise(6))
    energy = clip(100 - stress * 0.5 + noise(7))
    mood = clip(100 - stress * 0.4 + noise(8))
    sat = clip(90 - workload * 0.35 + noise(7))
    attend = clip(98 - (4 if base > 0.7 else 0) + noise(2), 70, 100)
    leave_f = clip((3 if base > 0.65 else 1) + abs(noise(0.6)), 0, 12)
    complete = clip(92 - workload * 0.25 + noise(5), 20, 100)
    deadline = clip(workload * 0.7 + noise(8))
    difficulty = clip(40 + base * 40 + noise(8))
    exp_wl = clip(workload - RNG.uniform(0, 18))
    act_wl = clip(workload + (RNG.uniform(0, 15) if base > 0.55 else RNG.uniform(-5, 8)))
    exp_h = 8
    act_h = hours
    # communication aligned with base
    if base > 0.62:
        txt = RNG.choice(HIGH_TXT)
        sent, cstress, cneg = -0.55 + noise(0.1), 0.75 + abs(noise(0.08)), 0.7 + abs(noise(0.08))
    elif base > 0.4:
        txt = RNG.choice(MOD_TXT)
        sent, cstress, cneg = -0.1 + noise(0.15), 0.45 + noise(0.1), 0.35 + abs(noise(0.1))
    else:
        txt = RNG.choice(LOW_TXT)
        sent, cstress, cneg = 0.45 + noise(0.1), 0.18 + abs(noise(0.08)), 0.12 + abs(noise(0.06))
    sent = max(-1, min(1, sent))
    cstress = max(0, min(1, cstress))
    cneg = max(0, min(1, cneg))
    # latent + noise → label (not used as a feature)
    latent = (
        0.18 * (stress / 100)
        + 0.16 * (workload / 100)
        + 0.12 * (overtime / 12)
        + 0.10 * ((hours - 8) / 4)
        + 0.10 * (1 - wlb / 100)
        + 0.08 * (1 - energy / 100)
        + 0.08 * (deadline / 100)
        + 0.08 * cstress
        + 0.06 * cneg
        + 0.04 * ((act_wl - exp_wl) / 50)
        + noise(0.07)
    )
    if latent < 0.38:
        label = "LOW"
    elif latent < 0.62:
        label = "MODERATE"
    else:
        label = "HIGH"
    return {
        "employee_id": 1000 + i,
        "stress_score": round(stress, 2),
        "workload_score": round(workload, 2),
        "work_life_balance_score": round(wlb, 2),
        "energy_score": round(energy, 2),
        "mood_score": round(mood, 2),
        "job_satisfaction_score": round(sat, 2),
        "working_hours": round(hours, 2),
        "overtime_hours": round(overtime, 2),
        "attendance_rate": round(attend, 2),
        "leave_frequency": round(leave_f, 2),
        "task_completion_rate": round(complete, 2),
        "deadline_pressure": round(deadline, 2),
        "task_difficulty": round(difficulty, 2),
        "expected_workload": round(exp_wl, 2),
        "actual_workload": round(act_wl, 2),
        "workload_deviation": round(act_wl - exp_wl, 2),
        "expected_working_hours": exp_h,
        "actual_working_hours": round(act_h, 2),
        "working_hour_deviation": round(act_h - exp_h, 2),
        "communication_sentiment": round(sent, 3),
        "communication_stress_score": round(cstress, 3),
        "communication_negative_score": round(cneg, 3),
        "communication_text": txt,
        "burnout_label": label,
    }


COMM_EXTRA = []
for s in LOW_TXT:
    COMM_EXTRA.append((s, "LOW_STRESS", "POSITIVE"))
for s in MOD_TXT:
    COMM_EXTRA.append((s, "MODERATE_STRESS", "NEUTRAL"))
for s in HIGH_TXT:
    COMM_EXTRA.append((s, "HIGH_STRESS", "NEGATIVE"))
# extra paraphrases
COMM_EXTRA += [
    ("Shipped the patch and logged off on time.", "LOW_STRESS", "POSITIVE"),
    ("Quiet afternoon, no incidents on the board.", "LOW_STRESS", "POSITIVE"),
    ("Need to juggle two reviews before EOD.", "MODERATE_STRESS", "NEUTRAL"),
    ("Slightly behind but the plan is still intact.", "MODERATE_STRESS", "NEUTRAL"),
    ("I cannot keep this pace for another sprint.", "HIGH_STRESS", "NEGATIVE"),
    ("Overtime every night is burning me out.", "HIGH_STRESS", "NEGATIVE"),
    ("Grateful for the clearer priorities this week.", "LOW_STRESS", "POSITIVE"),
    ("A bit anxious about tomorrow's demo.", "MODERATE_STRESS", "NEUTRAL"),
    ("Blocked for hours and nobody is responding.", "HIGH_STRESS", "NEGATIVE"),
]


def main():
    rows = [correlated_row(i) for i in range(1200)]
    fields = list(rows[0].keys())
    with open(DS / "burnout_training.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(DS / "communication_training.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "stress_class", "sentiment_class", "source"])
        w.writeheader()
        for r in rows:
            sc = {"LOW": "LOW_STRESS", "MODERATE": "MODERATE_STRESS", "HIGH": "HIGH_STRESS"}[r["burnout_label"]]
            sent = "NEGATIVE" if r["communication_sentiment"] < -0.2 else ("POSITIVE" if r["communication_sentiment"] > 0.2 else "NEUTRAL")
            w.writerow({"text": r["communication_text"], "stress_class": sc, "sentiment_class": sent, "source": "synthetic_aligned"})
        for text, sc, sent in COMM_EXTRA:
            w.writerow({"text": text, "stress_class": sc, "sentiment_class": sent, "source": "synthetic_template"})
    print(f"wrote {len(rows)} burnout rows and communication samples to {DS}")


if __name__ == "__main__":
    main()
