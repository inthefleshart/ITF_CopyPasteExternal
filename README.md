# ITF_CopyPasteExternal

Easily copy and paste geometry and common attributes across 3D applications — perfect for quick iterations without any file management overhead.

---

## Why?

Because nothing this easy exists. If you work across multiple DCC applications, this is extremely beneficial. The tool uses a simple ASCII file in your system temp directory as a shared clipboard. That directory can also be pointed at a network share or Dropbox folder for inter-machine or collaborative use.

This is not about asset management. It's a "fire and forget" approach to quickly moving a mesh between apps — think of it like GoZ or 3D-Coat's AppLink, but cross-application.

---

## Supported Applications

| Application | Versions | Features |
|---|---|---|
| **Maya** | 2020+ | Vertices / Polygons / Skin Weights / UV Maps (multi-set, UDIM) |
| **Blender** | 5.0+ | Vertices / Polygons / Weight Maps / UV Maps / Morph Maps |
| **3ds Max** | 2020+ | Vertices / Polygons / UV Maps / Material Names |
| **ZBrush** | 2020+ | Vertices / Polygons / UV Maps |
| **Houdini** | 19+ | Vertices / Polygons / UV Maps / Vertex Normals / Vertex Colors |
| **Cinema 4D** | R17+ | Vertices / Polygons / UVs |
| **Substance Painter** | — | Paste only — Vertices / Polygons / UVs |
| **3D-Coat** | — | Vertices / Polygons / UVs |

---

## How It Works

- **Copy To External** — writes the current mesh into `ODVertexData.txt` in your system temp folder
- **Paste From External** — reads `ODVertexData.txt` and rebuilds the geometry in the target application

The file format is a simple ASCII format documented in [`docs/datafile_spec.md`](docs/datafile_spec.md). You can open and read the clipboard file in any text editor.

---

## Installation

### Maya (2020+)

Run `maya_ExportToExternal.py` and `maya_PasteFromExternal.py` from the Script Editor (Python tab), or add them to a shelf button.

**Supports:** Multiple UV sets, UDIM tiles, skin weights via skinCluster.

---

### Blender (5.0+)

1. In Blender: `Edit > Preferences > Add-ons > Install from File`
2. Select `BLENDER_ExportToExternal.py` — check the box to enable it
3. Repeat for `BLENDER_PasteFromExternal.py`
4. Both operators are found under the **Object** menu in the 3D Viewport

Scripts are located in: `Blender/Blender5/`

---

### Houdini (19+)

Scripts are located in: `Houdini/Houdini19/`

1. Right-click an empty area of the shelf → **New Tool...**
2. In the **Options** tab, set a Label (e.g. `Copy (to External)`)
3. In the **Script** tab, paste the entire contents of `Houdini_CopyToExternal.py`
4. Ensure **Script Language** is set to **Python** → click **Apply** and **Accept**
5. Repeat for `Houdini_PasteFromExternal.py`

The paste tool creates a Python SOP node with a **Reload Geometry** button for re-importing without re-running the shelf tool.

---

### 3ds Max (2020+)

Scripts are located in: `3DsMax/`

1. Edit the path in `3DSMax_LaunchCopyToExternal.ms` to point to the full path of `3DSMax_CopyToExternal.py` on your machine
2. Do the same for `3DSMax_LaunchPasteFromExternal.ms`
3. Run either `.ms` file from the **MaxScript Editor**

Alternatively, run directly from MaxScript:
```maxscript
python.ExecuteFile @"C:\path\to\3DSMax_CopyToExternal.py"
```

---

### ZBrush (2020+)

Scripts are located in: `ZBrush/`

1. Copy the entire **ODCopyPaste** folder into `ZStartup/ZPlugs64/`:
   ```
   ZStartup/
   └── ZPlugs64/
       └── ODCopyPaste/
           ├── ZFileUtils64.dll    (Windows)
           ├── ZFileUtils.lib      (macOS)
           ├── objToVertData.exe   (Windows) / objToVertData (macOS)
           ├── vertDataToObj.exe   (Windows) / vertDataToObj (macOS)
           └── source/             (source files — not required at runtime)
   ```
2. Copy `ZBRUSH_ODCopyPasteExternal.zsc` into `ZStartup/ZPlugs64/`
3. Restart ZBrush — buttons appear under **ZPlugin > ITF CopyPaste**

> **Recompiling the ZScript (optional):** If you modify `source/ZBRUSH_ODCopyPasteExternal.txt`, load it in ZBrush via `ZPlugin > Zscript > Load` to recompile the `.zsc`.

> **Rebuilding the helper executables:** If you modify the Python source files in `source/`, rebuild the executables using the included build script (Windows only):
> ```bat
> .venv\Scripts\activate
> build_zbrush_exes.bat
> ```
> macOS binaries must be compiled on a Mac using the same build script with PyInstaller.

---

### Cinema 4D (R17+)

Copy the scripts into the Cinema 4D scripts folder. They appear under the Python menu. See the script files in `C4D/` for details.

---

### Substance Painter

Paste-only (import). See `SubstancePainter/` for instructions.

---

### 3D-Coat

See `3DCoat/` for installation instructions.

---

## FAQ

**How do I report an issue?**  
Open a ticket on the [Issues tab on GitHub](https://github.com/inthefleshart/ITF_CopyPasteExternal/issues). Attach the `ODVertexData.txt` from your temp folder and note which applications you are transferring between.

**How do I change the clipboard file location?**  
Open any of the Python scripts in a text editor and change the `tempfile.gettempdir()` path to any local or network folder.

**Why not use OBJ / FBX / Alembic?**  
Simplicity. The ASCII format is human-readable, requires no external libraries, and works in every scripting language (Python, MaxScript, ZScript, JavaScript, Ruby). This tool is about a quick "fire and forget" mesh transfer, not full asset management.

**What coordinate system does the clipboard file use?**  
Y-up, with counter-clockwise front-facing polygon winding order. See [`docs/datafile_spec.md`](docs/datafile_spec.md) for the full specification.

---

## Dev Environment (for contributors)

A self-contained Python virtual environment is included for building the ZBrush helper executables.

**Setup:**
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

**Build ZBrush executables:**
```bat
.venv\Scripts\activate
build_zbrush_exes.bat
```

---

## TODO

- **Maya:** Morph/Blendshape export and import
- **Blender:** Vertex color export/import  
- **Houdini:** Morph/Blendshape export
- **Cinema 4D:** Native C++ implementation (currently Python only)
- **Unreal Engine:** R&D to determine feasibility
- **macOS ZBrush binaries:** Compile and ship macOS versions of the helper executables
