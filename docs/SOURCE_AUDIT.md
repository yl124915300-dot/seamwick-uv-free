# Source audit

The paid Seamwick UV 0.2.0 source was read from the existing licensed Extensions-format package before extracting Free functionality. Its real operators are `uvmvp.run_auto_uv` and `uvmvp.preview_seams`. The auto operator implements hard-surface angle/sharp/material seam rules, an organic back-cut heuristic with projection fallback, Blender unwrap, world-area island scale matching and selected-object shared-atlas packing. Preview enters Edit Mode and selects seam edges. The paid source has no UV checker.

Free extracts the existing unsigned polygon area and area-to-scale mathematics, adds a standalone existing-UV workflow, and implements only the procedural checker required to visually inspect that workflow. Free calculates areas from Blender's loop triangles rather than treating a potentially non-planar whole polygon as a planar face. Its own namespace (`seamwick_free.*`, `Scene.seamwick_free_settings`, `Object.seamwick_free_checker_state`) avoids changing or conflicting with the paid registration.

Free normalizes actual UV-connected islands around their existing centers. It uses each object's `matrix_world` before measuring surface area, preflights the whole selection, rejects non-finite/degenerate triangles and single-user/library violations, and plans UV updates before committing them. It never calls Blender's unwrap or packing operators and never changes seam flags or geometry. The active UV map is edited in place; other maps are not touched.

Checker preview backs up effective and data material pointers, DATA/OBJECT slot links, face indices and active slot in persisted Blender PropertyGroups. Reapplying the checker retains the original backup. Restoration works after saved-file reopening when the extension is enabled. The checker uses an explicit UV Map shader node for the current active UV map. It uses no texture file, network request, data collection, or purchase UI.

Original paid files were not edited. Compatibility and QA claims must be finalized only from actual Free-package tests.
