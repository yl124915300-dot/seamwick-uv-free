# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 yulei
"""Independent tests of the installed Extension, not a source-path import."""
import bpy
import importlib
import json
import math
import os
import traceback
from pathlib import Path

addon = importlib.import_module('bl_ext.seamwick_free_qa.seamwick_uv_free')
OUT = Path(os.environ['SW_QA_OUT'])
OUT.mkdir(parents=True, exist_ok=True)
results = {'blender': bpy.app.version_string, 'installed_module': addon.__name__, 'installed_path': addon.__file__, 'checks': []}


def check(name, function):
    try:
        detail = function()
        results['checks'].append({'name': name, 'status': 'PASS', 'detail': detail})
    except Exception as exc:
        results['checks'].append({'name': name, 'status': 'FAIL', 'error': str(exc), 'traceback': traceback.format_exc()})
    (OUT / 'headless-results.json').write_text(json.dumps(results, indent=2))


def uv_values(obj):
    layer = obj.data.uv_layers.active
    if layer is None:
        return None
    attr = getattr(layer, 'uv', None)
    return [tuple(attr[i].vector if attr is not None else layer.data[i].uv) for i in range(len(obj.data.loops))]


def put_uv(obj, values):
    layer = obj.data.uv_layers.active
    attr = getattr(layer, 'uv', None)
    for i, xy in enumerate(values):
        if attr is not None:
            attr[i].vector = xy
        else:
            layer.data[i].uv = xy


def density(obj):
    """Measure independently with Blender loop triangles, including world scale."""
    obj.data.calc_loop_triangles()
    xy = uv_values(obj)
    uv_area = world_area = 0.0
    for tri in obj.data.loop_triangles:
        u, v, w = [xy[i] for i in tri.loops]
        uv_area += abs((v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0])) / 2
        a, b, c = [obj.matrix_world @ obj.data.vertices[i].co for i in tri.vertices]
        world_area += (b-a).cross(c-a).length / 2
    return math.sqrt(uv_area/world_area), uv_area, world_area


def selected(*objects, active=None):
    bpy.context.view_layer.update()
    for obj in bpy.context.view_layer.objects:
        if obj is not None:obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active or objects[0]
    bpy.context.view_layer.update()


def clear():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def plane(name, uv_scale=1.0, scale=(1,1,1), offset=(0,0)):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)], [], [(0,1,2,3)])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.scale = scale
    mesh.uv_layers.new(name='Artist UV')
    values = [(offset[0]+uv_scale*x,offset[1]+uv_scale*y) for x,y in [(0,0),(1,0),(1,1),(0,1)]]
    put_uv(obj,values)
    bpy.context.view_layer.update()
    return obj


def structure(obj):
    return {'vertices':[tuple(v.co) for v in obj.data.vertices], 'faces':[tuple(p.vertices) for p in obj.data.polygons],
            'seams':[e.use_seam for e in obj.data.edges], 'materials':[m.name if m else None for m in obj.data.materials],
            'indices':[p.material_index for p in obj.data.polygons], 'uvs':[l.name for l in obj.data.uv_layers],
            'matrix':[list(r) for r in obj.matrix_world], 'slot_links':[s.link for s in obj.material_slots],
            'effective_materials':[s.material.name if s.material else None for s in obj.material_slots]}


def rejected(call):
    try:
        result=call()
    except RuntimeError as exc:
        return str(exc)
    assert result=={'CANCELLED'}, result
    return sorted(result)


def install_enabled():
    assert addon.__name__ in bpy.context.preferences.addons
    assert hasattr(bpy.types,'SEAMWICK_FREE_PT_main') or hasattr(bpy.context.scene,'seamwick_free_settings')
    return {'registered_after_fresh_process':True}


def normalize_active():
    clear()
    a=plane('Reference',.75,scale=(2,.5,1),offset=(.3,-.6))
    b=plane('Mismatch',.2,scale=(1,3,1),offset=(2,1))
    c=plane('Negative Scale',.9,scale=(-2,2,1),offset=(-1,3))
    selected(a,b,c,active=a)
    before={o.name:uv_values(o) for o in (a,b,c)}
    invariant={o.name:structure(o) for o in (a,b,c)}
    d0=density(a)[0]
    bpy.context.scene.seamwick_free_settings.reference='ACTIVE'
    assert bpy.ops.seamwick_free.normalize_density()=={'FINISHED'}
    assert uv_values(a)==before[a.name], 'Active reference changed'
    for o in (a,b,c):
        assert math.isclose(density(o)[0],d0,rel_tol=1e-6)
        assert structure(o)==invariant[o.name], 'Mesh/seams/materials/UV names/transform changed'
        center0=[sum(x[i] for x in before[o.name])/len(before[o.name]) for i in (0,1)]
        now=uv_values(o)
        center1=[sum(x[i] for x in now)/len(now) for i in (0,1)]
        assert all(abs(x-y)<1e-6 for x,y in zip(center0,center1))
    return {'reference_density':d0,'after':[density(o)[0] for o in (a,b,c)],'active_uv_preserved':True,'centers_preserved':True,'geometry_seams_materials_preserved':True}


