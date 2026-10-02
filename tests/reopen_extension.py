# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 yulei
import bpy
import json
import importlib
import os
from pathlib import Path
OUT=Path(os.environ['SW_QA_OUT'])
module='bl_ext.seamwick_free_qa.seamwick_uv_free'
assert module in bpy.context.preferences.addons
importlib.import_module(module)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'free-save.blend'))
assert hasattr(bpy.context.scene,'seamwick_free_settings')
expected=json.loads((OUT/'persist-expected.json').read_text())
assert bpy.ops.seamwick_free.remove_checker()=={'FINISHED'}
for name,x in expected.items():
    obj=bpy.data.objects[name];layer=obj.data.uv_layers.active;attr=getattr(layer,'uv',None)
    actual=[tuple(attr[i].vector if attr is not None else layer.data[i].uv) for i in range(len(obj.data.loops))]
    assert all(abs(a-b)<1e-7 for u,v in zip(actual,x['uv']) for a,b in zip(u,v)),(name,'UV persistence mismatch')
    assert [m.name if m else None for m in obj.data.materials]==x['structure']['materials'],(name,'Material mismatch')
    assert [p.material_index for p in obj.data.polygons]==x['structure']['indices'],(name,'Face index mismatch')
    assert [s.link for s in obj.material_slots]==x['structure']['slot_links'],(name,'DATA/OBJECT slot links mismatch')
    assert [s.material.name if s.material else None for s in obj.material_slots]==x['structure']['effective_materials'],(name,'Effective object-linked material mismatch')
result={'blender':bpy.app.version_string,'status':'PASS','checks':{'extension_enabled_after_process_restart':True,'saved_normalized_uv_preserved':True,'checker_removable_after_save_reopen':True,'original_materials_and_indices_restored':True}}
(OUT/'reopen-results.json').write_text(json.dumps(result,indent=2))
print('SEAMWICK_FREE_REOPEN='+json.dumps(result))
