# ITF_CopyPasteExternal - ZBrush Helper
# vertDataToObj.py
#
# Converts ODVertexData.txt clipboard format to an OBJ file for ZBrush import.
# This script is compiled into vertDataToObj.exe using PyInstaller.
#
# Build command (run from project root with .venv active):
#   build_zbrush_exes.bat

import tempfile
import os
import sys


def vert_data_to_obj(output_file):
    """Read ODVertexData.txt and write a standard OBJ file."""
    input_file = os.path.join(tempfile.gettempdir(), "ODVertexData.txt")
    with open(input_file, "r") as f:
        lines = f.readlines()

    # --- Parse ---
    vert_blocks = []    # [(count, start_line), ...]
    poly_blocks = []    # [(count, start_line), ...]
    uv_maps = []        # [(name, count, start_line), ...]
    normal_blocks = []  # [(count, start_line), ...]

    count = 0
    for line in lines:
        s = line.rstrip()
        if s.startswith("VERTICES:"):
            vert_blocks.append((int(s.split(":")[1]), count))
        elif s.startswith("POLYGONS:"):
            poly_blocks.append((int(s.split(":")[1]), count))
        elif s.startswith("VERTEXNORMALS:"):
            parts = s.split(":")
            normal_blocks.append((int(parts[1]), count))
        elif s.startswith("UV:"):
            parts = s.split(":")
            if len(parts) >= 3 and parts[2] != "0":
                uv_maps.append((parts[1], int(parts[2]), count))
        count += 1

    output = []
    output.append("o ODVertexData.obj")
    output.append("g default")

    # --- Vertices ---
    for v_count, v_start in vert_blocks:
        for i in range(v_start + 1, v_start + v_count + 1):
            x = list(map(float, lines[i].split()))
            output.append(f"v {x[0]} {x[1]} {x[2]}")

    # --- UV Texture Coords ---
    # Collect unique UV values in insertion order (for vt lines)
    uv_values = []       # list of "u v" strings (unique)
    uv_value_set = set()
    # per-entry assignment: list of "u v" string (matches face vertex order)
    uv_assignment = []

    for uv_name, uv_count, uv_start in uv_maps:
        for i in range(uv_start + 1, uv_start + uv_count + 1):
            split = lines[i].split(":")
            uv_str = f"{float(split[0].split()[0])} {float(split[0].split()[1])}"
            if uv_str not in uv_value_set:
                uv_values.append(uv_str)
                uv_value_set.add(uv_str)
            uv_assignment.append(uv_str)

    for uv in uv_values:
        output.append(f"vt {uv}")

    # --- Vertex Normals ---
    for n_count, n_start in normal_blocks:
        for i in range(n_start + 1, n_start + n_count + 1):
            x = list(map(float, lines[i].split()))
            output.append(f"vn {x[0]} {x[1]} {x[2]}")

    # --- Faces ---
    has_uvs = len(uv_assignment) > 0
    has_normals = len(normal_blocks) > 0

    global_uv_idx = 0  # index into uv_assignment
    global_normal_idx = 0

    current_mat = ""
    for poly_count, poly_start in poly_blocks:
        for i in range(poly_start + 1, poly_start + poly_count + 1):
            parts = lines[i].split(";;")
            pt_indices_0based = [int(p) for p in parts[0].strip().split(",")]
            mat = parts[1].strip() if len(parts) > 1 else "Default"

            if mat != current_mat:
                output.append(f"g {mat}")
                output.append(f"usemtl {mat}")
                current_mat = mat

            # Build face tokens: v/vt/vn  (all 1-based in OBJ)
            face_tokens = []
            for k, pt_0based in enumerate(pt_indices_0based):
                token = str(pt_0based + 1)
                if has_uvs:
                    uv_1based = uv_values.index(uv_assignment[global_uv_idx]) + 1
                    global_uv_idx += 1
                    token += f"/{uv_1based}"
                    if has_normals:
                        token += f"/{global_normal_idx + 1}"
                elif has_normals:
                    token += f"//{global_normal_idx + 1}"

                if has_normals:
                    global_normal_idx += 1

                face_tokens.append(token)

            output.append("f " + " ".join(face_tokens))

    # --- Write ---
    with open(output_file, "w") as f:
        f.write("\n".join(output) + "\n")


# -------------------------------------------------------
# Entry point: output OBJ is next to the compiled .exe
# -------------------------------------------------------
output_file = os.path.join(os.path.dirname(sys.executable), "1.OBJ")
vert_data_to_obj(output_file)