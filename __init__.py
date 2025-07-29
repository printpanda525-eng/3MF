bl_info = {
    "name": "Panda 3MF Import/Export",
    "author": "Panda Print",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Importa y exporta archivos 3MF",
    "category": "Import-Export",
}

import bpy
from .import_panda3mf import Import3MF
from .export_panda3mf import Export3MF

def menu_func_import(self, context):
    self.layout.operator(Import3MF.bl_idname, text="3MF (.3mf)")

def menu_func_export(self, context):
    self.layout.operator(Export3MF.bl_idname, text="3MF (.3mf)")

def register():
    bpy.utils.register_class(Import3MF)
    bpy.utils.register_class(Export3MF)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(Import3MF)
    bpy.utils.unregister_class(Export3MF)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
