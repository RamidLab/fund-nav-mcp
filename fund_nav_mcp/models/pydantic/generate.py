import os
from pathlib import Path
from typing import Dict, Set, Tuple

_pyi_registry: Dict[Path, Set[Tuple[str, str]]] = {}


def register_pyi_class(class_name: str, base_class: type, pyi_file: str) -> None:
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    target_pyi = Path(os.path.join(curr_dir, pyi_file)).with_suffix('.pyi').resolve()
    base_qual = f"{base_class.__module__}.{base_class.__qualname__}"
    _pyi_registry.setdefault(target_pyi, set()).add((class_name, base_qual))
    _write_pyi(target_pyi)


def _write_pyi(pyi_path: Path) -> None:
    entries = _pyi_registry.get(pyi_path, set())
    if not entries:
        return

    imports: Dict[str, Set[str]] = {}
    for _, base_qual in entries:
        parts = base_qual.rsplit('.', 1)
        if len(parts) == 2:
            mod, cls = parts
            imports.setdefault(mod, set()).add(cls)

    lines = []
    if imports:
        for mod, classes in sorted(imports.items()):
            lines.append(f"from typing import Type")
            lines.append("")
            lines.append(f"from {mod} import {', '.join(sorted(classes))}")
    lines.append("")

    for cls_name, base_qual in sorted(entries, key=lambda x: x[0]):
        base_short = base_qual.rsplit('.', 1)[-1]
        lines.append(f"{cls_name}: Type[{base_short}]")
    lines.append("")

    pyi_path.write_text("\n".join(lines), encoding="utf-8")

def clean_registry() -> None:
    _pyi_registry.clear()
