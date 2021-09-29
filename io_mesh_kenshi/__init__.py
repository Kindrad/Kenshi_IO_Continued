# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

"""
Name: 'OGRE for Kenshi (*.MESH)'
Blender: 2.80
Group: 'Import/Export'
Tooltip: 'Import/Export Kenshi OGRE mesh files'

Author: someone

Based on the Torchlight Impost/Export script by 'Dusho'

Also thanks to'goatman' for his port of Ogre export script from 2.49b to 2.5x,
and 'CCCenturion' for trying to refactor the code to be nicer (to be included)

last edited by Kindrad Oct-29-2021

"""

__author__ = "someone"
__version__ = "0.9.1 13-Sep-2019"

__bpydoc__ = """\
This script imports/exports Kenshi Ogre models into/from Blender.


Supported:<br>
    * import/export of basic meshes
    * import/export of skeleton
    * import/export of animations
    * import/export of vertex weights (ability to import characters and adjust rigs)
    * import/export of vertex colour (RGB)
    * import/export of vertex alpha (Uses second vertex colour layer called Alpha)
    * import/export of shape keys
    * Calculation of tangents and binormals for export


Known issues:<br>
    * imported materials will lose certain informations not applicable to Blender when exported

History:<br>
    * v0.9.1   (13-Sep-2019) - Fixed importing skeletons
    * v0.9.0   (07-May-2019) - Switched to Blender 2.80 API
    * v0.8.15  (17-Jul-2019) - Added option to import normals
    * v0.8.14  (14-May-2019) - Fixed blender deleting zero length bones
    * v0.8.13  (19-Mar-2019) - Exporting material files is optional
    * v0.8.12  (14-Mar-2019) - Fixed error exporting animation scale keyframes
    * v0.8.11  (26-Feb-2019) - Fixed tangents and binormals for mirrorred uvs
    * v0.8.10  (32-Jan-2019) - Fixed export when mesh has multiple uv sets
    * v0.8.9   (08-Mar-2018) - Added import option to match weight maps and link with a previously imported skeleton
    * v0.8.8   (26-feb-2018) - Fixed export triangulation and custom normals
    * v0.8.7   (01-Feb-2018) - Scene frame rate adjusted on import, Fixed quatenion normalisation
    * v0.8.6   (31-Jan-2018) - Fixed crash exporting animations in blender 2.79
    * v0.8.5   (02-Jan-2018) - Optimisation: Use hashmap for duplicate vertex detection
    * v0.8.4   (20-Nov-2017) - Fixed animation quaternion interpolation
    * v0.8.3   (06-Nov-2017) - Warning when linked skeleton file not found
    * v0.8.2   (25-Sep-2017) - Fixed bone translations in animations
    * v0.8.1   (28-Jul-2017) - Added alpha component to vertex colour
    * v0.8.0   (30-Jun-2017) - Added animation and shape key support. Rewritten skeleton export
    * v0.7.2   (08-Dec-2016) - fixed divide by 0 error calculating tangents
    * v0.7.1   (07-Sep-2016) - bug fixes
    * v0.7.0   (02-Sep-2016) - Implemented changes needed for Kenshi: Persistant Ogre bone IDs, Export vertex colours. Generates tangents and binormals.
    * v0.6.2   (09-Mar-2013) - bug fixes (working with materials+textures), added 'Apply modifiers' and 'Copy textures'
    * v0.6.1   (27-Sep-2012) - updated to work with Blender 2.63a
    * v0.6     (01-Sep-2012) - added skeleton import + vertex weights import/export
    * v0.5     (06-Mar-2012) - added material import/export
    * v0.4.1   (29-Feb-2012) - flag for applying transformation, default=true
    * v0.4     (28-Feb-2012) - fixing export when no UV data are present
    * v0.3     (22-Feb-2012) - WIP - started cleaning + using OgreXMLConverter
    * v0.2     (19-Feb-2012) - WIP - working export of geometry and faces
    * v0.1     (18-Feb-2012) - initial 2.59 import code (from .xml)
    * v0.0     (12-Feb-2012) - file created
"""

bl_info = {
    "name": "Kenshi Tools",
    "author": "someone",
    "blender": (2, 80, 0),
    "version": (0, 9, 1),
    "location": "File > Import-Export",
    "description": ("Import-Export Kenshi Model files, and export Kenshi collision files."),
    "warning": "",
    "wiki_url": "",
    "tracker_url": "http://lofigames.com/phpBB3/",
    "support": 'OFFICIAL',
    "category": "Import-Export"}

if "bpy" in locals():
    import imp
    if "OgreImport" in locals():
        imp.reload(OgreImport)
    if "OgreExport" in locals():
        imp.reload(OgreExport)
    if "PhysExport" in locals():
        imp.reload(PhysExport)

