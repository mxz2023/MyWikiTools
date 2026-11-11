"""机动车尾号限行政策查询核心。"""

from .policy import Policy, validate_policy

__all__ = ["Policy", "validate_policy"]
