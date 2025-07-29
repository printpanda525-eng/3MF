import bpy
import zipfile
import xml.etree.ElementTree as ET
from bpy_extras.io_utils import ImportHelper

class Import3MF(bpy.types.Operator, ImportHelper):
    bl_idname = "import_mesh.panda3mf"
    bl_label = "Import Panda 3MF"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".3mf"
    filter_glob: bpy.props.StringProperty(default="*.3mf", options={'HIDDEN'})

    def execute(self, context):
        if not zipfile.is_zipfile(self.filepath):
            self.report({'ERROR'}, "El archivo .3mf no es un ZIP válido.")
            return {'CANCELLED'}

        with zipfile.ZipFile(self.filepath, 'r') as archive:
            model_path = "3D/3dmodel.model"
            if model_path not in archive.namelist():
                self.report({'ERROR'}, "No se encontró el archivo 3D/3dmodel.model en el .3mf.")
                return {'CANCELLED'}

            xml_data = archive.read(model_path)
            root = ET.fromstring(xml_data)

            ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
            for idx, object_tag in enumerate(root.findall(".//m:object", ns)):
                mesh_tag = object_tag.find("m:mesh", ns)
                if mesh_tag is None:
                    continue

                vertices = []
                for vertex in mesh_tag.findall("m:vertices/m:vertex", ns):
                    x = float(vertex.attrib.get("x", "0"))
                    y = float(vertex.attrib.get("y", "0"))
                    z = float(vertex.attrib.get("z", "0"))
                    vertices.append((x, y, z))

                faces = []
                for triangle in mesh_tag.findall("m:triangles/m:triangle", ns):
                    v1 = int(triangle.attrib.get("v1", 0))
                    v2 = int(triangle.attrib.get("v2", 0))
                    v3 = int(triangle.attrib.get("v3", 0))
                    faces.append((v1, v2, v3))

                mesh = bpy.data.meshes.new(f"Imported_3MF_{idx}")
                mesh.from_pydata(vertices, [], faces)
                mesh.update()

                obj = bpy.data.objects.new(f"Imported_3MF_{idx}", mesh)
                context.collection.objects.link(obj)
                obj.select_set(True)

        self.report({'INFO'}, "Importación completa.")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(Import3MF)

def unregister():
    bpy.utils.unregister_class(Import3MF)
