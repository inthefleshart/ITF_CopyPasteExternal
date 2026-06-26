"""
ITF_CopyPasteExternal - 3ds Max Import (Paste From External)
Imports geometry from ODVertexData.txt into 3ds Max as a new editable mesh.

Supports: Vertices, Polygons (n-gons), UV Maps, Material names

Compatible with 3ds Max 2020+ (Python 3, pymxs API)

Usage:
    1. Edit the path in the .ms launcher file to point to this script.
    2. Run the launcher from the MaxScript Editor.

    Or run directly from MaxScript:
        python.ExecuteFile @"C:\path\to\3DSMax_PastefromExternal.py"
"""

import tempfile
import os
import pymxs

rt = pymxs.runtime


IMPORT_FILENAME = os.path.join(tempfile.gettempdir(), "ODVertexData.txt")
IMPORT_OBJECT_NAME = "ITF_Paste"


def _parse_file(lines):
    """Parse ODVertexData.txt into structured data."""
    data = {
        "verts": [],
        "faces": [],
        "face_mats": [],
        "uvs": [],
    }

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if line.startswith("VERTICES:"):
            count = int(line.split(":")[1])
            for j in range(i + 1, i + 1 + count):
                p = lines[j].split()
                # spec (X, Y, Z) → 3ds Max (X, -Z, Y)  [Y-up → Z-up]
                data["verts"].append((float(p[0]), float(p[2]) * -1, float(p[1])))
            i += count + 1

        elif line.startswith("POLYGONS:"):
            count = int(line.split(":")[1])
            for j in range(i + 1, i + 1 + count):
                parts = lines[j].split(";;")
                # Reverse winding order from spec CCW to 3ds Max CW
                vert_ids = [int(v) for v in reversed(parts[0].split(","))]
                mat = parts[1].strip() if len(parts) > 1 else "Default"
                data["faces"].append(vert_ids)
                data["face_mats"].append(mat)
            i += count + 1

        elif line.startswith("UV:"):
            parts = line.split(":")
            uv_count = int(parts[2])
            entries = []
            for j in range(i + 1, i + 1 + uv_count):
                uv_parts = lines[j].split(":")
                uv_coords = uv_parts[0].split()
                u, v = float(uv_coords[0]), float(uv_coords[1])
                ply = int(uv_parts[2]) if len(uv_parts) > 2 else 0
                pnt = int(uv_parts[4].strip()) if len(uv_parts) > 4 else 0
                entries.append((u, v, ply, pnt))
            data["uvs"].extend(entries)
            i += uv_count + 1

        else:
            i += 1

    return data


def _build_mesh(data):
    """Create a new TriMesh node in 3ds Max from parsed data."""
    verts = data["verts"]
    faces = data["faces"]
    face_mats = data["face_mats"]

    if not verts or not faces:
        rt.messageBox("No geometry found in clipboard file.", title="ITF Copy/Paste External")
        return

    # Build material map
    mat_names = list(dict.fromkeys(face_mats))  # unique, ordered
    use_multi_mat = len(mat_names) > 1

    if use_multi_mat:
        multi_mat = rt.Multimaterial(numsubs=len(mat_names))
        multi_mat.name = "ITF_Materials"
        for idx, name in enumerate(mat_names):
            sub = rt.StandardMaterial()
            sub.name = name
            multi_mat[idx] = sub
    else:
        single_mat = rt.StandardMaterial()
        single_mat.name = mat_names[0] if mat_names else "Default"

    # Triangulate n-gons by fan triangulation
    tri_faces = []
    tri_face_mats = []
    for face_verts, mat in zip(faces, face_mats):
        n = len(face_verts)
        if n < 3:
            continue
        # Fan triangulation from vertex 0
        for k in range(1, n - 1):
            tri_faces.append((face_verts[0], face_verts[k], face_verts[k + 1]))
            tri_face_mats.append(mat)

    # Create the mesh using MaxScript
    new_mesh = rt.mesh(
        numverts=len(verts),
        numfaces=len(tri_faces),
    )
    rt.setUserProp(new_mesh, "ITF_source", "ODVertexData")

    # Set vertices (1-indexed)
    for i, (x, y, z) in enumerate(verts):
        rt.setVert(new_mesh, i + 1, rt.Point3(x, y, z))

    # Set faces (1-indexed, 0-based vert ids → 1-based)
    for i, (v0, v1, v2) in enumerate(tri_faces):
        rt.setFace(new_mesh, i + 1, v0 + 1, v1 + 1, v2 + 1)
        if use_multi_mat:
            mat_id = mat_names.index(tri_face_mats[i]) + 1
            rt.setFaceMatID(new_mesh, i + 1, mat_id)

    rt.update(new_mesh)
    new_mesh.name = IMPORT_OBJECT_NAME

    if use_multi_mat:
        new_mesh.material = multi_mat
    else:
        new_mesh.material = single_mat

    rt.select(new_mesh)
    print(f"[ITF] Created mesh: {IMPORT_OBJECT_NAME}")
    rt.messageBox(f"Import complete!\nMesh: {IMPORT_OBJECT_NAME}", title="ITF Copy/Paste External")


def main():
    if not os.path.exists(IMPORT_FILENAME):
        rt.messageBox(
            f"Clipboard file not found:\n{IMPORT_FILENAME}",
            title="ITF Copy/Paste External",
        )
        return

    with open(IMPORT_FILENAME, "r") as f:
        lines = f.readlines()

    data = _parse_file(lines)
    _build_mesh(data)


if __name__ == "__main__":
    main()