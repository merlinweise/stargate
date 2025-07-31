import os
import re
from pathlib import PureWindowsPath


def linux_to_windows_path(path: str) -> str:
    """
    Converts a Linux or SMB path to a Windows path.
    :param path: Path in Linux or SMB format
    :type path: str
    :return: Path in Windows format
    :rtype: str
    """
    path = path.strip()

    if path.startswith('smb://'):
        stripped = path[len('smb://'):]
        parts = stripped.split('/')
        if len(parts) >= 2:
            server = parts[0]
            share = parts[1]
            rest = '\\'.join(parts[2:]) if len(parts) > 2 else ''
            return f"\\\\{server}\\{share}" + (f"\\{rest}" if rest else "")
        else:
            return "\\\\" + stripped.replace('/', '\\')

    if path.startswith('/mnt/'):
        parts = path.lstrip('/').split('/')
        if len(parts) >= 2:
            drive = parts[1].upper()
            rest = '\\'.join(parts[2:])
            return f"{drive}:\\{rest}" if rest else f"{drive}:\\"

    return path.replace('/', '\\')


def windows_to_linux_path(path: str) -> str:
    """
    Converts a Windows or SMB path to a Linux path.
    :param path: Path in Windows or SMB format
    :type path: str
    :return: Path in Linux format
    :rtype: str
    """
    path = path.strip()

    if path.startswith('\\\\'):
        parts = path.lstrip('\\').split('\\')
        if len(parts) >= 2:
            server = parts[0]
            share = parts[1]
            subpath = '/'.join(parts[2:])
            return f"smb://{server}/{share}/{subpath}"
        else:
            return "smb://" + path.lstrip('\\').replace('\\', '/')

    if ':' in path[0:3]:
        p = PureWindowsPath(path)
        drive = p.drive.lower().replace(':', '')
        return f"/mnt/{drive}/{'/'.join(p.parts[1:])}"

    if path.startswith('\\'):
        path = path.lstrip('\\')
        converted = path.replace('\\', '/')
        return f"/mnt/{os.getcwd()[0].lower()}/{converted}"

    return path.replace('\\', '/')


def is_linux_path(path: str) -> bool:
    """
    Checks if the given path is a Linux path.
    :param path: Path to check
    :type path: str
    :return: Whether the path is a Linux path
    :rtype: bool
    """
    if path.startswith("/"):
        return True
    if path.startswith("smb://"):
        return True
    if re.match(r"^/mnt/[a-zA-Z]", path):
        return True
    return False
