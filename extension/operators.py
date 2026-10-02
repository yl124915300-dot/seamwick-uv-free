# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 yulei
"""Local, reversible operators for the standalone Free UV workflow."""

import json
import math

import bpy

from .uv_utils import analyze_object, normalization_plan, set_uv_coordinates


def selected_meshes(context):
    if context.mode not in {'OBJECT', 'EDIT_MESH'}:
        raise ValueError('Use Object Mode or Mesh Edit Mode')
    targets = [obj for obj in context.selected_objects if obj.type == 'MESH']
    if not targets:
        raise ValueError('Select at least one mesh object')
    return targets


def require_writable(targets):
    for obj in targets:
        if (obj.library is not None or obj.override_library is not None
                or obj.data.library is not None or obj.data.override_library is not None
                or obj.data.users != 1):
            raise ValueError(f'{obj.name}: mesh and object must be local, non-override and single-user')


class ObjectMode:
    """Flush pending edits and restore the user's mode without changing selection."""
    def __init__(self, context):
        self.context = context
        self.was_edit = context.mode == 'EDIT_MESH'

    def __enter__(self):
        if self.was_edit and 'FINISHED' not in bpy.ops.object.mode_set(mode='OBJECT'):
            raise RuntimeError('Could not leave Edit Mode')
        return self

    def __exit__(self, kind, value, traceback):
        if self.was_edit and 'FINISHED' not in bpy.ops.object.mode_set(mode='EDIT'):
            raise RuntimeError('Could not restore Edit Mode')


def _material_snapshot(obj):
    return {
        'slots': [(slot.link, slot.material, obj.data.materials[index])
                  for index, slot in enumerate(obj.material_slots)],
        'indices': [face.material_index for face in obj.data.polygons],
        'active': obj.active_material_index,
    }


def _restore_material_snapshot(obj, snapshot):
    obj.data.materials.clear()
    for link, material, data_material in snapshot['slots']:
        obj.data.materials.append(data_material)
    for slot, (link, material, _) in zip(obj.material_slots, snapshot['slots']):
        slot.link = link
        slot.material = material
    count = len(obj.material_slots)
    for index, face in enumerate(obj.data.polygons):
        previous = snapshot['indices'][index] if index < len(snapshot['indices']) else 0
        # Blender permits a saved face index outside the current slot count.
        # Preserve it verbatim instead of silently changing the user's data.
        face.material_index = previous
    obj.active_material_index = min(snapshot['active'], max(0, count - 1))
    obj.data.update()


def _read_backup(state):
    return {
        'slots': [(slot.link, slot.material, slot.data_material) for slot in state.slots],
        'indices': json.loads(state.polygon_indices),
        'active': state.active_material_index,
    }


def _store_backup(state, snapshot):
    state.slots.clear()
    for link, material, data_material in snapshot['slots']:
        slot = state.slots.add()
        slot.link = link
        slot.material = material
        slot.data_material = data_material
    state.polygon_indices = json.dumps(snapshot['indices'], separators=(',', ':'))
    state.active_material_index = snapshot['active']


def _clear_backup(state):
    state.enabled = False
    state.slots.clear()
    state.polygon_indices = ''
    state.active_material_index = 0
    state.checker_material = None


def _new_checker(obj, uv_name, scale):
    material = bpy.data.materials.new(name=f'Seamwick Free Checker - {obj.name}')
    material.use_nodes = True
    material.diffuse_color = (0.15, 0.15, 0.15, 1.0)
    material['seamwick_uv_free_checker'] = True
    nodes = material.node_tree.nodes
    nodes.clear()
    uv_map = nodes.new('ShaderNodeUVMap')
    uv_map.uv_map = uv_name
    uv_map.location = (-500, 0)
    checker = nodes.new('ShaderNodeTexChecker')
    checker.inputs['Color1'].default_value = (0.025, 0.025, 0.025, 1.0)
    checker.inputs['Color2'].default_value = (0.8, 0.8, 0.8, 1.0)
    checker.inputs['Scale'].default_value = scale
    checker.location = (-260, 0)
    surface = nodes.new('ShaderNodeBsdfPrincipled')
    surface.inputs['Roughness'].default_value = 0.8
    surface.location = (0, 0)
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (280, 0)
    links = material.node_tree.links
    links.new(uv_map.outputs['UV'], checker.inputs['Vector'])
    links.new(checker.outputs['Color'], surface.inputs['Base Color'])
    links.new(surface.outputs['BSDF'], output.inputs['Surface'])
    return material


def _remove_unused_checker(material):
    """Dispose of this operation's superseded generated material safely."""
    try:
        if (material is not None and material.users == 0
                and material.get('seamwick_uv_free_checker', False)):
            bpy.data.materials.remove(material)
    except ReferenceError:
        # Object copies can share a saved checker pointer. A previous cleanup
        # in this operation may already have removed this now-unreferenced ID.
        pass


