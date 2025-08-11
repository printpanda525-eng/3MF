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
        ns = "{%s}" % model_ns

        def rgba_to_hex_with_alpha(color):
            r, g, b, a = color
            ri = max(0, min(255, int(round(r * 255))))
            gi = max(0, min(255, int(round(g * 255))))
            bi = max(0, min(255, int(round(b * 255))))
            ai = max(0, min(255, int(round(a * 255))))
            return f"#{ri:02X}{gi:02X}{bi:02X}{ai:02X}"

        def get_material_color(mat):
            color = (1.0, 1.0, 1.0, 1.0)
            if mat is None:
                return color
            if mat.use_nodes and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.bl_idname == "ShaderNodeBsdfPrincipled":
                        try:
                            val = node.inputs.get("Base Color")
                            if val is not None:
                                dv = val.default_value
                                if isinstance(dv, (tuple, list)) and len(dv) >= 3:
                                    a = dv[3] if len(dv) > 3 else 1.0
                                    return (dv[0], dv[1], dv[2], a)
                        except Exception:
                            pass
            if hasattr(mat, "diffuse_color"):
                dv = mat.diffuse_color
                if isinstance(dv, (tuple, list)) and len(dv) >= 3:
                    a = dv[3] if len(dv) > 3 else 1.0
                    return (dv[0], dv[1], dv[2], a)
            return color

        model = ET.Element(ns + "model", attrib={"unit": "millimeter"})
        resources = ET.SubElement(model, ns + "resources")
        build = ET.SubElement(model, ns + "build")
        components = ET.SubElement(model, ns + "components")  # NUEVO: componentes para ensamblaje

        base_materials = ET.SubElement(resources, ns + "basematerials", attrib={"id": "1"})

        material_map = {}
        material_list = []

        for obj in mesh_objects:
            for mat in obj.data.materials:
                if mat is None:
                    continue
                if mat.name not in material_map:
                    idx = len(material_map)
                    material_map[mat.name] = idx
                    material_list.append(mat)
                    col = get_material_color(mat)
                    hexcol = rgba_to_hex_with_alpha(col)
                    ET.SubElement(base_materials, ns + "base", attrib={
                        "name": mat.name,
                        "displaycolor": hexcol
                    })

        if not material_list:
            material_map["__default_white__"] = 0
            material_list.append(None)
            ET.SubElement(base_materials, ns + "base", attrib={
                "name": "DefaultWhite",
                "displaycolor": "#FFFFFFFF"
            })

        object_id_counter = 1

        for obj in mesh_objects:
            depsgraph = context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()

            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            bm.to_mesh(mesh)
            bm.free()

            faces_by_matname = {}
            for poly in mesh.polygons:
                midx = poly.material_index
                mat = mesh.materials[midx] if midx < len(mesh.materials) else None
                mat_name = mat.name if mat else "__default_white__"
                faces_by_matname.setdefault(mat_name, []).append(poly)

            for mat_name, faces in faces_by_matname.items():
                mat_index = material_map.get(mat_name, 0)
                object_elem = ET.SubElement(resources, ns + "object", attrib={
                    "id": str(object_id_counter),
                    "type": "model",
                    "name": f"{obj.name}_{mat_name}",
                    "pid": "1",
                    "pindex": str(mat_index)
                })

                mesh_elem = ET.SubElement(object_elem, ns + "mesh")
                vertices_elem = ET.SubElement(mesh_elem, ns + "vertices")
                triangles_elem = ET.SubElement(mesh_elem, ns + "triangles")

                vert_map = {}
                new_idx = 0
                for face in faces:
                    for vid in face.vertices:
                        if vid not in vert_map:
                            v = mesh.vertices[vid]
                            vert_map[vid] = new_idx
                            new_idx += 1
                            ET.SubElement(vertices_elem, ns + "vertex", attrib={
                                "x": format(v.co.x, '.6f'),
                                "y": format(v.co.y, '.6f'),
                                "z": format(v.co.z, '.6f')
                            })

                for face in faces:
                    rem = [vert_map[vid] for vid in face.vertices]
                    ET.SubElement(triangles_elem, ns + "triangle", attrib={
                        "v1": str(rem[0]),
                        "v2": str(rem[1]),
                        "v3": str(rem[2])
                    })

                # Agregar componente para este objeto con transform identidad
                ET.SubElement(components, ns + "component", attrib={
                    "objectid": str(object_id_counter),
                    "transform": "1 0 0 0 1 0 0 0 1 0 0 0"
                })

                # Agregar item en build para referenciar el componente
                ET.SubElement(build, ns + "item", attrib={
                    "objectid": str(object_id_counter),
                    "componentid": str(object_id_counter)
                })

                object_id_counter += 1

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

        self.report({'INFO'}, "Exportación 3MF completada")
        return {'FINISHED'}
