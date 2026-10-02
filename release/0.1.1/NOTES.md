Fixes the Blender 4.5 LTS density-normalization Undo defect in 0.1.0. Use this release instead of 0.1.0. The corrected UV write path detaches shared data before modifying it.

Seamwick UV Free is a standalone, GPL-3.0-or-later utility for meshes with existing UV maps.

- Match relative UV island density across selected objects using world-space mesh area.
- Preview active UV maps with a procedural checker and restore original materials, including after save/reopen.
- Inspect density, island counts and UV corners outside the 0–1 tile.

Download **seamwick_uv_free-0.1.1.zip**, keep it zipped, then use Blender **Preferences > Get Extensions > Install from Disk**. The complete source and usage instructions are in this repository.

Verified on **macOS Apple Silicon**, in **Blender 4.5.14 LTS, 5.1.2 and 5.2.2 LTS**: ZIP validation/install/enable, 16 functional checks per version and fresh-process save/reopen. The extension is packaged only for `macos-arm64`. Other versions and platforms are unverified. See [QA](https://github.com/yl124915300-dot/seamwick-uv-free/blob/main/docs/QA.md) for detailed coverage and the current native GUI checks.

This workflow does not unwrap, mark seams or pack UV islands. Relative normalization can create overlaps or move UVs outside the tile; inspect the result. Modifier output is not included in the area calculation. Restore the checker before disabling the extension.

The attached checksum identifies the exact locally tested ZIP; the publication workflow verifies it before uploading.

Graphical Blender 4.5.14 Undo/Redo restored baseline and normalized UVs exactly in the controlled regression test. This is graphical API verification; native keyboard testing of the patch was unavailable.
