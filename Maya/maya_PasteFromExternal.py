"""
ITF_CopyPasteExternal - Maya Import (Paste From External)
Imports geometry from ODVertexData.txt into Maya as a new mesh object.

Supports: Vertices, Polygons, Skin Weights, UV Maps (including multiple sets / UDIM tiles),
          Vertex Normals

Compatible with Maya 2020+ (Python 3, OpenMaya 2)

Usage:
    Run this script via the Maya Script Editor (Python tab).
    A new mesh object named "ITF_Paste" will be created in the scene.
"""

from __future__ import print_function
import os
import tempfile
import maya.cmds as cmds
import maya.api.OpenMaya as om2


IMPORT_OBJECT_NAME = "ITF_Paste"
IMPORT_FILENAME = os.path.join(tempfile.gettempdir(), "ODVertexData.txt")


# ---------------------------------------------------------------------------
# File parsing
# ---------------------------------------------------------------------------

def _parse_file(lines):
    """
    Parse ODVertexData.txt lines into a structured dict:
    {
        'vertices': [(x, y, z), ...],
        'polygons': [(material, [v0, v1, ...]), ...],
        'weights':  {name: [w0, w1, ...], ...},
        'uvs':      {name: [(u, v, ply, pnt), ...], ...},
        'normals':  [(nx, ny, nz, ply, pnt), ...],
        'object_name': "ITF_Paste",
    }
    """
    data = {
        "vertices": [],
        "polygons": [],
        "weights": {},
        "uvs": {},
        "normals": [],
        "object_name": "ITF_Paste",
    }

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if line.startswith("VERTICES:"):
            count = int(line.split(":")[1])
            for j in range(i + 1, i + 1 + count):
                parts = lines[j].split()
                data["vertices"].append((float(parts[0]), float(parts[1]), float(parts[2])))
            i += count + 1

        elif line.startswith("POLYGONS:"):
            count = int(line.split(":")[1])
            for j in range(i + 1, i + 1 + count):
                parts = lines[j].split(";;")
                vert_ids = [int(v) for v in parts[0].split(",")]
                mat = parts[1].strip() if len(parts) > 1 else "Default"
                data["polygons"].append((mat, vert_ids))
            i += count + 1

        elif line.startswith("WEIGHT:"):
            name = line.split(":", 1)[1].strip()
            weights = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith(
                ("VERTICES:", "POLYGONS:", "WEIGHT:", "UV:", "MORPH:", "VERTEXNORMALS:", "VERTEXCOLORS:", "OBJECTNAME:")
            ):
                val = lines[j].strip()
                weights.append(float(val) if val not in ("None", "") else 0.0)
                j += 1
            data["weights"][name] = weights
            i = j

        elif line.startswith("UV:"):
            parts = line.split(":")
            uv_name = parts[1]
            uv_count = int(parts[2])
            entries = []
            for j in range(i + 1, i + 1 + uv_count):
                uv_parts = lines[j].split(":")
                uv_coords = uv_parts[0].split()
                u, v = float(uv_coords[0]), float(uv_coords[1])
                # Format: u v:PLY:poly_id:PNT:pnt_id
                ply = int(uv_parts[2]) if len(uv_parts) > 2 else 0
                pnt = int(uv_parts[4]) if len(uv_parts) > 4 else 0
                entries.append((u, v, ply, pnt))
            data["uvs"][uv_name] = entries
            i += uv_count + 1

        elif line.startswith("VERTEXNORMALS:"):
            parts = line.split(":")
            count = int(parts[1])
            for j in range(i + 1, i + 1 + count):
                norm_parts = lines[j].split(":")
                xyz = norm_parts[0].split()
                nx, ny, nz = float(xyz[0]), float(xyz[1]), float(xyz[2])
                ply = int(norm_parts[2]) if len(norm_parts) > 2 else 0
                pnt = int(norm_parts[4].strip()) if len(norm_parts) > 4 else j - (i + 1)
                data["normals"].append((nx, ny, nz, ply, pnt))
            i += count + 1

        elif line.startswith("OBJECTNAME:"):
            data["object_name"] = line.split(":", 1)[1].strip()
            i += 1

        else:
            i += 1

    return data


# ---------------------------------------------------------------------------
# Mesh creation
# ---------------------------------------------------------------------------

def _create_mesh(data):
    """Build the Maya mesh from parsed data using the OpenMaya 2 batch API."""
    vertices = data["vertices"]
    polygons = data["polygons"]

    if not vertices or not polygons:
        cmds.confirmDialog(title="Error", message="No geometry found in file!", button=["Ok"])
        return None

    # Build OM2 arrays
    point_array = om2.MPointArray([om2.MPoint(v[0], v[1], v[2]) for v in vertices])
    poly_counts = om2.MIntArray([len(p[1]) for p in polygons])
    poly_connects = om2.MIntArray([vi for p in polygons for vi in p[1]])

    mesh_fn = om2.MFnMesh()
    mesh_obj = mesh_fn.create(point_array, poly_counts, poly_connects)

    # Assign to default shader
    cmds.sets(mesh_fn.name(), edit=True, forceElement="initialShadingGroup")

    # Rename the parent transform node (mesh_fn.name() is the shape node name)
    parent_transform = cmds.listRelatives(mesh_fn.name(), parent=True, fullPath=True)[0]
    final_name = cmds.rename(parent_transform, data["object_name"])
    return final_name


