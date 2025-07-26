import os

import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy.types import AddonPreferences

from ..config import __addon_name__


class ExampleAddonPreferences(AddonPreferences):
    # this must match the add-on name (the folder name of the unzipped file)
    bl_idname = __addon_name__

    # https://docs.blender.org/api/current/bpy.props.html
    # The name can't be dynamically translated during blender programming running as they are defined
    # when the class is registered, i.e. we need to restart blender for the property name to be correctly translated.
    glb2fbx_input_filepath: StringProperty(
        name="GLB Folder",
        default=os.path.join(os.path.expanduser("~"), "Documents", __addon_name__),
        subtype='DIR_PATH',
    )
    refine_armature_input_filepath: StringProperty(
        name="Input Folder",
        default=os.path.join(os.path.expanduser("~"), "Documents", __addon_name__),
        subtype='DIR_PATH',
    )
    refine_armature_output_filepath: StringProperty(
        name="Ouput Folder",
        default=os.path.join(os.path.expanduser("~"), "Documents", __addon_name__),
        subtype='DIR_PATH',
    )

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.label(text="Add-on Preferences View")
        layout.prop(self, "glb2fbx_input_filepath")
        layout.prop(self, "refine_armature_input_filepath")
        layout.prop(self, "refine_armature_output_filepath")
