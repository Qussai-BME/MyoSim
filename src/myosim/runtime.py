"""Resolve source assets during development and packaged assets after installation."""

from __future__ import annotations

from pathlib import Path


def resource_root() -> Path:
    """Return the root containing V1 configs, assets, and replay examples.

    A checkout keeps these directories at repository root. A built wheel carries
    a synchronized immutable copy under ``myosim/resources``. The source tree is
    preferred whenever it exists so authoring paths remain transparent.
    """
    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "assets" / "models" / "hand.xml").is_file():
        return source_root
    packaged_root = Path(__file__).resolve().parent / "resources"
    if (packaged_root / "assets" / "models" / "hand.xml").is_file():
        return packaged_root
    raise RuntimeError("MyoSim V1 package assets are missing from this installation")