def _apply_uvs(mesh_name, data):
    """Apply all UV sets to the mesh using OpenMaya 2."""
    try:
        selection_list = om2.MSelectionList()
        selection_list.add(mesh_name)
        dag_path = selection_list.getDagPath(0)
        dag_path.extendToShape()
        mesh_fn = om2.MFnMesh(dag_path)
    except Exception as e:
        print("[ITF] Warning: Could not initialize OpenMaya mesh for UV import: {0}".format(e))
        return

    for uv_set_name, entries in data["uvs"].items():
        if not entries:
            continue

        # Create/rename UV set in Maya
        existing_sets = mesh_fn.getUVSetNames()
        if uv_set_name not in existing_sets:
            if "map1" in existing_sets and len(existing_sets) == 1:
                cmds.polyUVSet(mesh_name, rename=True, uvSet="map1", newUVSet=uv_set_name)
            else:
                cmds.polyUVSet(mesh_name, create=True, uvSet=uv_set_name)

        # Build a lookup: (poly_id, pnt_id) -> (u, v)
        uv_lookup = {}
        for u, v, ply, pnt in entries:
            uv_lookup[(ply, pnt)] = (u, v)

        # Build unique coordinates and map indices
        unique_uvs = []
        uv_to_index = {}
        uv_counts = om2.MIntArray()
        uv_ids = om2.MIntArray()

        for face_id in range(mesh_fn.numPolygons):
            vert_ids = mesh_fn.getPolygonVertices(face_id)
            uv_counts.append(len(vert_ids))
            
            for vtx_id in vert_ids:
                uv_coord = uv_lookup.get((face_id, vtx_id))
                if uv_coord is None:
                    uv_coord = (0.0, 0.0)
                
                if uv_coord not in uv_to_index:
                    uv_to_index[uv_coord] = len(unique_uvs)
                    unique_uvs.append(uv_coord)
                
                uv_ids.append(uv_to_index[uv_coord])

        u_array = [uv[0] for uv in unique_uvs]
        v_array = [uv[1] for uv in unique_uvs]

        try:
            mesh_fn.setUVs(u_array, v_array, uv_set_name)
            mesh_fn.assignUVs(uv_counts, uv_ids, uv_set_name)
        except Exception as e:
            print("[ITF] Warning: Could not assign UVs for set '{0}': {1}".format(uv_set_name, e))


def _apply_skin_weights(mesh_name, data):
    """Apply skin weights. Creates joints as stand-ins if the rig is not present."""
    if not data["weights"]:
        return

    joint_names = []
    for influence_name in data["weights"]:
        if not cmds.objExists(influence_name):
            jnt = cmds.joint(name=influence_name)
            cmds.select(clear=True)
        else:
            jnt = influence_name
        joint_names.append(jnt)

    skin_cluster = cmds.skinCluster(
        joint_names + [mesh_name],
        toSelectedBones=True,
        name="{0}_skinCluster".format(mesh_name),
    )[0]

    vertex_count = cmds.polyEvaluate(mesh_name, vertex=True)
    for influence, weights in data["weights"].items():
        for v in range(min(vertex_count, len(weights))):
            vtx = "{0}.vtx[{1}]".format(mesh_name, v)
            cmds.skinPercent(
                skin_cluster, vtx,
                transformValue=[(influence, weights[v])]
            )


def _apply_normals(mesh_name, data):
    """Apply vertex normals."""
    for nx, ny, nz, ply, pnt in data["normals"]:
        vtx_face = "{0}.vtxFace[{1}][{2}]".format(mesh_name, pnt, ply)
        try:
            cmds.select(vtx_face)
            cmds.polyNormalPerVertex(xyz=(nx, ny, nz))
        except Exception:
            pass
    cmds.select(clear=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(IMPORT_FILENAME):
        cmds.confirmDialog(
            title="Error",
            message="Cannot find clipboard file:\n{0}".format(IMPORT_FILENAME),
            button=["Ok"],
        )
        return

    with open(IMPORT_FILENAME, "r") as f:
        lines = f.readlines()

    data = _parse_file(lines)

    if not data["vertices"]:
        cmds.confirmDialog(title="Error", message="File contains no vertex data.", button=["Ok"])
        return

    mesh_name = _create_mesh(data)
    if not mesh_name:
        return

    _apply_uvs(mesh_name, data)

    if data["normals"]:
        _apply_normals(mesh_name, data)

    if data["weights"]:
        try:
            _apply_skin_weights(mesh_name, data)
        except Exception as e:
            print("[ITF] Warning: Could not apply skin weights: {0}".format(e))

    cmds.select(mesh_name)
    print("[ITF] Imported mesh: {0}".format(mesh_name))
    cmds.confirmDialog(
        title="ITF Copy/Paste External",
        message="Import complete!\nMesh: {0}".format(mesh_name),
        button=["Ok"],
    )


main()
