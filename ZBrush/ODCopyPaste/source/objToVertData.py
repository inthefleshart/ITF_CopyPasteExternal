# ITF_CopyPasteExternal - ZBrush Helper
# objToVertData.py
#
# Converts a ZBrush-exported OBJ file to the ODVertexData.txt clipboard format.
# This script is compiled into objToVertData.exe using PyInstaller.
#
# Build command (run from project root with .venv active):
#   build_zbrush_exes.bat

import tempfile
import os
import sys


def obj_to_vert_data(input_file):
    """Read an OBJ file and write out ODVertexData.txt format."""
    with open(input_file, "r") as f:
        lines = f.readlines()

    obj_name = "ZBrushObject"

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("v "):
            points.append(stripped[2:])
        elif stripped.startswith("f "):
            polygons.append((count, stripped[2:]))
        elif stripped.startswith("vt "):
            uvs.append(stripped[3:])
        elif stripped.startswith("vn "):
            vertex_normals.append(stripped[3:])
        elif stripped.startswith("o "):
            obj_name = stripped[2:].strip()
        elif stripped.startswith("g ") and obj_name == "ZBrushObject":
            obj_name = stripped[2:].strip()
        count += 1

    output_lines = []

    # --- Object Name ---
    output_lines.append(f"OBJECTNAME:{obj_name}")

    # --- Vertices ---
    output_lines.append(f"VERTICES:{len(points)}")
    for p in points:
        output_lines.append(p)

    # --- Polygons ---
    output_lines.append(f"POLYGONS:{len(polygons)}")
    uv_info = []  # (face_index_0based, uv_index_1based, point_index_0based)
    mat = "Default"

    for face_0idx, (line_before, face_str) in enumerate(polygons):
        pts = face_str.split()
        new_pts = []

        # OBJ indices are 1-based; spec is 0-based
        for pt in pts:
            if "/" in pt:
                tokens = pt.split("/")
                pt_idx = int(tokens[0]) - 1
                new_pts.append(str(pt_idx))
                if len(tokens) > 1 and tokens[1]:
                    uv_info.append((face_0idx, int(tokens[1]), pt_idx))
            else:
                new_pts.append(str(int(pt) - 1))

        # Check for a usemtl directive on the line immediately before this face
        if line_before > 0 and "usemtl" in lines[line_before - 1]:
            mat = lines[line_before - 1].split(None, 1)[1].strip()

        output_lines.append(",".join(new_pts) + ";;" + mat + ";;FACE")

    # --- UVs ---
    if uv_info:
        output_lines.append(f"UV:Default:{len(uv_info)}")
        for face_idx, uv_1idx, pnt_0idx in uv_info:
            uv_str = uvs[uv_1idx - 1].strip()
            output_lines.append(f"{uv_str}:PLY:{face_idx}:PNT:{pnt_0idx}")

    # --- Vertex Normals ---
    if vertex_normals:
        output_lines.append(f"VERTEXNORMALS:{len(vertex_normals)}")
        for n in vertex_normals:
            output_lines.append(n.strip())

    # Write output file
    out_path = os.path.join(tempfile.gettempdir(), "ODVertexData.txt")
    with open(out_path, "w") as f:
        f.write("\n".join(output_lines) + "\n")


# -------------------------------------------------------
# Entry point: input OBJ is next to the compiled .exe
# -------------------------------------------------------
input_file = os.path.join(os.path.dirname(sys.executable), "1.OBJ")
obj_to_vert_data(input_file)