def normalize_selection():
    clear()
    a=plane('Selection A',.9,scale=(1,2,1));b=plane('Selection B',.1,scale=(2,2,1))
    selected(a,b)
    measured=[density(o) for o in (a,b)]
    expected=math.sqrt(sum(x[1] for x in measured)/sum(x[2] for x in measured))
    bpy.context.scene.seamwick_free_settings.reference='SELECTION'
    assert bpy.ops.seamwick_free.normalize_density()=={'FINISHED'}
    assert all(math.isclose(density(o)[0],expected,rel_tol=1e-6) for o in (a,b))
    return {'expected_pooled_density':expected,'after':[density(o)[0] for o in (a,b)]}


def missing_uv_atomic():
    clear();a=plane('Valid');b=plane('No UV')
    b.data.uv_layers.remove(b.data.uv_layers.active)
    selected(a,b)
    before=uv_values(a)
    rejection=rejected(bpy.ops.seamwick_free.normalize_density)
    assert uv_values(a)==before
    return {'rejection':rejection,'valid_uv_unchanged':True}


def zero_uv_atomic():
    clear();a=plane('Valid');b=plane('Collapsed UV',0)
    selected(a,b);before=uv_values(a)
    rejection=rejected(bpy.ops.seamwick_free.normalize_density)
    assert uv_values(a)==before
    return {'rejection':rejection,'valid_uv_unchanged':True}


def shared_mesh_atomic():
    clear();a=plane('Shared A');b=bpy.data.objects.new('Shared B',a.data);bpy.context.collection.objects.link(b)
    selected(a,b);before=uv_values(a)
    rejection=rejected(bpy.ops.seamwick_free.normalize_density)
    assert uv_values(a)==before
    return {'rejection':rejection,'shared_uv_unchanged':True}


def inspect_read_only():
    clear();a=plane('Report valid');b=plane('Report collapsed',0)
    selected(a,b)
    before={o.name:(structure(o),uv_values(o)) for o in (a,b)}
    assert bpy.ops.seamwick_free.inspect_uv()=={'FINISHED'}
    report=bpy.context.scene.seamwick_free_settings.last_report
    assert report
    assert before=={o.name:(structure(o),uv_values(o)) for o in (a,b)}
    return {'report':report,'read_only':True}


def edit_mode():
    clear();a=plane('Edit reference',.8);b=plane('Edit target',.2)
    selected(a,b,active=a)
    bpy.context.scene.seamwick_free_settings.reference='ACTIVE'
    bpy.ops.object.mode_set(mode='EDIT')
    assert bpy.ops.seamwick_free.normalize_density()=={'FINISHED'}
    assert bpy.context.object.mode=='EDIT', 'Edit mode not restored'
    bpy.ops.object.mode_set(mode='OBJECT')
    assert math.isclose(density(a)[0],density(b)[0],rel_tol=1e-6)
    return {'multi_object_edit_mode_restored':True,'density_equalized':True}


