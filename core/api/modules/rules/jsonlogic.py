"""A small JSONLogic evaluator (https://jsonlogic.com) for rule conditions.

Only the operators rules need: no loops, no external calls (docs/domain/rules.md, "Limits").
It must agree with json-logic-js in the browser; a shared example file runs against both.
An unknown operator raises, so a rule can never silently pass.
"""

from collections.abc import Callable
from typing import Any


class JsonLogicError(ValueError):
    pass


_MISSING = object()


def _var(data: Any, path: Any, default: Any = None) -> Any:
    if path is None or path == "":
        return data
    current = data
    for part in str(path).split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return default
    return current


def truthy(value: Any) -> bool:
    """JSONLogic truthiness: empty arrays are false, like json-logic-js."""
    if isinstance(value, list):
        return len(value) > 0
    return bool(value)


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise JsonLogicError(f"Not a number: {value!r}") from None


def _loose_eq(a: Any, b: Any) -> bool:
    if (isinstance(a, int | float) and isinstance(b, str)) or (
        isinstance(b, int | float) and isinstance(a, str)
    ):
        try:
            return float(a) == float(b)
        except ValueError:
            return False
    return a == b


def _compare(op: Callable[[float, float], bool]) -> Callable[..., bool]:
    def run(*args: Any) -> bool:
        if len(args) == 3:  # between: {"<": [1, x, 3]}
            return op(_num(args[0]), _num(args[1])) and op(_num(args[1]), _num(args[2]))
        return op(_num(args[0]), _num(args[1]))

    return run


_OPS: dict[str, Callable[..., Any]] = {
    "==": _loose_eq,
    "!=": lambda a, b: not _loose_eq(a, b),
    "===": lambda a, b: a == b and type(a) is type(b),
    "!==": lambda a, b: not (a == b and type(a) is type(b)),
    ">": _compare(lambda a, b: a > b),
    ">=": _compare(lambda a, b: a >= b),
    "<": _compare(lambda a, b: a < b),
    "<=": _compare(lambda a, b: a <= b),
    "!!": lambda a: truthy(a),
    "in": lambda a, b: a in b if isinstance(b, list | str) else False,
    "+": lambda *a: sum(_num(x) for x in a),
    "*": lambda *a: _product(a),
    "-": lambda a, b=_MISSING: -_num(a) if b is _MISSING else _num(a) - _num(b),
    "/": lambda a, b: _num(a) / _num(b),
    "%": lambda a, b: _num(a) % _num(b),
    "min": lambda *a: min(_num(x) for x in a),
    "max": lambda *a: max(_num(x) for x in a),
    "cat": lambda *a: "".join(str(x) for x in a),
}


def _product(values: tuple[Any, ...]) -> float:
    out = 1.0
    for v in values:
        out *= _num(v)
    return out


def evaluate(logic: Any, data: Any, depth: int = 0) -> Any:
    if depth > 50:
        raise JsonLogicError("Condition nested too deeply.")
    if isinstance(logic, list):
        return [evaluate(item, data, depth + 1) for item in logic]
    if not isinstance(logic, dict) or len(logic) != 1:
        return logic
    op, raw_args = next(iter(logic.items()))
    args = raw_args if isinstance(raw_args, list) else [raw_args]

    # Operators that must not evaluate every argument up front.
    if op == "var":
        values = [evaluate(a, data, depth + 1) for a in args]
        return _var(data, values[0] if values else None, values[1] if len(values) > 1 else None)
    if op == "missing":
        keys = evaluate(args, data, depth + 1)
        keys = keys[0] if keys and isinstance(keys[0], list) else keys
        return [k for k in keys if _var(data, k, _MISSING) in (_MISSING, None, "")]
    if op == "and":
        value: Any = True
        for a in args:
            value = evaluate(a, data, depth + 1)
            if not truthy(value):
                return value
        return value
    if op == "or":
        value = False
        for a in args:
            value = evaluate(a, data, depth + 1)
            if truthy(value):
                return value
        return value
    if op == "!":
        return not truthy(evaluate(args[0], data, depth + 1))
    if op in ("if", "?:"):
        i = 0
        while i + 1 < len(args):
            if truthy(evaluate(args[i], data, depth + 1)):
                return evaluate(args[i + 1], data, depth + 1)
            i += 2
        return evaluate(args[i], data, depth + 1) if i < len(args) else None

    fn = _OPS.get(op)
    if fn is None:
        raise JsonLogicError(f"Unknown operator: {op}")
    values = [evaluate(a, data, depth + 1) for a in args]
    try:
        return fn(*values)
    except TypeError:
        raise JsonLogicError(f"Wrong arguments for {op}") from None


_SPECIAL = frozenset({"var", "missing", "and", "or", "!", "if", "?:"})
KNOWN_OPERATORS = frozenset(_OPS) | _SPECIAL


def check(logic: Any, depth: int = 0) -> None:
    """Reject unknown operators and deep nesting when a rule is saved, not when it runs."""
    if depth > 50:
        raise JsonLogicError("Condition nested too deeply.")
    if isinstance(logic, list):
        for item in logic:
            check(item, depth + 1)
        return
    if isinstance(logic, dict):
        if len(logic) != 1:
            raise JsonLogicError("Each operation is an object with exactly one operator.")
        op, args = next(iter(logic.items()))
        if op not in KNOWN_OPERATORS:
            raise JsonLogicError(f"Unknown operator: {op}")
        check(args, depth + 1)
