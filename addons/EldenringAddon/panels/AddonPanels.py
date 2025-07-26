import bpy

from ..config import __addon_name__
from ..operators.AddonOperators import (
    Glb2fbxOperator,
    RefineArmatureOperator
)
from ....common.i18n.i18n import i18n
from ....common.types.framework import reg_order


class BasePanel(object):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "EldenringAddon"

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True


@reg_order(0)
class ExampleAddonPanel(BasePanel, bpy.types.Panel):
    bl_label = "ExtractAnimation"
    bl_idname = "SCENE_PT_sample"

    def draw(self, context: bpy.types.Context):
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        layout = self.layout

        glb2fbx_box = layout.box()
        glb2fbx_box.label(
            text=i18n("Input .glb filepath, output .fbx file"))
        glb2fbx_box.prop(
            addon_prefs, "glb2fbx_input_filepath")
        glb2fbx_box.separator()
        glb2fbx_box.operator(Glb2fbxOperator.bl_idname)

        refine_armature_box = layout.box()
        refine_armature_box.label(
            text=i18n("Input .fbx filepath, output refine .fbx file"))
        refine_armature_box.prop(
            addon_prefs, "refine_armature_input_filepath")
        refine_armature_box.separator()
        refine_armature_box.prop(
            addon_prefs, "refine_armature_output_filepath")
        refine_armature_box.separator()
        refine_armature_box.operator(RefineArmatureOperator.bl_idname)

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True


