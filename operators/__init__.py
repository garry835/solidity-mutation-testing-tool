"""Registry and factory for mutation operators."""

from typing import Dict, List, Optional
from operators.base_operator import BaseMutationOperator
from operators.unchecked_math import UncheckedMathOperator
from operators.reentrancy import ReentrancyOperator
from operators.timestamp_reliance import TimestampRelianceOperator
from src.exceptions import OperatorNotFoundError

_OPERATOR_REGISTRY: Dict[str, BaseMutationOperator] = {
    "UNCHECKED_MATH": UncheckedMathOperator(),
    "REENTRANCY": ReentrancyOperator(),
    "TIMESTAMP_RELIANCE": TimestampRelianceOperator(),
}

# Alias mapping for friendly CLI flags
_OPERATOR_ALIASES: Dict[str, str] = {
    "unchecked_math": "UNCHECKED_MATH",
    "unchecked": "UNCHECKED_MATH",
    "math": "UNCHECKED_MATH",
    "reentrancy": "REENTRANCY",
    "reentrant": "REENTRANCY",
    "timestamp_reliance": "TIMESTAMP_RELIANCE",
    "timestamp": "TIMESTAMP_RELIANCE",
    "time": "TIMESTAMP_RELIANCE",
}


def get_available_operators() -> List[BaseMutationOperator]:
    """Return instances of all registered mutation operators."""
    return list(_OPERATOR_REGISTRY.values())


def get_operator(name: str) -> BaseMutationOperator:
    """Retrieve an operator instance by name or alias.

    Args:
        name: Name or alias of the operator (e.g. 'unchecked_math', 'REENTRANCY').

    Returns:
        BaseMutationOperator instance.

    Raises:
        OperatorNotFoundError: If operator is not recognized.
    """
    key = name.strip()
    if key in _OPERATOR_REGISTRY:
        return _OPERATOR_REGISTRY[key]
    
    canonical = _OPERATOR_ALIASES.get(key.lower())
    if canonical and canonical in _OPERATOR_REGISTRY:
        return _OPERATOR_REGISTRY[canonical]

    available = list(_OPERATOR_REGISTRY.keys()) + list(_OPERATOR_ALIASES.keys())
    raise OperatorNotFoundError(
        f"Operator '{name}' not found. Available operators: {sorted(list(set(available)))}"
    )
