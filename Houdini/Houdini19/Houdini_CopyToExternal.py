import tempfile, os, re

# ITF_CopyPasteExternal - Houdini Export (Copy To External)
# Tested with Houdini 19+
#
# Instructions:
#   1. Right-click an empty area of the tool shelf and click "New Tool..."
#   2. In the Options tab, provide a Label like "Copy (to External)"
#   3. In the Script tab, paste this entire document.
#      Ensure Script Language is set to "Python".
#   Pressing this button exports the currently selected SOP to the cross-app clipboard.
#
# Features and Limitations:
#   - Only one SOP must be selected at a time.
#   - Only polygon face geometry is supported (no NURBS/bezier curves).
#   - Exports point positions, normals (N) and colors (Cd).
#   - Exports named material assignments via the shop_materialpath attribute.
#   - Exports vertex UV coordinate attributes (uv).

if len(hou.selectedNodes()) != 1:
    hou.ui.displayMessage(
        "There must be exactly one selected node.",
        severity=hou.severityType.Error,
        title="ITF Copy/Paste External",
    )
else:
    node = hou.selectedNodes()[0]

    if not isinstance(node, hou.SopNode):
        hou.ui.displayMessage(
            "Selected node must be a SOP node.",
            severity=hou.severityType.Error,
            title="ITF Copy/Paste External",
        )
    else:
        # Houdini stores faces in CW order; reverse to CCW for the spec.
        rev = node.node("..").createNode("reverse")
        rev.setInput(0, node)
        geo = rev.geometry()

        with open(os.path.join(tempfile.gettempdir(), "ODVertexData.txt"), "w") as f:
            # --- Object Name ---
            obj_name = node.parent().name() if node.parent() else node.name()
            print(f"OBJECTNAME:{obj_name}", file=f)

            # Collect texture-coordinate vertex attributes
            texture_coord_attribs = [
                attrib
                for attrib in geo.vertexAttribs()
                if attrib.options().get("type") == "texturecoord"
            ]

            point_normals = [] if geo.findPointAttrib("N") else None
            point_colors = [] if geo.findPointAttrib("Cd") else None

            # --- Vertices ---
            # Houdini is Y-up; spec is Y-up — no coordinate conversion needed.
            print(f"VERTICES:{len(geo.points())}", file=f)
            for p in geo.points():
                pos = p.position()
                print(f"{pos[0]} {pos[1]} {pos[2]}", file=f)
                if point_normals is not None:
                    point_normals.append(p.attribValue("N"))
                if point_colors is not None:
                    point_colors.append(p.attribValue("Cd"))

            # --- Polygons ---
            polygons = []
            polygon_vertex_point_indices = []
            polygon_uv_entries = {}

            for p in geo.prims():
                if isinstance(p, hou.Face):
                    vertex_point_indices = []
                    for v in p.vertices():
                        vertex_point_indices.append(v.point().number())
                        for uv_attrib in texture_coord_attribs:
                            uv_val = v.attribValue(uv_attrib)
                            polygon_uv_entries.setdefault(uv_attrib.name(), []).append(
                                f"{uv_val[0]} {uv_val[1]}:PLY:{len(polygons)}:PNT:{v.point().number()}"
                            )

                    material_name = (
                        p.attribValue("shop_materialpath")
                        if geo.findPrimAttrib("shop_materialpath")
                        else ""
                    )
                    polygons.append(
                        f'{",".join(map(str, vertex_point_indices))};;{material_name};;FACE'
                    )
                    polygon_vertex_point_indices.append(vertex_point_indices)
                else:
                    print(f'Skipping unsupported primitive type "{p}".')

            print(f"POLYGONS:{len(polygons)}", file=f)
            for p in polygons:
                print(p, file=f)

            # --- UVs ---
            for uv_attrib in texture_coord_attribs:
                entries = polygon_uv_entries.get(uv_attrib.name(), [])
                print(f"UV:{uv_attrib.name()}:{len(entries)}", file=f)
                for u in entries:
                    print(u, file=f)

            # --- Vertex Normals ---
            if point_normals is not None:
                print(f"VERTEXNORMALS:{len(geo.points())}", file=f)
                for n in point_normals:
                    print(f"{n[0]} {n[1]} {n[2]}", file=f)

            # --- Vertex Colors ---
            if point_colors is not None:
                print(f"VERTEXCOLORS:{len(geo.points())}:DEF:1 1 1 1", file=f)
                for c in point_colors:
                    print(f"{c[0]} {c[1]} {c[2]} 1.0", file=f)

        rev.destroy()
        hou.ui.displayMessage(
            "Copied to clipboard!",
            title="ITF Copy/Paste External",
        )
