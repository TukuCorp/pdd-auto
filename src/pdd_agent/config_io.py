"""Strict YAML loading for project inputs.

PyYAML's ``safe_load`` silently keeps the last of duplicate mapping keys,
which once hid a ``biomethanization_suitable_fraction`` override behind a
documented assumption. Every ``ProjectInput`` load must go through
``load_project_input`` so duplicates fail loudly instead.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError

from schemas.project_input import ProjectInput


class UniqueKeyLoader(yaml.SafeLoader):
    """A SafeLoader whose mapping constructor rejects duplicate keys."""


def _mapping_no_duplicates(
    loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        try:
            duplicate = key in mapping
        except TypeError:
            duplicate = False  # unhashable key: cannot be a duplicate
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f'found duplicate key "{key}"',
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _mapping_no_duplicates,
)


def load_yaml_unique(path: Path | str) -> Any:
    """Parse a YAML file, raising ``ConstructorError`` on duplicate keys."""
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=UniqueKeyLoader)


def load_project_input(path: Path | str) -> ProjectInput:
    """Load and validate a ``ProjectInput`` from a duplicate-free YAML file."""
    return ProjectInput.model_validate(load_yaml_unique(path))
