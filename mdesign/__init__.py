"""mdesign - design of machine elements (shaft, rigid flanged coupling, bolted joint)."""

from .bolted_joint import BoltInput, design_bolted_joint
from .coupling import CouplingInput, design_coupling
from .database import get_db
from .shaft import ShaftInput, ShaftLoad, design_shaft

__all__ = [
    "BoltInput", "CouplingInput", "ShaftInput", "ShaftLoad",
    "design_bolted_joint", "design_coupling", "design_shaft", "get_db",
]
