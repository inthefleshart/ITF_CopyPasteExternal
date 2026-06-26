import toolutils, tempfile, os, sys, re

# ITF_CopyPasteExternal - Houdini Import (Paste From External)
# Tested with Houdini 19+
#
# Instructions:
#   1. Right-click an empty area of the tool shelf and click "New Tool..."
#   2. In the Options tab, provide a Label like "Paste (from External)"
#   3. In the Script tab, paste this entire document.
#      Ensure Script Language is set to "Python".
#   Pressing this button pastes previously copied geometry from the cross-app clipboard.
#
#   Paste location follows the viewport focus:
#     - In Geometry scope (e.g. /obj/geo1/): creates a Python SOP "pastefromexternal".
#     - In Object scope (/obj/):             creates a geo node containing the Python SOP.
#     - In Solaris scope (/stage/):          creates a "SOP Create" node with the Python SOP inside.
#   The Python SOP includes a "Reload Geometry" button to re-read the clipboard.
#   The Python SOP merges its output with the first input if connected.

parentNode = toolutils.sceneViewer().pwd()

if parentNode.childTypeCategory().name() == "Object":
    parentNode = parentNode.createNode("geo")
    parentNode.moveToGoodPosition()
elif parentNode.childTypeCategory().name() == "Lop":
    parentNode = parentNode.createNode("sopcreate")
    parentNode.moveToGoodPosition()
    parentNode = parentNode.node("./sopnet/create/")
elif parentNode.childTypeCategory().name() != "Sop":
    hou.ui.displayMessage(
        "The active scene view must be in a SOP, OBJ, or LOP context to paste.",
        severity=hou.severityType.Error,
        title="ITF Copy/Paste External",
    )

node = parentNode.createNode("python", "pastefromexternal1")
node.setUserData("nodeshape", "tabbed_left")

# Hide the default python parm interface and add our own "Reload Geometry" button
templateGroup = node.parmTemplateGroup()
for p in templateGroup.entries():
    p.hide(True)
    templateGroup.replace(p.name(), p)

templateGroup.append(hou.ButtonParmTemplate(
    "btnReloadGeometry",
    "Reload Geometry",
    script_callback_language=hou.scriptLanguage.Python,
    script_callback="hou.pwd().cook(force=True)",
))
node.setParmTemplateGroup(templateGroup)

node.setParms({"python": '''
import tempfile, os, sys, re

node = hou.pwd()
geo = hou.Geometry()

lines = []
with open(os.path.join(tempfile.gettempdir(), "ODVertexData.txt"), "r") as line:
    for header in map(lambda l: l.rstrip().split(":"), line):
        if header[0] == "VERTICES":
            for _ in range(int(header[1])):
                xyz = next(line).split(" ")
                point = geo.createPoint()
                # Houdini is Y-up; spec is Y-up — no coordinate conversion needed
                point.setPosition([float(xyz[0]), float(xyz[1]), float(xyz[2].rstrip())])

        elif header[0] == "POLYGONS":
            for _ in range(int(header[1])):
                groups = next(line).split(";;")
                polygon = geo.createPolygon()
                for pointNum in map(int, groups[0].split(",")):
                    polygon.addVertex(geo.point(pointNum))

        elif header[0] == "UV":
            uv_attrib_name = header[1]
            uv_count = int(header[2])
            uvAttr = geo.addAttrib(hou.attribType.Vertex, uv_attrib_name, (0.0, 0.0, 0.0))
            uvAttr.setOption("type", "texturecoord")

            # Build a per-face vertex lookup: {face_index: {point_index: vertex}}
            face_vertex_map = {}
            for prim in geo.prims():
                face_vertex_map[prim.number()] = {
                    v.point().number(): v for v in prim.vertices()
                }

            for _ in range(uv_count):
                uv_entry = next(line).split(":")
                ply_idx = int(uv_entry[2])
                pnt_idx = int(uv_entry[4])
                uv_coords = uv_entry[0].split(" ")
                u, v_coord = float(uv_coords[0]), float(uv_coords[1])

                face_verts = face_vertex_map.get(ply_idx, {})
                if pnt_idx in face_verts:
                    face_verts[pnt_idx].setAttribValue(uvAttr, (u, v_coord, 0.0))

        elif header[0] == "VERTEXNORMALS":
            normalAttr = geo.addAttrib(hou.attribType.Point, "N", (0.0, 0.0, 0.0))
            normalAttr.setOption("type", "normal")
            for i in range(int(header[1])):
                # Fixed: use 'rgba' (the variable we actually read), not 'xyz'
                rgba = next(line).split(" ")
                geo.point(i).setAttribValue(normalAttr, (float(rgba[0]), float(rgba[1]), float(rgba[2].rstrip())))

        elif header[0] == "VERTEXCOLORS":
            default_rgba = header[2].split(" ") if len(header) > 2 else ["0.0", "0.0", "0.0", "1.0"]
            colorAttr = geo.addAttrib(
                hou.attribType.Point, "Cd",
                (float(default_rgba[0]), float(default_rgba[1]), float(default_rgba[2]), float(default_rgba[3]))
            )
            colorAttr.setOption("type", "color")
            for i in range(int(header[1])):
                rgba = next(line).split(" ")
                geo.point(i).setAttribValue(colorAttr, (float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3].rstrip())))

# Houdini stores faces in CW; the spec is CCW — reverse the winding on import
hou.sopNodeTypeCategory().nodeVerb("reverse").execute(geo, [geo])

node.geometry().merge(geo)
'''})

node.moveToGoodPosition()
hou.clearAllSelected()
node.setSelected(True)
