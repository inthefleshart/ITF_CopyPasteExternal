bl_info = {
    "name": "ITF Copy To External",
    "version": (2, 0, 0),
    "blender": (4, 2, 0),
    "author": "Oliver Hotz / ITF",
    "description": "Copies the active mesh object to the cross-app clipboard (ODVertexData.txt)",
    "category": "Object",
}

import bpy
import bmesh
import tempfile
import os
from mathutils import Vector


class ITF_OT_CopyToExternal(bpy.types.Operator):
    """Copy the active mesh to the external cross-app clipboard"""
    bl_idname = "object.itf_copy_to_external"
    bl_label = "ITF Copy To External"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object selected.")
            return {'CANCELLED'}

        mesh = obj.data
        file_path = os.path.join(tempfile.gettempdir(), "ODVertexData.txt")

        try:
            with open(file_path, "w") as f:
                f.write(f"OBJECTNAME:{obj.name}\n")
                self._write_vertices(f, obj)
                self._write_polygons(f, obj)
                self._write_weights(f, obj, mesh)
                self._write_morphs(f, obj, mesh)
                self._write_uvs(f, mesh)
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Exported to {file_path}")
        return {'FINISHED'}

    # ------------------------------------------------------------------
    # Blender uses Z-up. The spec requires Y-up (Blender Z → spec Y,
    # Blender Y → spec -Z, Blender X → spec X).
    # Export:  spec_x = bl_x,  spec_y = bl_z,  spec_z = bl_y * -1
    # ------------------------------------------------------------------

    def _write_vertices(self, f, obj):
        verts = obj.data.vertices
        f.write(f"VERTICES:{len(verts)}\n")
        for v in verts:
            x, y, z = v.co
            f.write(f"{x} {z} {y * -1}\n")

    def _write_polygons(self, f, obj):
        polys = obj.data.polygons
        f.write(f"POLYGONS:{len(polys)}\n")
        for poly in polys:
            surf = "Default"
            if obj.material_slots and poly.material_index < len(obj.material_slots):
                slot = obj.material_slots[poly.material_index]
                if slot.name:
                    surf = slot.name
            vert_str = ",".join(str(obj.data.vertices[vi].index) for vi in poly.vertices)
            f.write(f"{vert_str};;{surf};;FACE\n")

    def _write_weights(self, f, obj, mesh):
        """
        Write one WEIGHT block per vertex group.
        Outer loop = groups, inner loop = vertices (correct order for the spec).
        """
        groups = obj.vertex_groups
        if not groups:
            return

        group_count = len(groups)
        # Build weight table: weight_table[group_index][vertex_index]
        weight_table = [[0.0] * len(mesh.vertices) for _ in range(group_count)]
        for v in mesh.vertices:
            for g in v.groups:
                if g.group < group_count:
                    weight_table[g.group][v.index] = g.weight

        for group in groups:
            weights = weight_table[group.index]
            if any(w > 0.0 for w in weights):
                f.write(f"WEIGHT:{group.name}\n")
                for w in weights:
                    f.write(f"{w}\n")

    def _write_morphs(self, f, obj, mesh):
        shape_keys = mesh.shape_keys
        if not shape_keys or len(shape_keys.key_blocks) < 2:
            return
        basis = shape_keys.key_blocks[0]
        for key in shape_keys.key_blocks[1:]:
            f.write(f"MORPH:{key.name}\n")
            for j, kv in enumerate(key.data):
                delta = kv.co - basis.data[j].co
                dx, dy, dz = delta
                f.write(f"{dx} {dz} {dy * -1}\n")

    def _write_uvs(self, f, mesh):
        for uv_layer in mesh.uv_layers:
            uv_entries = []
            for poly in mesh.polygons:
                for loop_idx in poly.loop_indices:
                    loop = mesh.loops[loop_idx]
                    uv = uv_layer.data[loop_idx].uv
                    uv_entries.append((uv[0], uv[1], poly.index, loop.vertex_index))
            f.write(f"UV:{uv_layer.name}:{len(uv_entries)}\n")
            for u, v, ply, pnt in uv_entries:
                f.write(f"{u} {v}:PLY:{ply}:PNT:{pnt}\n")


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------

def menu_func(self, context):
    self.layout.operator(ITF_OT_CopyToExternal.bl_idname)


def register():
    bpy.utils.register_class(ITF_OT_CopyToExternal)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(ITF_OT_CopyToExternal)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