import bpy
from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       )
from bpy_extras.io_utils import (ExportHelper,
                                 ImportHelper,
                                 path_reference_mode,
                                 axis_conversion,
                                 )


# Path for your OgreXmlConverter
OGRE_XML_CONVERTER = "OgreXMLConverter.exe"

def findConverter(p):
    import os

    # Full path exists
    if os.path.isfile(p): return p

    # Look in script directory
    scriptPath = os.path.dirname( os.path.realpath( __file__ ) )
    sp = os.path.join(scriptPath, p)
    if os.path.isfile(sp): return sp

    # Fail
    print('Could not find xml converter', p)
    return None



class ImportOgre(bpy.types.Operator, ImportHelper):
    '''Load an Ogre MESH File'''
    bl_idname = "import_scene.mesh"
    bl_label = "Import MESH"
    bl_options = {'PRESET'}

    filename_ext = ".mesh"


    keep_xml: BoolProperty(
            name="Keep XML",
            description="Keeps the XML file when converting from .MESH",
            default=False,
            )
    
    import_normals: BoolProperty(
            name="Import Normals",
            description="Import custom mesh normals",
            default=True,
            )

    import_animations: BoolProperty(
            name="Import animation",
            description="Import animations as actions",
            default=True,
            )

    round_frames: BoolProperty(
            name="Adjust frame rate",
            description="Adjust scene frame rate to match imported animation",
            default=True,
            )
            
    import_shapekeys: BoolProperty(
            name="Import shape keys",
            description="Import shape keys (morphs)",
            default=True,
            )
    
    use_selected_skeleton: BoolProperty(
            name='Use selected skeleton',
            description='Link with selected armature object rather than importing a skeleton.\nUse this for importing skinned meshes that don\'t have their own skeleton.\nMake sure you have the correct skeleton selected or the weight maps may get mixed up.',
            default=False,
            )

    filter_glob: StringProperty(
            default="*.mesh;*.MESH;.xml;.XML",
            options={'HIDDEN'},
            )

    xml_converter: StringProperty(
            name="XML Converter",
            description="Ogre XML Converter program for converting between .MESH files and .XML files",
            default=OGRE_XML_CONVERTER
            )


    def execute(self, context):
        # print("Selected: " + context.active_object.name)
        from . import OgreImport

        keywords = self.as_keywords(ignore=("filter_glob",))
        keywords['xml_converter'] = findConverter( keywords['xml_converter'] )

        print( 'converter', keywords['xml_converter'])

        bpy.context.window.cursor_set("WAIT")
        result = OgreImport.load(self, context, **keywords)
        bpy.context.window.cursor_set("DEFAULT")
        return result

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "xml_converter")
        layout.prop(self, "keep_xml")
        layout.prop(self, "import_normals")
        layout.prop(self, "import_shapekeys")
        
        link = layout.column()
        link.enabled = True if context.active_object and context.active_object.type == 'ARMATURE' else False
        link.prop(self, "use_selected_skeleton")

        layout.prop(self, "import_animations")

        rate = layout.column()
        rate.enabled = self.import_animations
        rate.prop(self, "round_frames")

##############################################################################################################################

