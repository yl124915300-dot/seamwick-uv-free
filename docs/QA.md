# Seamwick UV Free 0.1.0 QA

Test date: 2026-10-02. Runtime platform: macOS Apple Silicon (`macos-arm64`).

## Verified versions

| Blender version | ZIP validation and install/enable | Independent functional checks | Separate-process save/reopen |
| --- | --- | --- | --- |
| 4.5.14 LTS | PASS | 16/16 PASS | PASS |
| 5.1.2 | PASS | 16/16 PASS | PASS |
| 5.2.2 LTS | PASS | 16/16 PASS | PASS |

Each run used a separate Blender user configuration and local extension repository. Tests imported the installed extension, rather than importing its source directory. Installed Python file hashes matched the tested release source.

The final release ZIP was validated, installed and enabled again on all three versions after a documentation-only package update. Its Python source hashes matched the source that passed the functional and reopening tests. Final ZIP SHA256:

```text
385fe75ff23c1db5fb93c3ab13dca167e74ecb0d3ce720e2c8ea25a88ef26876
```

## Functional coverage

The following 16 checks passed separately on each listed Blender version:

1. Extension installation, registration and enablement in a fresh process.
2. Active-object density reference across multiple objects, including nonuniform and negative world scale; preservation of island centers, geometry, seams, material assignments and transforms.
3. Selection-average reference using the pooled UV-area/world-area ratio.
4. Multi-object Edit Mode operation and return to Edit Mode.
5. Per-island density matching within one object, preservation of each island center, inactive UV coordinates and existing seam flags.
6. Missing-UV rejection without changing another valid selected object's UVs.
7. Zero-area UV rejection without changing another valid selected object's UVs.
8. Shared-mesh rejection without changing the shared UV data.
9. Non-finite UV and zero-world-area rejection without changing valid selected objects.
10. Inspection reports valid and invalid UV data without changing mesh, UV or material data.
11. Checker application, repeat application and exact original material-slot/face-index restoration, including objects with no initial material slots.
12. Preservation of separate DATA and OBJECT material pointers, slot links, empty material slots and face material indices.
13. Five repeated checker applications without generated orphan-material growth; cleanup of unused generated checker materials on restoration.
14. Restoration and reapplication after copying a checker-enabled object and making its mesh single-user.
15. Saving normalized UVs and an active checker with persistent original-material backups.
16. Unregistering and registering the extension again.

Fresh Blender processes then reopened the saved scenes. Each version confirmed extension enablement, preservation of normalized UV coordinates, successful checker removal and restoration of original material slots, face indices, DATA/OBJECT links and effective object-linked material assignments.

## Graphical checks

In graphical Blender 4.5.14 LTS, native UI interaction confirmed the panel, checker application, checker Undo/Redo and **Restore Original Materials**. The screenshot below shows the actual Free extension workflow in Blender.

![Seamwick UV Free running in Blender 4.5.14 LTS](screenshots/free-workflow-blender-4.5.14.jpg)

**0.1.0 density Undo failure:** a fresh graphical Blender 4.5.14 process opened a clean saved baseline, executed normalization, then Undo and Redo in separate event-loop callbacks. Undo retained the normalized UVs instead of restoring the baseline. Blender's built-in object translation passed Undo/Redo in the same harness, so this is a concrete extension defect rather than a successful Undo test. A corrective release is in progress. Do not use 0.1.0 density normalization on production meshes. Native keyboard verification of this operation remains pending because the Mac was locked. GUI coverage has not been established for Blender 5.1.2 or 5.2.2.

## Full-version preservation and coexistence

The existing Seamwick UV 0.2.0 source was not edited for this Free release. Its existing independent baseline suite passed 14/14 checks on each of Blender 4.5.14, 5.1.2 and 5.2.2.

A separate coexistence check on Blender 4.5.14 LTS passed with Free and full Seamwick UV enabled together: both panels registered, the full version's hard-surface UV operation still ran, the Free checker worked on that result, and Free remained registered after disabling the full version. This is a focused coexistence check, not an exhaustive test of every possible interaction.

## Unverified scope

Only the exact versions and runtime platform listed above were tested. Windows, Linux, Intel macOS and other Blender versions are unverified. The manifest's minimum version and lack of a maximum version do not imply that every later Blender release has been tested.

No performance benchmark, evaluated-modifier workflow, overlap detection, absolute pixels-per-unit accuracy, or claim of distortion-free UVs is established by these tests. UV normalization may produce overlaps or coordinates outside the 0–1 tile. The checker backup does not reconstruct original topology after geometry edits; inspect face material assignments if topology changes while the checker is active.

The independent installed-package test scripts and reproduction instructions are in [tests](../tests/README.md). No local account information or private machine paths are included in this public report.
