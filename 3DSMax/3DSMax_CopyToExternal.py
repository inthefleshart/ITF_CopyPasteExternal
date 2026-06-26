"""
ITF_CopyPasteExternal - 3ds Max Export (Copy To External)
Exports the selected mesh to ODVertexData.txt for use in other DCC applications.

Supports: Vertices, Polygons, UV Maps, Material names

Compatible with 3ds Max 2020+ (Python 3, pymxs API)

Usage:
    1. Edit the path in the .ms launcher file to point to this script.
    2. Select a mesh object in 3ds Max, then run the launcher from the MaxScript Editor.

    Or run directly from MaxScript:
        python.ExecuteFile @"C:\path\to\3DSMax_CopyToExternal.py"
"""

import tempfile
import os
import pymxs

rt = pymxs.runtime


def _get_mesh_and_node():
    """Return the TriMesh and its node for the first selected object, or (None, None)."""
    if rt.selection.count == 0:
        rt.messageBox("Please select a mesh object first.", title="ITF Copy/Paste External")
        return None, None

    node = rt.selection[0]
    tri_obj = rt.snapshotAsMesh(node)
    if tri_obj is None or tri_obj.numverts == 0:
        rt.messageBox("Selected object has no mesh data.", title="ITF Copy/Paste External")
        return None, None

    return tri_obj, node


def _write_vertices(f, mesh):
    """Write vertex positions. 3ds Max is Z-up, right-handed. Spec is Y-up.
    Conversion: spec_x = max_x,  spec_y = max_z,  spec_z = max_y * -1
    """
    count = mesh.numverts
    f.write(f"VERTICES:{count}\n")
    for i in range(1, count + 1):
        v = rt.getVert(mesh, i)
        f.write(f"{v.x} {v.z} {v.y * -1}\n")


def _write_polygons(f, mesh, node):
    """Write face/polygon data with material names."""
    num_faces = mesh.numfaces
    f.write(f"POLYGONS:{num_faces}\n")

    # Build material name lookup by materialID
    mat_names = {}
    node_mat = node.material
    if node_mat is not None:
        if rt.classOf(node_mat) == rt.Multimaterial:
            for i in range(node_mat.numsubs):
                sub = node_mat[i]
                if sub is not None:
                    mat_names[i + 1] = sub.name
        else:
            mat_names[1] = node_mat.name

    for i in range(1, num_faces + 1):
        face = rt.getFace(mesh, i)
        mat_id = rt.getFaceMatID(mesh, i)
        mat_name = mat_names.get(mat_id, "Default")

        # 3ds Max face vertex indices are 1-based; spec is 0-based
        # 3ds Max uses CW winding; reverse to CCW for spec
        v0 = int(face.x) - 1
        v1 = int(face.y) - 1
        v2 = int(face.z) - 1
        f.write(f"{v2},{v1},{v0};;{mat_name};;FACE\n")


def _write_uvs(f, mesh):
    """Write UV coordinates from the first UV channel."""
    num_faces = mesh.numfaces
    num_tverts = rt.getNumTVerts(mesh)

    if num_tverts == 0:
        return

    uv_entries = []
    for face_id in range(1, num_faces + 1):
        tv_face = rt.getTVFace(mesh, face_id)
        face = rt.getFace(mesh, face_id)

        # tv_face.x/y/z are 1-based UV vert indices; face.x/y/z are 1-based point indices
        tv_indices = [int(tv_face.x), int(tv_face.y), int(tv_face.z)]
        pt_indices = [int(face.x) - 1, int(face.y) - 1, int(face.z) - 1]

        for k in range(3):
            tv = rt.getTVert(mesh, tv_indices[k])
            uv_entries.append((tv.x, tv.y, face_id - 1, pt_indices[k]))

    if uv_entries:
        f.write(f"UV:UVMap:{len(uv_entries)}\n")
        for u, v, ply, pnt in uv_entries:
            f.write(f"{u} {v}:PLY:{ply}:PNT:{pnt}\n")


def main():
    mesh, node = _get_mesh_and_node()
    if mesh is None:
        return

    file_path = os.path.join(tempfile.gettempdir(), "ODVertexData.txt")

    with open(file_path, "w") as f:
        _write_vertices(f, mesh)
        _write_polygons(f, mesh, node)
        _write_uvs(f, mesh)

    print(f"[ITF] Exported to: {file_path}")
    rt.messageBox(f"Export complete!\n{file_path}", title="ITF Copy/Paste External")


if __name__ == "__main__":
    main()