class ExportOgre(bpy.types.Operator, ExportHelper):
    '''Export a Kenshi MESH File'''

    bl_idname = "export_scene.mesh"
    bl_label = 'Export MESH'
    bl_options = {'PRESET'}

    filename_ext = ".mesh"

    xml_converter: StringProperty(
            name="XML Converter",
            description="Ogre XML Converter program for converting between .MESH files and .XML files",
            default=OGRE_XML_CONVERTER,
            )

    export_tangents: BoolProperty(
            name="Export tangents",
            description="Export tangent data for the mesh",
            default=True,
            )
    tangent_parity: BoolProperty(
            name="   Parity in W",
            description="Tangents have parity stored in the W component",
            default=False,
            )

    export_binormals: BoolProperty(
            name="Export Binormals",
            description="Generate binormals for the mesh",
            default=False,
            )

    export_colour: BoolProperty(
            name="Export colour",
            description="Export vertex colour data. Name a colour layer 'Alpha' to use as the alpha component",
            default=False,
            )

    keep_xml: BoolProperty(
            name="Keep XML",
            description="Keeps the XML file when converting to .MESH",
            default=False,
            )

    apply_transform: BoolProperty(
            name="Apply Transform",
            description="Applies object's transformation to its data",
            default=False,
            )

    apply_modifiers: BoolProperty(
            name="Apply Modifiers",
            description="Applies modifiers to the mesh",
            default=False,
            )

    export_poses: BoolProperty(
            name="Export shape keys",
            description="Export shape keys as poses",
            default=False,
            )

    export_materials: BoolProperty(
            name="Export materials",
            description="Export material files. Kenshi does not use these",
            default=False,
            )

    overwrite_material: BoolProperty(
            name="Overwrite material",
            description="Overwrites existing .material file, if present.",
            default=False,
            )

    copy_textures: BoolProperty(
            name="Copy textures",
            description="Copies material source textures to material file location",
            default=False,
            )

    export_skeleton: BoolProperty(
            name="Export skeleton",
            description="Exports new skeleton and links the mesh to this new skeleton.\nLeave off to link with existing skeleton if applicable.",
            default=False,
            )

    export_animation: BoolProperty(
            name="Export Animation",
            description="Export all actions attached to the selected skeleton as animations",
            default=False,
            )

    batch_export: BoolProperty(
            name="Batch Export",
            description="Export individual meshes as unique files based on blender object name",
            default=False,
            )

    filter_glob: StringProperty(
            default="*.mesh;*.MESH;.xml;.XML",
            options={'HIDDEN'},
            )

    def invoke(self, context, event):
        #if not self.filepath:
        #    self.filepath = bpy.path.ensure_ext(bpy.data.filepath, ".bm")

        

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from . import OgreExport
        from mathutils import Matrix

        keywords = self.as_keywords(ignore=("check_existing", "filter_glob"))
        keywords['xml_converter'] = findConverter( keywords['xml_converter'] )
        
        bpy.context.window.cursor_set("WAIT")
        result = OgreExport.save(self, context, **keywords)
        bpy.context.window.cursor_set("DEFAULT")
        return result


    def draw(self, context):
        layout = self.layout

        xml = layout.box()
        xml.prop(self, "xml_converter")
        xml.prop(self, "keep_xml")
        
        mesh = layout.box()
        mesh.prop(self, "export_tangents")
        mesh.prop(self, "export_binormals")
        mesh.prop(self, "export_colour")
        mesh.prop(self, "export_poses")
        mesh.prop(self, "apply_transform")
        mesh.prop(self, "apply_modifiers")

        material = layout.box()
        material.prop(self, "export_materials")
        materialOps = material.column()
        materialOps.prop(self, "overwrite_material")
        materialOps.prop(self, "copy_textures")
        materialOps.enabled = False

        skeleton = layout.box()
        skeleton.prop(self, "export_skeleton")
        skeleton.prop(self, "export_animation")

        batch = layout.box()
        batch.prop(self, "batch_export")

##############################################################################################################################

class ExportKenshiCollision(bpy.types.Operator, ExportHelper):
    '''Export a Kenshi MESH File'''

    bl_idname = "export_scene_collision.xml"
    bl_label = 'Export Collision'
    bl_options = {'PRESET'}
    filename_ext = ".xml"

    objects: EnumProperty(
            name="Objects",
            description="Which objects to export",
            items=[('ALL', 'All Objects', 'Export all collision objects in the scene'),
                    ('SELECTED', 'Selection', 'Export only selected objects'),
                    ('CHILDREN', 'Selected Children', 'Export selected objects and all their child objects')],
            default='CHILDREN',
            )
    transform: EnumProperty(
            name="Transform",
            description="Root transformation",
            items=[('SCENE', 'Scene', 'Export objects relative to scene origin'),
                    ('PARENT', 'Parent', 'Export objects relative to common parent'),
                    ('ACTIVE', 'Active', 'Export objects relative to the active object')],
            default='PARENT',
            )

    filter_glob: StringProperty(
            default="*.xml;*.XML",
            options={'HIDDEN'},
            )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from . import PhysExport
        keywords = self.as_keywords(ignore=("check_existing", "filter_glob"))
        bpy.context.window.cursor_set("WAIT")
        result = PhysExport.save(self, context, **keywords)
        bpy.context.window.cursor_set("DEFAULT")
        return result


    def draw(self, context):
        layout = self.layout
        layout.prop(self, "objects")
        layout.prop(self, "transform")

##############################################################################################################################

def menu_func_import(self, context):
    self.layout.operator(ImportOgre.bl_idname, text="Kenshi OGRE (.mesh)")


def menu_func_export(self, context):
    self.layout.operator(ExportOgre.bl_idname, text="Kenshi OGRE (.mesh)")

def menu_func_export_collision(self, context):
    self.layout.operator(ExportKenshiCollision.bl_idname, text="Kenshi Collision (.xml)")


classes = ( ImportOgre, ExportOgre, ExportKenshiCollision )

def register():
    from bpy.utils import register_class
    for cls in classes: register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_collision)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes): unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export_collision)

if __name__ == "__main__":
    register()
