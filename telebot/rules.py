"""Rule engine powering Telebot automation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, List, Pattern


class ActionType(str, Enum):
    DELETE = "delete"
    MUTE = "mute"
    REPLY = "reply"
    ADD_POINTS = "add_points"


@dataclass
class Action:
    type: ActionType
    message: str | None = None
    duration: int | None = None
    points: int | None = None


@dataclass
class Rule:
    name: str
    trigger: Pattern[str]
    action: Action
    delete_original: bool = False

    def matches(self, text: str) -> bool:
        return bool(self.trigger.search(text))


@dataclass
class RuleMatch:
    rule: Rule
    action: Action


class RuleEngine:
    """Evaluate incoming text against configured rules."""

    def __init__(self, rules: Iterable[Rule]) -> None:
        self.rules: List[Rule] = list(rules)

    def match(self, text: str) -> List[RuleMatch]:
        matches: List[RuleMatch] = []
        for rule in self.rules:
            if rule.matches(text):
                matches.append(RuleMatch(rule=rule, action=rule.action))
        return matches

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "RuleEngine":
        rules: List[Rule] = []

        for keyword in config.get("banned_keywords", []):
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            rules.append(
                Rule(
                    name=f"ban:{keyword}",
                    trigger=pattern,
                    action=Action(type=ActionType.DELETE),
                    delete_original=True,
                )
            )

        for reply in config.get("auto_replies", []):
            trigger = re.compile(re.escape(reply["keyword"]), re.IGNORECASE)
            rules.append(
                Rule(
                    name=f"reply:{reply['keyword']}",
                    trigger=trigger,
                    action=Action(type=ActionType.REPLY, message=reply["reply"]),
                    delete_original=reply.get("delete_original", False),
                )
            )

        for punish in config.get("punishments", []):
            trigger = re.compile(punish["regex"], re.IGNORECASE)
            rules.append(
                Rule(
                    name=f"punish:{punish['regex']}",
                    trigger=trigger,
                    action=Action(
                        type=ActionType.MUTE,
                        duration=punish.get("mute_seconds", 60),
                        message=punish.get("notice"),
                    ),
                    delete_original=punish.get("delete_original", True),
                )
            )

        for point_rule in config.get("point_rules", []):
            trigger = re.compile(point_rule["regex"], re.IGNORECASE)
            rules.append(
                Rule(
                    name=f"points:{point_rule['regex']}",
                    trigger=trigger,
                    action=Action(type=ActionType.ADD_POINTS, points=point_rule.get("points", 1)),
                    delete_original=False,
                )
            )

        return cls(rules)
