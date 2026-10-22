"""NetworkX skill graph and recurring-error practice recommendations."""

from __future__ import annotations

from collections import Counter

import networkx as nx


ERROR_SKILLS = {
    "ERR_THUMB_ABDUCTION": ("thumb_control", "Thumb range and placement drill"),
    "ERR_INDEX_EXT": ("index_extension", "Index extension and hold drill"),
    "ERR_MIDDLE_FLEX": ("middle_finger_control", "Middle finger bend-and-release drill"),
    "ERR_RING_FLEX": ("ring_finger_control", "Ring finger isolation drill"),
    "ERR_PINKY_FLEX": ("pinky_isolation", "Pinky flexion drill #1"),
    "ERR_WRIST_ROTATION": ("palm_orientation", "Palm orientation practice"),
}


def build_skill_graph() -> nx.DiGraph:
    """Build a transparent, provisional error -> skill -> exercise graph.

    Sign nodes are included as skill practice targets. Their mappings are
    scaffolding and should be reviewed by an SLSL instructor before being
    presented as pedagogically validated prerequisites.
    """
    graph = nx.DiGraph()
    for code, (skill, exercise) in ERROR_SKILLS.items():
        graph.add_node(code, kind="error")
        graph.add_node(skill, kind="skill")
        graph.add_node(exercise, kind="exercise", label=exercise)
        graph.add_edge(code, skill, relation="diagnoses")
        graph.add_edge(skill, exercise, relation="remediated_by")

    signs = {
        "book-sign": ("two_hand_coordination", "book-sign"),
        "house-sign": ("two_hand_coordination", "house-sign"),
        "come": ("palm_orientation", "come"),
        "go": ("palm_orientation", "go"),
        "like": ("thumb_control", "like"),
        "pen-sign": ("index_extension", "pen-sign"),
    }
    graph.add_node("two_hand_coordination", kind="skill")
    for sign_id, (skill, label) in signs.items():
        graph.add_node(sign_id, kind="sign", label=label)
        graph.add_edge(sign_id, skill, relation="practices")
    return graph


SKILL_GRAPH = build_skill_graph()


def recommend_from_history(attempts: list[dict], threshold: int = 3) -> list[dict[str, str]]:
    """Recommend practice when an error occurs in at least 3 recent attempts."""
    counts = Counter(
        error
        for attempt in attempts
        for error in set(
            attempt.get("detected_error_codes", attempt.get("detected_errors", []))
        )
    )
    recommendations: list[dict[str, str]] = []
    for error_code, count in counts.items():
        if count < threshold or error_code not in SKILL_GRAPH:
            continue
        skill_nodes = [
            node for node in SKILL_GRAPH.successors(error_code)
            if SKILL_GRAPH.nodes[node].get("kind") == "skill"
        ]
        exercises = [
            SKILL_GRAPH.nodes[node]["label"]
            for skill in skill_nodes
            for node in SKILL_GRAPH.successors(skill)
            if SKILL_GRAPH.nodes[node].get("kind") == "exercise"
        ]
        if exercises:
            recommendations.append({
                "error_code": error_code,
                "skill": skill_nodes[0],
                "exercise": exercises[0],
                "attempt_count": f"{count}/{len(attempts)}",
            })
    return recommendations
