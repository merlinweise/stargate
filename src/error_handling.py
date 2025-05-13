import sys
from fractions import Fraction


def print_warning(reason: str):
    print(f"WARNING: {reason}")


def print_error(reason: str):
    print(f"ERROR: {reason}")
    sys.exit(1)


def print_debug(reason: str):
    print(f"DEBUG: {reason}")


def is_float_expr(s):
    try:
        # Nur erlaubte Zeichen prüfen (Zahlen, Operatoren, Klammern, Leerzeichen, Punkt)
        if not all(c in "0123456789+*-/(). " for c in s):
            return False
        result = eval(s)
        return isinstance(result, (int, float))
    except Exception as e:
        return False


def float_or_fraction(f: float, max_d: int) -> str:
    fract = Fraction(f).limit_denominator(max_d)
    if len(str(f)) < len(str(fract)):
        return str(f)
    else:
        return str(fract)
