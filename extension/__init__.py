# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 yulei
"""A complete local workflow for relative UV density and checker preview."""

import bpy
from bpy.props import PointerProperty

from .operators import (
    SWFREE_OT_apply_checker,
    SWFREE_OT_inspect_uv,
    SWFREE_OT_normalize_density,
    SWFREE_OT_remove_checker,
)
from .ui import (
    SWFREE_PG_checker_state,
    SWFREE_PG_material_slot,
    SWFREE_PG_settings,
    SWFREE_PT_main,
)

CLASSES = (
    SWFREE_PG_material_slot,
    SWFREE_PG_checker_state,
    SWFREE_PG_settings,
    SWFREE_OT_inspect_uv,
    SWFREE_OT_normalize_density,
    SWFREE_OT_apply_checker,
    SWFREE_OT_remove_checker,
    SWFREE_PT_main,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.seamwick_free_settings = PointerProperty(type=SWFREE_PG_settings)
    bpy.types.Object.seamwick_free_checker_state = PointerProperty(type=SWFREE_PG_checker_state)


def unregister():
    del bpy.types.Object.seamwick_free_checker_state
    del bpy.types.Scene.seamwick_free_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
