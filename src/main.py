s = "[1,2,3, 4.0]"
# make integer list from string
def make_list_from_string(s: str) -> list[int]:
    """
    Converts a string representation of a list of integers into an actual list of integers.
    :param s: String representation of a list of integers
    :return: List of integers
    """
    try:
        new_list = []
        for x in s.strip("[]").split(","):
            if x.strip().isdigit():
                new_list.append(int(x.strip()))
            else:
                try:
                    new_list.append(float(x.strip()))
                except ValueError:
                    pass
        return new_list
    except Exception as e:
        print(f"Error converting string to list: {e}")
        return []
print(make_int_list_from_string("[1,2,3, 4.0]"))


