"""
ITF_CopyPasteExternal - Maya Export (Copy To External)
Exports the selected mesh to ODVertexData.txt for use in other DCC applications.

Supports: Vertices, Polygons, Skin Weights, UV Maps (including multiple sets / UDIM tiles)

Compatible with Maya 2020+ (Python 3, OpenMaya 2)

Usage:
    Select a mesh object, then run this script via the Maya Script Editor (Python tab).
"""

import os
import tempfile
import maya.cmds as cmds
import maya.api.OpenMaya as om2


def _get_skin_cluster(mesh_name):
    """Return the skinCluster node attached to mesh_name, or None."""
    history = cmds.listHistory(mesh_name, interestLevel=1) or []
    for node in history:
        if cmds.nodeType(node) == "skinCluster":
            return node
    return None


def _export_skin_weights(f, mesh_name, vertex_count):
    """Write WEIGHT blocks for each skin influence to the file."""
    skin_cluster = _get_skin_cluster(mesh_name)
    if not skin_cluster:
        return

    influences = cmds.skinCluster(skin_cluster, query=True, influence=True) or []
    if not influences:
        return

    for influence in influences:
        weights = []
        for v in range(vertex_count):
            vtx = f"{mesh_name}.vtx[{v}]"
            w = cmds.skinPercent(skin_cluster, vtx, transform=influence, query=True)
            weights.append(w)

        # Only write this influence if it has any non-zero weights
        if any(w > 0.0 for w in weights):
            # Use the short influence name as the weight map label
            label = influence.split("|")[-1].split(":")[-1]
            f.write(f"WEIGHT:{label}\n")
            for w in weights:
                f.write(f"{w}\n")


def _export_uvs(f, mesh_name):
    """
    Write UV blocks for every UV set on the mesh.
    Supports multiple UV sets and UDIM tiles (tile offsets are preserved in U coordinates).
    """
    uv_sets = cmds.polyUVSet(mesh_name, query=True, allUVSets=True) or []

    for uv_set in uv_sets:
        # Collect per-loop UV data: (u, v, poly_index, vertex_index)
        poly_count = cmds.polyEvaluate(mesh_name, face=True)
        uv_entries = []

        for face_id in range(poly_count):
            face_str = f"{mesh_name}.f[{face_id}]"
            # Get the vertex indices for this face
            vtx_info = cmds.polyInfo(face_str, faceToVertex=True)
            if not vtx_info:
                continue
            raw = vtx_info[0].split(":")[1].strip().split()
            vert_ids = [int(v) for v in raw if v.strip()]

            # Get UV coordinates for each vertex in this face
            for vtx_id in vert_ids:
                vtx_face_str = f"{mesh_name}.vtxFace[{vtx_id}][{face_id}]"
                try:
                    uvs = cmds.polyEditUV(
                        vtx_face_str,
                        query=True,
                        uvSetName=uv_set,
                    )
                    if uvs and len(uvs) >= 2:
                        uv_entries.append((uvs[0], uvs[1], face_id, vtx_id))
                except Exception:
                    pass

        if uv_entries:
            f.write(f"UV:{uv_set}:{len(uv_entries)}\n")
            for u, v, ply, pnt in uv_entries:
                f.write(f"{u} {v}:PLY:{ply}:PNT:{pnt}\n")


def main():
    export_filename = os.path.join(tempfile.gettempdir(), "ODVertexData.txt")

    selection = cmds.ls(selection=True)
    if not selection:
        cmds.confirmDialog(title="Error", message="No object selected!", button=["Ok"])
        return

    obj_name = selection[0]

    # Ensure we are working with a mesh shape
    shapes = cmds.listRelatives(obj_name, shapes=True, fullPath=True) or []
    mesh_shape = next((s for s in shapes if cmds.nodeType(s) == "mesh"), None)
    if not mesh_shape:
        cmds.confirmDialog(title="Error", message="Selected object has no mesh shape.", button=["Ok"])
        return

    vertex_count = cmds.polyEvaluate(obj_name, vertex=True)
    poly_count = cmds.polyEvaluate(obj_name, face=True)

    with open(export_filename, "w") as f:
        # --- Vertices ---
        f.write(f"VERTICES:{vertex_count}\n")
        for v in range(vertex_count):
            vtx_str = f"{obj_name}.vtx[{v}]"
            pos = cmds.xform(vtx_str, query=True, objectSpace=True, translation=True)
            f.write(f"{pos[0]} {pos[1]} {pos[2]}\n")

        # --- Polygons ---
        f.write(f"POLYGONS:{poly_count}\n")
        for face_id in range(poly_count):
            face_str = f"{obj_name}.f[{face_id}]"
            cmds.select(face_str, replace=True)
            vtx_info = cmds.polyInfo(faceToVertex=True)
            raw = vtx_info[0].split(":")[1].strip().split()
            vert_ids = [int(v) for v in raw if v.strip()]
            poly_str = ",".join(str(v) for v in vert_ids)
            f.write(f"{poly_str};;Default;;FACE\n")

        cmds.select(selection, replace=True)

        # --- Skin Weights ---
        _export_skin_weights(f, obj_name, vertex_count)

        # --- UVs ---
        _export_uvs(f, obj_name)

    cmds.confirmDialog(
        title="ITF Copy/Paste External",
        message=f"Export complete!\n{export_filename}",
        button=["Ok"],
    )
    print(f"[ITF] Exported to: {export_filename}")


main()
