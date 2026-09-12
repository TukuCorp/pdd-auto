"""Tests for the duplicate-key-rejecting YAML loader (PHASE-04)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pdd_agent.config_io import UniqueKeyLoader, load_project_input, load_yaml_unique


def test_top_level_duplicate_raises_with_key_and_line(tmp_path: Path):
    p = tmp_path / "d.yaml"
    p.write_text("a: 1\na: 2\n", encoding="utf-8")
    with pytest.raises(yaml.constructor.ConstructorError) as exc_info:
        load_yaml_unique(p)
    message = str(exc_info.value)
    assert '"a"' in message or "'a'" in message or " a" in message
    assert "line" in message.lower()


def test_nested_duplicate_raises(tmp_path: Path):
    p = tmp_path / "d.yaml"
    p.write_text("t:\n  x: 1\n  x: 2\n", encoding="utf-8")
    with pytest.raises(yaml.constructor.ConstructorError, match="x"):
        load_yaml_unique(p)


def test_unique_yaml_loads_normally(tmp_path: Path):
    p = tmp_path / "d.yaml"
    p.write_text("a: 1\nb:\n  x: 1\n  y: 2\n", encoding="utf-8")
    assert load_yaml_unique(p) == {"a": 1, "b": {"x": 1, "y": 2}}


def test_loader_is_safe_loader_subclass():
    assert issubclass(UniqueKeyLoader, yaml.SafeLoader)


def test_load_project_input_inegol():
    root = Path(__file__).parent.parent
    pi = load_project_input(root / "configs/demo/inegol_project_input.yaml")
    assert pi.technology.biomethanization_suitable_fraction == pytest.approx(0.4312)


def test_load_project_input_rejects_every_project_config_without_duplicates():
    """Every committed ProjectInput YAML must pass the strict loader.

    This catches any other latent duplicate key (RISK-04-02): a failure here
    is the intended outcome, fixed by keeping the sourced value.
    """
    root = Path(__file__).parent.parent
    candidates = sorted(root.glob("configs/**/*project*.yaml")) + sorted(
        root.glob("configs/projects/*.yaml")
    )
    assert candidates, "no project configs found"
    loaded = 0
    for path in candidates:
        if path.name.endswith(".assumptions.yaml"):
            continue
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if not isinstance(data, dict) or "technology" not in data:
            continue  # not a ProjectInput (schema/rules/other config)
        pi = load_project_input(path)
        assert pi.technology is not None
        loaded += 1
    assert loaded >= 3, f"only {loaded} ProjectInput configs exercised"
