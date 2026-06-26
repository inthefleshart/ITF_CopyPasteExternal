bl_info = {
    "name": "ITF Paste From External",
    "version": (2, 0),
    "blender": (5, 0, 0),
    "author": "Oliver Hotz / ITF",
    "description": "Pastes geometry from the cross-app clipboard (ODVertexData.txt) into the scene",
    "category": "Object",
}

import bpy
import bmesh
import tempfile
import os
from mathutils import Vector


class ITF_OT_PasteFromExternal(bpy.types.Operator):
    """Paste geometry from the external cross-app clipboard"""
    bl_idname = "object.itf_paste_from_external"
    bl_label = "ITF Paste From External"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        file_path = os.path.join(tempfile.gettempdir(), "ODVertexData.txt")

        if not os.path.exists(file_path):
            self.report({'ERROR'}, f"Clipboard file not found: {file_path}")
            return {'CANCELLED'}

        with open(file_path, "r") as f:
            lines = f.readlines()

        parsed = self._parse(lines)
        if not parsed["verts"] or not parsed["faces"]:
            self.report({'ERROR'}, "No usable geometry found in clipboard file.")
            return {'CANCELLED'}

        obj = self._build_mesh(context, parsed)
        if obj is None:
            self.report({'ERROR'}, "Failed to create mesh.")
            return {'CANCELLED'}

        self._apply_weights(obj, parsed)
        self._apply_morphs(obj, parsed)
        self._apply_uvs(obj, parsed)

        self.report({'INFO'}, f"Pasted mesh: {obj.name}")
        return {'FINISHED'}

    # ------------------------------------------------------------------
    # Import coordinate conversion:
    # spec_x → bl_x,  spec_y → bl_z,  spec_z → bl_y * -1
    # ------------------------------------------------------------------

    def _parse(self, lines):
        data = {
            "verts": [], "faces": [], "face_mats": [],
            "weights": {}, "morphs": {}, "uvs": {},
        }

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            if line.startswith("VERTICES:"):
                count = int(line.split(":")[1])
                for j in range(i + 1, i + 1 + count):
                    p = lines[j].split()
                    # spec (X, Y, Z) → Blender (X, -Z, Y)
                    data["verts"].append([float(p[0]), float(p[2]) * -1, float(p[1])])
                i += count + 1

            elif line.startswith("POLYGONS:"):
                count = int(line.split(":")[1])
                for j in range(i + 1, i + 1 + count):
                    parts = lines[j].split(";;")
                    vert_ids = [int(v) for v in parts[0].split(",")]
                    mat = parts[1].strip() if len(parts) > 1 else "Default"
                    data["faces"].append(vert_ids)
                    data["face_mats"].append(mat)
                i += count + 1

            elif line.startswith("WEIGHT:"):
                name = line.split(":", 1)[1].strip()
                ws = []
                j = i + 1
                while j < len(lines) and not lines[j].rstrip().startswith(
                    ("VERTICES:", "POLYGONS:", "WEIGHT:", "UV:", "MORPH:", "VERTEXNORMALS:", "VERTEXCOLORS:")
                ):
                    val = lines[j].strip()
                    ws.append(float(val) if val not in ("None", "") else 0.0)
                    j += 1
                data["weights"][name] = ws
                i = j

            elif line.startswith("MORPH:"):
                name = line.split(":", 1)[1].strip()
                deltas = []
                j = i + 1
                while j < len(lines) and not lines[j].rstrip().startswith(
                    ("VERTICES:", "POLYGONS:", "WEIGHT:", "UV:", "MORPH:", "VERTEXNORMALS:", "VERTEXCOLORS:")
                ):
                    val = lines[j].strip()
                    if val == "None":
                        deltas.append(None)
                    else:
                        p = val.split()
                        # spec delta (dX, dY, dZ) → Blender (dX, -dZ, dY)
                        deltas.append(Vector((float(p[0]), float(p[2]) * -1, float(p[1]))))
                    j += 1
                data["morphs"][name] = deltas
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
                    ply = int(uv_parts[2]) if len(uv_parts) > 2 else 0
                    pnt = int(uv_parts[4].strip()) if len(uv_parts) > 4 else 0
                    entries.append((u, v, ply, pnt))
                data["uvs"][uv_name] = entries
                i += uv_count + 1

            else:
                i += 1

        return data

    def _build_mesh(self, context, data):
        # Ensure materials exist in scene
        used_mats = list(dict.fromkeys(data["face_mats"]))  # preserve order, deduplicate
        for mat_name in used_mats:
            if mat_name not in bpy.data.materials:
                bpy.data.materials.new(mat_name)

        active_obj = context.active_object
        if active_obj is not None and active_obj.type == 'MESH':
            # Replace geometry in-place
            me = active_obj.data
            bpy.ops.object.mode_set(mode='OBJECT')
            me.clear_geometry()
            me.from_pydata(data["verts"], [], data["faces"])
            me.update()
            obj = active_obj
        else:
            # Create a brand new object
            me = bpy.data.meshes.new("ITF_Paste")
            me.from_pydata(data["verts"], [], data["faces"])
            me.update()
            obj = bpy.data.objects.new("ITF_Paste", me)
            context.collection.objects.link(obj)

        # Assign materials
        obj.data.materials.clear()
        for mat_name in used_mats:
            obj.data.materials.append(bpy.data.materials[mat_name])

        mat_index_map = {name: i for i, name in enumerate(used_mats)}
        for i, poly in enumerate(obj.data.polygons):
            poly.material_index = mat_index_map.get(data["face_mats"][i], 0)

        # Remove all vertex groups before re-applying
        obj.vertex_groups.clear()

        context.view_layer.update()
        return obj

    def _apply_weights(self, obj, data):
        for group_name, weights in data["weights"].items():
            vg = obj.vertex_groups.new(name=group_name)
            for v_idx, w in enumerate(weights):
                if w > 0.0:
                    vg.add([v_idx], w, 'REPLACE')

    def _apply_morphs(self, obj, data):
        if not data["morphs"]:
            return

        # Ensure shape keys exist and base is set
        if obj.data.shape_keys:
            bpy.ops.object.shape_key_remove(all=True)
        basis = obj.shape_key_add(from_mix=False)
        basis.name = "Basis"

        for morph_name, deltas in data["morphs"].items():
            sk = obj.shape_key_add(from_mix=False)
            sk.name = morph_name
            for v_idx, vert in enumerate(obj.data.vertices):
                if v_idx < len(deltas) and deltas[v_idx] is not None:
                    sk.data[v_idx].co = vert.co + deltas[v_idx]

    def _apply_uvs(self, obj, data):
        mesh = obj.data

        # Remove all existing UV layers
        while mesh.uv_layers:
            mesh.uv_layers.remove(mesh.uv_layers[0])

        for uv_name, entries in data["uvs"].items():
            uv_layer = mesh.uv_layers.new(name=uv_name)

            # Build a bmesh to look up face → loop mapping
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.faces.ensure_lookup_table()
            uv_bm_layer = bm.loops.layers.uv[uv_name]

            # Build a per-face lookup: face_id → {pnt_id: loop}
            face_loop_map = {}
            for face in bm.faces:
                loop_map = {}
                for loop in face.loops:
                    loop_map[loop.vert.index] = loop
                face_loop_map[face.index] = loop_map

            for u, v, ply, pnt in entries:
                if ply < len(bm.faces) and pnt in face_loop_map.get(ply, {}):
                    face_loop_map[ply][pnt][uv_bm_layer].uv = (u, v)

            bm.to_mesh(mesh)
            bm.free()

        mesh.update()


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------

def menu_func(self, context):
    self.layout.operator(ITF_OT_PasteFromExternal.bl_idname)


def register():
    bpy.utils.register_class(ITF_OT_PasteFromExternal)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(ITF_OT_PasteFromExternal)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