def multi_island_and_inactive():
    clear()
    mesh=bpy.data.meshes.new('Two islands mesh')
    mesh.from_pydata([(-3,-1,0),(-1,-1,0),(-1,1,0),(-3,1,0),(1,-1,0),(3,-1,0),(3,1,0),(1,1,0)],[],[(0,1,2,3),(4,5,6,7)])
    obj=bpy.data.objects.new('Two independent UV islands',mesh);bpy.context.collection.objects.link(obj)
    active=mesh.uv_layers.new(name='Normalize me')
    coords=[(0,0),(1,0),(1,1),(0,1),(2,2),(2.25,2),(2.25,2.25),(2,2.25)]
    put_uv(obj,coords)
    other=mesh.uv_layers.new(name='Keep this UV')
    mesh.uv_layers.active=other;put_uv(obj,[(i*.07,i*.09) for i in range(8)])
    untouched=uv_values(obj);mesh.uv_layers.active=active
    for i,e in enumerate(mesh.edges):e.use_seam=(i%2==0)
    invariant=structure(obj);selected(obj)
    bpy.context.scene.seamwick_free_settings.reference='ACTIVE'
    expected=density(obj)[0]
    assert bpy.ops.seamwick_free.normalize_density()=={'FINISHED'}
    assert structure(obj)==invariant
    after=uv_values(obj)
    for start in (0,4):
        uv=after[start:start+4]
        area=sum(abs((uv[i][0]-uv[0][0])*(uv[i+1][1]-uv[0][1])-(uv[i][1]-uv[0][1])*(uv[i+1][0]-uv[0][0]))/2 for i in (1,2))
        assert math.isclose(math.sqrt(area/4),expected,rel_tol=1e-6)
        assert all(abs(sum(uv[i][j] for i in range(4))/4-sum(coords[start+i][j] for i in range(4))/4)<1e-6 for j in (0,1))
    mesh.uv_layers.active=other;assert uv_values(obj)==untouched;mesh.uv_layers.active=active
    return {'per_island_density_equalized':True,'per_island_centers_preserved':True,'inactive_uv_preserved':True,'seam_flags_preserved':True}


def object_link_empty_slots():
    clear();bpy.ops.mesh.primitive_cube_add();obj=bpy.context.object
    data_mat=bpy.data.materials.new('DATA original pointer');effective=bpy.data.materials.new('OBJECT original pointer')
    obj.data.materials.append(data_mat);obj.data.materials.append(None)
    obj.material_slots[0].link='OBJECT';obj.material_slots[0].material=effective
    for i,p in enumerate(obj.data.polygons):p.material_index=1 if i%2 else 0
    before=structure(obj);selected(obj)
    assert bpy.ops.seamwick_free.apply_checker()=={'FINISHED'}
    assert bpy.ops.seamwick_free.remove_checker()=={'FINISHED'}
    assert structure(obj)==before
    assert obj.data.materials[0]==data_mat and obj.material_slots[0].material==effective
    assert obj.data.materials[1] is None
    return {'data_and_effective_object_pointer_preserved':True,'slot_link_preserved':True,'empty_none_slot_preserved':True,'per_face_indices_preserved':True}


def invalid_numeric_and_world_area():
    clear();valid=plane('Valid numerical reference');bad=plane('Nonfinite UV')
    xy=uv_values(bad);xy[0]=(float('nan'),0);put_uv(bad,xy);selected(valid,bad,active=valid)
    before=uv_values(valid);first=rejected(bpy.ops.seamwick_free.normalize_density);assert uv_values(valid)==before
    clear();valid=plane('Valid world reference');bad=plane('Zero world area',scale=(0,1,1))
    selected(valid,bad,active=valid);before=uv_values(valid)
    second=rejected(bpy.ops.seamwick_free.normalize_density);assert uv_values(valid)==before
    return {'nonfinite_uv_rejected':first,'zero_world_area_rejected':second,'valid_objects_unchanged':True}


def repeat_checker_no_leak():
    clear();obj=plane('Repeat material allocation');selected(obj)
    tagged=lambda:len([m for m in bpy.data.materials if m.get('seamwick_uv_free_checker')])
    initial=tagged();assert bpy.ops.seamwick_free.apply_checker()=={'FINISHED'}
    first=tagged()
    for _ in range(5):assert bpy.ops.seamwick_free.apply_checker()=={'FINISHED'}
    assert tagged()==first
    assert bpy.ops.seamwick_free.remove_checker()=={'FINISHED'}
    assert tagged()==initial
    return {'five_repeat_applications_no_orphan_growth':True,'owned_unused_checker_released_on_restore':True}


def copied_checker_restore():
    clear();a=plane('Checker original');mat=bpy.data.materials.new('Copy original material');a.data.materials.append(mat);selected(a)
    assert bpy.ops.seamwick_free.apply_checker()=={'FINISHED'}
    b=a.copy();b.data=a.data.copy();b.name='Checker local single-user copy';bpy.context.collection.objects.link(b)
    assert b.seamwick_free_checker_state.enabled
    selected(a,b)
    assert bpy.ops.seamwick_free.remove_checker()=={'FINISHED'}
    assert list(a.data.materials)==[mat] and list(b.data.materials)==[mat]
    selected(a);assert bpy.ops.seamwick_free.apply_checker()=={'FINISHED'}
    c=a.copy();c.data=a.data.copy();c.name='Checker copy reapply';bpy.context.collection.objects.link(c);selected(a,c)
    assert bpy.ops.seamwick_free.apply_checker()=={'FINISHED'}
    assert bpy.ops.seamwick_free.remove_checker()=={'FINISHED'}
    assert list(a.data.materials)==[mat] and list(c.data.materials)==[mat]
    return {'copied_checker_shared_material_id_restore':True,'copied_checker_reapply_restore':True}


