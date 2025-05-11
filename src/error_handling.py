import sys


def print_warning(reason: str):
    print(f"Warning: {reason}")


def print_error(reason: str):
    print(f"Error: {reason}")
    sys.exit(1)


def is_float_expr(s):
    try:
        # Nur erlaubte Zeichen prüfen (Zahlen, Operatoren, Klammern, Leerzeichen, Punkt)
        if not all(c in "0123456789+*-/(). " for c in s):
            return False
        result = eval(s)
        return isinstance(result, (int, float))
    except Exception as e:
        return False