class SWFREE_OT_normalize_density(bpy.types.Operator):
    bl_idname = 'seamwick_free.normalize_density'
    bl_label = 'Normalize Relative Density'
    bl_description = 'Match existing UV islands to one world-area density; preserve centers without packing'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            targets = selected_meshes(context)
            require_writable(targets)
            with ObjectMode(context):
                records = [analyze_object(obj) for obj in targets]
                settings = context.scene.seamwick_free_settings
                if settings.reference == 'ACTIVE':
                    active = context.view_layer.objects.active
                    reference = next((record for record in records if record['object'] == active), None)
                    if reference is None:
                        raise ValueError('Active object must be one of the selected mesh objects')
                    density = reference['relative_density']
                else:
                    density = math.sqrt(sum(record['uv_area'] for record in records) / sum(record['world_area'] for record in records))
                plans = [normalization_plan(record, density) for record in records]
                try:
                    for record, plan in zip(records, plans):
                        set_uv_coordinates(record['layer'], plan)
                        record['object'].data.update()
                except Exception:
                    for record in records:
                        set_uv_coordinates(record['layer'], record['coordinates'])
                        record['object'].data.update()
                    raise
                count = sum(len(record['islands']) for record in records)
            self.report({'INFO'}, f'Normalized {count} UV island(s) on {len(targets)} mesh(es); inspect overlaps and tile bounds')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class SWFREE_OT_inspect_uv(bpy.types.Operator):
    bl_idname = 'seamwick_free.inspect_uv'
    bl_label = 'Inspect UV Density'
    bl_description = 'Report existing UV islands, world-area density and corners outside the 0-1 tile'
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            targets = selected_meshes(context)
            lines = []
            with ObjectMode(context):
                for obj in targets:
                    try:
                        record = analyze_object(obj)
                    except ValueError as exc:
                        lines.append(str(exc))
                    else:
                        lines.append(f"{obj.name}: {len(record['islands'])} island(s), relative density {record['relative_density']:.4g}")
                        lines.append(f"  Outside 0-1: {record['outside_tile']} UV corner(s)")
            context.scene.seamwick_free_settings.last_report = '\n'.join(lines)
            self.report({'INFO'}, '; '.join(lines)[:1000])
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class SWFREE_OT_apply_checker(bpy.types.Operator):
    bl_idname = 'seamwick_free.apply_checker'
    bl_label = 'Apply UV Checker'
    bl_description = 'Preview active UV maps using a procedural checker; store original material assignments'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        created = []
        snapshots = []
        try:
            targets = selected_meshes(context)
            require_writable(targets)
            with ObjectMode(context):
                records = [analyze_object(obj) for obj in targets]
                scale = context.scene.seamwick_free_settings.checker_scale
                for record in records:
                    obj = record['object']
                    state = obj.seamwick_free_checker_state
                    if state.enabled:
                        _read_backup(state)  # Refuse corrupted backups before any changes.
                    snapshots.append((obj, _material_snapshot(obj), state.enabled,
                                      _read_backup(state) if state.enabled else None,
                                      state.checker_material))
                    created.append(_new_checker(obj, record['layer'].name, scale))
                try:
                    for (obj, snapshot, was_enabled, _, _), material in zip(snapshots, created):
                        state = obj.seamwick_free_checker_state
                        if not was_enabled:
                            _store_backup(state, snapshot)
                        obj.data.materials.clear()
                        obj.data.materials.append(material)
                        obj.material_slots[0].link = 'DATA'
                        obj.material_slots[0].material = material
                        for face in obj.data.polygons:
                            face.material_index = 0
                        obj.active_material_index = 0
                        state.checker_material = material
                        state.enabled = True
                        obj.data.update()
                except Exception:
                    for obj, snapshot, was_enabled, backup, old_checker in snapshots:
                        _restore_material_snapshot(obj, snapshot)
                        state = obj.seamwick_free_checker_state
                        if was_enabled:
                            _store_backup(state, backup)
                            state.checker_material = old_checker
                            state.enabled = True
                        else:
                            _clear_backup(state)
                    raise
            for _, _, _, _, old_checker in snapshots:
                _remove_unused_checker(old_checker)
            self.report({'INFO'}, f'Checker applied to {len(targets)} mesh(es); use Material Preview')
            return {'FINISHED'}
        except Exception as exc:
            for material in created:
                if material.users == 0:
                    bpy.data.materials.remove(material)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class SWFREE_OT_remove_checker(bpy.types.Operator):
    bl_idname = 'seamwick_free.remove_checker'
    bl_label = 'Restore Original Materials'
    bl_description = 'Remove the checker and restore saved material slots and face assignments'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            targets = [obj for obj in selected_meshes(context) if obj.seamwick_free_checker_state.enabled]
            if not targets:
                raise ValueError('No selected mesh has a Seamwick Free checker backup')
            require_writable(targets)
            changed_topology = False
            with ObjectMode(context):
                backups = [(obj, _read_backup(obj.seamwick_free_checker_state)) for obj in targets]
                current = [(obj, _material_snapshot(obj)) for obj in targets]
                try:
                    for obj, backup in backups:
                        changed_topology |= len(backup['indices']) != len(obj.data.polygons)
                        _restore_material_snapshot(obj, backup)
                except Exception:
                    for obj, snapshot in current:
                        _restore_material_snapshot(obj, snapshot)
                    raise
                old_checkers = [obj.seamwick_free_checker_state.checker_material for obj in targets]
                for obj in targets:
                    _clear_backup(obj.seamwick_free_checker_state)
            for material in old_checkers:
                _remove_unused_checker(material)
            message = f'Restored original materials on {len(targets)} mesh(es)'
            if changed_topology:
                message += '; topology changed: inspect face material assignments'
            self.report({'WARNING'} if changed_topology else {'INFO'}, message)
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