def checker_restore_and_idempotence():
    clear();bpy.ops.mesh.primitive_cube_add();a=bpy.context.object;a.name='Material preservation cube'
    a.data.uv_layers.active.name='Artist UV'
    m1=bpy.data.materials.new('Original Blue');m2=bpy.data.materials.new('Original Red')
    a.data.materials.append(m1);a.data.materials.append(m2)
    for i,p in enumerate(a.data.polygons):p.material_index=i%2
    b=plane('Original no materials',.5)
    selected(a,b)
    before={o.name:(structure(o),uv_values(o)) for o in (a,b)}
    assert bpy.ops.seamwick_free.apply_checker()=={'FINISHED'}
    assert any(m and m.use_nodes for o in (a,b) for m in o.data.materials)
    assert bpy.ops.seamwick_free.apply_checker()=={'FINISHED'}
    assert all(len(o.data.materials)==1 for o in (a,b)), 'Repeated apply accumulated material slots'
    for o in (a,b):assert uv_values(o)==before[o.name][1]
    assert bpy.ops.seamwick_free.remove_checker()=={'FINISHED'}
    assert before=={o.name:(structure(o),uv_values(o)) for o in (a,b)}
    return {'multiple_slots_restored':True,'face_material_indices_restored':True,'original_zero_slots_restored':True,'repeat_apply_original_backup_preserved':True,'repeat_apply_no_extra_slots':True,'uv_unchanged':True}


def prepare_persistence():
    clear();a=plane('Saved Reference',.8);b=plane('Saved Match',.2,scale=(3,1,1))
    m=bpy.data.materials.new('Persisted DATA original material');a.data.materials.append(m);a.data.materials.append(None)
    effective=bpy.data.materials.new('Persisted OBJECT effective material');a.material_slots[0].link='OBJECT';a.material_slots[0].material=effective
    selected(a,b,active=a)
    bpy.context.scene.seamwick_free_settings.reference='ACTIVE'
    assert bpy.ops.seamwick_free.normalize_density()=={'FINISHED'}
    expectation={o.name:{'uv':uv_values(o),'structure':structure(o)} for o in (a,b)}
    (OUT/'persist-expected.json').write_text(json.dumps(expectation,indent=2))
    assert bpy.ops.seamwick_free.apply_checker()=={'FINISHED'}
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'free-save.blend'),check_existing=False)
    return {'saved_path':str(OUT/'free-save.blend'),'checker_applied_before_save':True}


def register_cycle():
    addon.unregister()
    assert not hasattr(bpy.context.scene,'seamwick_free_settings')
    addon.register()
    assert hasattr(bpy.context.scene,'seamwick_free_settings')
    return {'unregister_reregister':True}


for name,fn in [('installed_and_enabled',install_enabled),('normalize_active_world_scale',normalize_active),('normalize_selection_pooled_area',normalize_selection),('multi_object_edit_mode',edit_mode),('multi_island_inactive_uv_seams',multi_island_and_inactive),('missing_uv_atomic_rejection',missing_uv_atomic),('zero_uv_atomic_rejection',zero_uv_atomic),('shared_mesh_atomic_rejection',shared_mesh_atomic),('nonfinite_zero_world_atomic_rejection',invalid_numeric_and_world_area),('inspect_read_only',inspect_read_only),('checker_restore_idempotent',checker_restore_and_idempotence),('object_link_and_empty_material_slot',object_link_empty_slots),('checker_repeat_no_orphan_growth',repeat_checker_no_leak),('checker_local_copies_restore',copied_checker_restore),('save_with_checker_and_normalized_uv',prepare_persistence),('unregister_reregister',register_cycle)]:check(name,fn)
results['status']='PASS' if all(c['status']=='PASS' for c in results['checks']) else 'FAIL'
(OUT/'headless-results.json').write_text(json.dumps(results,indent=2))
print('SEAMWICK_FREE_QA='+json.dumps(results))
assert results['status']=='PASS',results
