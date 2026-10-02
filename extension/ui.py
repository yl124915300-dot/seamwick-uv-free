# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 yulei
"""The Free workflow has no advertising, network access, or payment UI."""

import bpy
from bpy.props import (
    BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
    IntProperty, PointerProperty, StringProperty,
)


class SWFREE_PG_material_slot(bpy.types.PropertyGroup):
    material: PointerProperty(type=bpy.types.Material)
    data_material: PointerProperty(type=bpy.types.Material)
    link: EnumProperty(items=(('DATA', 'Data', ''), ('OBJECT', 'Object', '')))


class SWFREE_PG_checker_state(bpy.types.PropertyGroup):
    enabled: BoolProperty(default=False, options={'HIDDEN'})
    slots: CollectionProperty(type=SWFREE_PG_material_slot, options={'HIDDEN'})
    polygon_indices: StringProperty(default='', options={'HIDDEN'})
    active_material_index: IntProperty(default=0, options={'HIDDEN'})
    checker_material: PointerProperty(type=bpy.types.Material, options={'HIDDEN'})


class SWFREE_PG_settings(bpy.types.PropertyGroup):
    reference: EnumProperty(
        name='Density Reference',
        description='Relative UV-area to world-area ratio used for every island',
        items=(
            ('ACTIVE', 'Active Object', 'Keep the active mesh overall density as the reference'),
            ('SELECTION', 'Selection Average', 'Use the area-weighted density of all selected meshes'),
        ),
        default='ACTIVE',
    )
    checker_scale: FloatProperty(
        name='Checker Scale', description='Procedural checker frequency per UV unit',
        default=16.0, min=1.0, max=512.0,
    )
    last_report: StringProperty(name='Last Inspection', default='')


class SWFREE_PT_main(bpy.types.Panel):
    bl_label = 'Seamwick UV Free'
    bl_idname = 'SWFREE_PT_main'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Seamwick Free'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.seamwick_free_settings
        layout.label(text='Uses existing active UV maps')
        layout.prop(settings, 'reference')
        layout.operator('seamwick_free.normalize_density', icon='UV')
        layout.operator('seamwick_free.inspect_uv', icon='VIEWZOOM')
        layout.separator()
        layout.prop(settings, 'checker_scale')
        row = layout.row(align=True)
        row.operator('seamwick_free.apply_checker', text='Apply Checker')
        row.operator('seamwick_free.remove_checker', text='Restore Materials')
        layout.label(text='View checker in Material Preview')
        layout.label(text='Scaling does not unwrap or pack')
        if settings.last_report:
            box = layout.box()
            for line in settings.last_report.split('\n')[:8]:
                box.label(text=line)
