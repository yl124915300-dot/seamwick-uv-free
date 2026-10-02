# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 yulei
"""Read existing UV islands and plan density changes without changing meshes."""

import itertools
import math

from .math_utils import area_match_scale, polygon_area_2d, polygon_area_3d

EPSILON = 1e-12


def uv_coordinates(layer, loop_count):
    """Use Blender's modern UV attribute or the older loop data view."""
    attribute = getattr(layer, 'uv', None)
    if attribute is not None:
        return [tuple(attribute[index].vector) for index in range(loop_count)]
    return [tuple(layer.data[index].uv) for index in range(loop_count)]


def set_uv_coordinates(layer, coordinates):
    """Write through an attribute collection that makes shared data mutable.

    Blender 4.5's MeshUVLoopLayer.uv accessors do not detach shared CustomData
    before returning writable values. Direct writes through that view can also
    change UV buffers retained by memfile Undo. The generic attribute data
    iterator performs the required copy-on-write before foreach_set writes.
    """
    mesh = layer.id_data
    if len(coordinates) != len(mesh.loops):
        raise ValueError('UV coordinate count does not match mesh face corners')
    flat = [value for coordinate in coordinates for value in coordinate]
    attribute = mesh.attributes.get(layer.name)
    if (attribute is not None and attribute.data_type == 'FLOAT2'
            and attribute.domain == 'CORNER'):
        attribute.data.foreach_set('vector', flat)
    else:
        # The older collection also ensures mutable CustomData on iteration.
        layer.data.foreach_set('uv', flat)


def analyze_object(obj):
    """Measure tessellated original mesh triangles in UV and world space.

    Island connectivity follows UV continuity, rather than seam flags. The
    user's existing seams, UV maps, and corner selection are never changed.
    """
    mesh = obj.data
    layer = mesh.uv_layers.active
    if layer is None:
        raise ValueError(f'{obj.name}: no active UV map; unwrap the mesh first')
    if not mesh.polygons:
        raise ValueError(f'{obj.name}: mesh has no faces')
    coords = uv_coordinates(layer, len(mesh.loops))
    if any(not all(math.isfinite(value) for value in uv) for uv in coords):
        raise ValueError(f'{obj.name}: non-finite UV coordinates')
    world = [tuple(obj.matrix_world @ vertex.co) for vertex in mesh.vertices]
    if any(not all(math.isfinite(value) for value in co) for co in world):
        raise ValueError(f'{obj.name}: non-finite world coordinates')

    parent = list(range(len(mesh.polygons)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    edge_faces = {}
    for face in mesh.polygons:
        loops = list(face.loop_indices)
        for offset, first in enumerate(loops):
            second = loops[(offset + 1) % len(loops)]
            edge = mesh.loops[first].edge_index
            endpoints = {
                mesh.loops[first].vertex_index: coords[first],
                mesh.loops[second].vertex_index: coords[second],
            }
            edge_faces.setdefault(edge, []).append((face.index, endpoints))
    for records in edge_faces.values():
        for (face_a, uv_a), (face_b, uv_b) in itertools.combinations(records, 2):
            if uv_a.keys() == uv_b.keys() and all(
                abs(uv[axis] - uv_b[vertex][axis]) <= 1e-6
                for vertex, uv in uv_a.items() for axis in (0, 1)
            ):
                parent[find(face_a)] = find(face_b)

    islands = {}
    for face in mesh.polygons:
        island = islands.setdefault(find(face.index), {'loops': [], 'uv_area': 0.0, 'world_area': 0.0})
        island['loops'].extend(face.loop_indices)
    mesh.calc_loop_triangles()
    for triangle in mesh.loop_triangles:
        island = islands[find(triangle.polygon_index)]
        uv_area = polygon_area_2d([coords[index] for index in triangle.loops])
        world_area = polygon_area_3d([world[index] for index in triangle.vertices])
        if not (math.isfinite(uv_area) and math.isfinite(world_area)):
            raise ValueError(f'{obj.name}: non-finite triangle area')
        if uv_area <= EPSILON or world_area <= EPSILON:
            raise ValueError(f'{obj.name}: zero-area or degenerate UV/surface triangle')
        island['uv_area'] += uv_area
        island['world_area'] += world_area
    groups = list(islands.values())
    uv_area = sum(item['uv_area'] for item in groups)
    world_area = sum(item['world_area'] for item in groups)
    area_match_scale(world_area, uv_area)
    return {
        'object': obj,
        'layer': layer,
        'coordinates': coords,
        'islands': groups,
        'uv_area': uv_area,
        'world_area': world_area,
        'relative_density': math.sqrt(uv_area / world_area),
        'outside_tile': sum(any(value < 0.0 or value > 1.0 for value in uv) for uv in coords),
    }


def normalization_plan(record, target_density):
    """Scale each whole island around its current corner-coordinate center."""
    old = record['coordinates']
    result = list(old)
    for island in record['islands']:
        loops = island['loops']
        scale = area_match_scale(island['world_area'], island['uv_area']) * target_density
        center = tuple(sum(old[index][axis] for index in loops) / len(loops) for axis in (0, 1))
        for index in loops:
            result[index] = tuple(center[axis] + (old[index][axis] - center[axis]) * scale for axis in (0, 1))
            if not all(math.isfinite(value) and abs(value) <= 1e30 for value in result[index]):
                raise ValueError(f"{record['object'].name}: normalized UV values exceed a safe range")
    return result
