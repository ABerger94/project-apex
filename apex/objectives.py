from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgiLevel:
    level: int
    name: str
    description: str
    required_capabilities: tuple[str, ...]


AGI_LEVELS: tuple[AgiLevel, ...] = (
    AgiLevel(
        level=1,
        name="Conversational AI/Chatbots",
        description=(
            "AI systems can hold conversations with humans, understand and respond to "
            "human language, and support applications such as customer service, virtual "
            "assistance, and human-like interaction."
        ),
        required_capabilities=("conversation", "language_understanding", "helpful_response"),
    ),
    AgiLevel(
        level=2,
        name="Human-Level Problem Solving/Reasoners",
        description=(
            "AI systems can solve problems at a human level, provide more accurate "
            "responses, evaluate reliability, and reduce hallucinations in settings where "
            "correctness matters."
        ),
        required_capabilities=("reasoning", "reliability_evaluation", "hallucination_reduction"),
    ),
    AgiLevel(
        level=3,
        name="Agents",
        description=(
            "AI systems can take actions on behalf of users, perform tasks, make "
            "decisions, execute plans autonomously, and verify outcomes."
        ),
        required_capabilities=("autonomous_action", "task_execution", "plan_execution", "outcome_verification"),
    ),
    AgiLevel(
        level=4,
        name="Innovators",
        description=(
            "AI systems can create new innovations by generating original ideas, "
            "inventions, and approaches that push beyond routine problem solving."
        ),
        required_capabilities=("original_ideas", "validated_novelty", "invention", "measured_improvement"),
    ),
    AgiLevel(
        level=5,
        name="Organizers",
        description=(
            "AI systems can perform the work of entire organizations by managing complex "
            "processes, making high-level decisions, and coordinating large-scale operations."
        ),
        required_capabilities=("organization_scale_coordination", "complex_process_management", "high_level_decision_making", "large_scale_operations"),
    ),
)

TARGET_AGI_LEVEL = 5
TARGET_OBJECTIVE = (
    "Reach and act as a Level 5 AGI Organizer: manage complex processes, make "
    "high-level decisions, and coordinate large-scale operations with evidence, "
    "verification, and accountability."
)


def target_level() -> AgiLevel:
    return level_by_number(TARGET_AGI_LEVEL)


def level_by_number(level: int) -> AgiLevel:
    for item in AGI_LEVELS:
        if item.level == level:
            return item
    raise ValueError(f"Unknown AGI level: {level}")


def objective_directive() -> str:
    lines = [TARGET_OBJECTIVE, "", "AGI capability ladder:"]
    for item in AGI_LEVELS:
        lines.append(f"L{item.level} {item.name}: {item.description}")
    return "\n".join(lines)

