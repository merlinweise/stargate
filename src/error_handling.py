import sys
from fractions import Fraction


def print_warning(reason: str) -> None:
    """
    Prints a warning message.
    :param reason: Reason for the warning
    :type reason: str
    """
    print(f"WARNING: {reason}")


def print_error(reason: str) -> None:
    """
    Prints an error message and exits the program.
    :param reason: Reason for the error
    :type reason: str
    """
    print(f"ERROR: {reason}")
    sys.exit(1)


def print_debug(reason: str) -> None:
    """
    Prints debug information.
    :param reason: Reason for the debug message
    :type reason: str
    """
    print(f"DEBUG: {reason}")


def is_float_expr(s: str) -> bool:
    """
    Check if the string s is a valid float expression.
    :param s: String to check
    :type s: str
    :return: True if s is a valid float expression, False otherwise
    :rtype: bool
    """
    try:
        if not all(c in "0123456789+*-/(). " for c in s):
            return False
        result = eval(s)
        return isinstance(result, (int, float))
    except Exception:
        return False


def float_or_fraction(f: float, max_d: int) -> str:
    """
    Convert a float to a string representation, either as a float or as a fraction depending on the better representation.
    :param f: Float to convert
    :type f: float
    :param max_d: Maximum denominator for the fraction
    :type max_d: int
    :return: String representation of the float or fraction
    :rtype: str
    """
    fract = Fraction(f).limit_denominator(max_d)
    if len(str(f)) < len(str(fract)):
        return str(f)
    else:
        return str(fract)
