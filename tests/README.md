# Installed-extension tests

These scripts test the extension after installing its ZIP into an isolated local Blender extension repository. They do not import `extension/` directly. The tested runtime versions and actual results are documented in [QA](../docs/QA.md).

`installed_extension.py` generates small test scenes and runs 16 functional checks. It writes `headless-results.json`, `persist-expected.json` and `free-save.blend` to the directory supplied by `SW_QA_OUT`. `reopen_extension.py` runs in a second Blender process, reopens that saved scene and writes `reopen-results.json` after checking normalized UVs and restored material assignments.

The scripts require Blender's bundled Python and no external Python packages. They test normalization and persistence in background Blender; they do not establish native GUI Undo/Redo or screenshot results.

## Reproduce on macOS

Run from the repository root. Set `SW_BLENDER_BINARY` to the desired Blender executable if it is not available as `blender` on your command path. Use a separate `SW_TEST_ROOT` directory for each version. These commands are the macOS command-line test workflow; they are not evidence of Windows or Linux compatibility.

Build the ZIP from this source checkout, or download the release ZIP and place it at `dist/seamwick_uv_free-0.1.1.zip`:

```bash
python3 scripts/build_package.py
```

Prepare isolated configuration, repository and result directories:

```bash
SW_BLENDER_BINARY="${SW_BLENDER_BINARY:-blender}"
SW_TEST_ROOT="$PWD/work/qa-local"
export BLENDER_USER_RESOURCES="$SW_TEST_ROOT/resources"
export SW_QA_OUT="$SW_TEST_ROOT/results"
mkdir -p "$BLENDER_USER_RESOURCES" "$SW_TEST_ROOT/repository" "$SW_QA_OUT"
unset BLENDER_USER_CONFIG BLENDER_USER_SCRIPTS BLENDER_USER_EXTENSIONS BLENDER_USER_DATAFILES
```

Validate the ZIP, configure the isolated local repository and install/enable the extension:

```bash
"$SW_BLENDER_BINARY" --background --factory-startup --offline-mode \
  --command extension validate dist/seamwick_uv_free-0.1.1.zip

"$SW_BLENDER_BINARY" --background --factory-startup --offline-mode \
  --command extension repo-add seamwick_free_qa \
  --name "Seamwick Free isolated QA" \
  --directory "$SW_TEST_ROOT/repository" --clear-all

"$SW_BLENDER_BINARY" --background --offline-mode \
  --command extension install-file -r seamwick_free_qa --enable \
  dist/seamwick_uv_free-0.1.1.zip
```

Run the functional checks and then the separate-process reopening check:

```bash
"$SW_BLENDER_BINARY" --background --offline-mode --python-exit-code 1 \
  --python tests/installed_extension.py

"$SW_BLENDER_BINARY" --background --offline-mode --python-exit-code 1 \
  --python tests/reopen_extension.py
```

Both processes must exit successfully. Inspect `headless-results.json` for 16 `PASS` checks and overall `PASS`, then inspect `reopen-results.json` for overall `PASS`. A successful install alone does not establish functional or reopening success.

The repository name `seamwick_free_qa` is intentional: the test scripts import the installed module `bl_ext.seamwick_free_qa.seamwick_uv_free`. If you choose a different repository identifier, update that import in both test scripts. Keep tests in the isolated configuration: the functional suite removes objects from its generated scene and saves a test file.
