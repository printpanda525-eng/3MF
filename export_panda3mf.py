import bpy
import zipfile
import xml.etree.ElementTree as ET
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
import bmesh

class Export3MF(Operator, ExportHelper):
    bl_idname = "export_mesh.panda3mf"
    bl_label = "Export Panda 3MF"
    bl_options = {'PRESET'}
    filename_ext = ".3mf"
    filter_glob: bpy.props.StringProperty(default="*.3mf", options={'HIDDEN'})

    def execute(self, context):
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'ERROR'}, "Selecciona al menos un objeto tipo malla.")
            return {'CANCELLED'}

        model_ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
        ET.register_namespace('', model_ns)

        model = ET.Element("{%s}model" % model_ns, attrib={"unit": "millimeter"})
        resources = ET.SubElement(model, "resources")
        build = ET.SubElement(model, "build")

        for idx, obj in enumerate(mesh_objects, start=1):
            depsgraph = context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()

            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            bm.to_mesh(mesh)
            bm.free()

            object_elem = ET.SubElement(resources, "object", attrib={
                "id": str(idx),
                "pid": "1",
                "type": "model",
                "name": obj.name
            })

            mesh_elem = ET.SubElement(object_elem, "mesh")
            vertices_elem = ET.SubElement(mesh_elem, "vertices")
            triangles_elem = ET.SubElement(mesh_elem, "triangles")

            for v in mesh.vertices:
                ET.SubElement(vertices_elem, "vertex", attrib={
                    "x": format(v.co.x, '.6f'),
                    "y": format(v.co.y, '.6f'),
                    "z": format(v.co.z, '.6f')
                })

            for poly in mesh.polygons:
                if len(poly.vertices) == 3:
                    verts = poly.vertices
                    ET.SubElement(triangles_elem, "triangle", attrib={
                        "v1": str(verts[0]),
                        "v2": str(verts[1]),
                        "v3": str(verts[2])
                    })

            ET.SubElement(build, "item", attrib={"objectid": str(idx)})

            eval_obj.to_mesh_clear()

        xml_bytes = ET.tostring(model, encoding='utf-8', xml_declaration=True)

        content_types = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>'''

        rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model"/>
</Relationships>'''

        try:
            with zipfile.ZipFile(self.filepath, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("3D/3dmodel.model", xml_bytes)
                archive.writestr("[Content_Types].xml", content_types)
                archive.writestr("_rels/.rels", rels)
        except Exception as e:
            self.report({'ERROR'}, f"Error escribiendo archivo 3MF: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, "Exportación 3MF compatible con slicers completada.")
        return {'FINISHED'}
