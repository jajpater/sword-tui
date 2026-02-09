"""SWORD module detection via diatheke."""

import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ModuleInfo:
    """Information about a SWORD module."""

    name: str
    description: str
    module_type: str  # "Biblical Texts", "Commentaries", etc.


def get_installed_modules() -> List[ModuleInfo]:
    """Get list of installed SWORD modules using diatheke -b system -k modulelist.

    Returns:
        List of ModuleInfo for installed modules
    """
    if not shutil.which("diatheke"):
        return _fallback_modules()

    try:
        proc = subprocess.run(
            ["diatheke", "-b", "system", "-k", "modulelist"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return _fallback_modules()

        return _parse_module_list(proc.stdout)
    except (subprocess.TimeoutExpired, OSError):
        return _fallback_modules()


def _parse_module_list(output: str) -> List[ModuleInfo]:
    """Parse diatheke -M output.

    Format example:
    Biblical Texts:
      KJV : King James Version
      DutSVV : Dutch Staten Vertaling
    Commentaries:
      MHC : Matthew Henry Commentary
    """
    modules: List[ModuleInfo] = []
    current_type = "Unknown"

    for line in output.splitlines():
        line = line.rstrip()
        if not line:
            continue

        # Category header (no leading whitespace, ends with :)
        if not line.startswith(" ") and line.endswith(":"):
            current_type = line[:-1]
            continue

        # Module entry (contains " : " separator)
        if " : " in line:
            parts = line.strip().split(" : ", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                description = parts[1].strip()
                modules.append(ModuleInfo(
                    name=name,
                    description=description,
                    module_type=current_type,
                ))

    return modules


def get_bible_modules() -> List[ModuleInfo]:
    """Get only Bible text modules."""
    return [m for m in get_installed_modules() if m.module_type == "Biblical Texts"]


def find_module(name: str) -> Optional[ModuleInfo]:
    """Find a module by name (case-insensitive)."""
    name_lower = name.lower()
    for module in get_installed_modules():
        if module.name.lower() == name_lower:
            return module
    return None


def _fallback_modules() -> List[ModuleInfo]:
    """Return fallback module list when diatheke unavailable."""
    return [
        ModuleInfo("DutSVV", "Dutch Staten Vertaling", "Biblical Texts"),
        ModuleInfo("KJV", "King James Version", "Biblical Texts"),
    ]
