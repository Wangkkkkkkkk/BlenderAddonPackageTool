import bpy

from ..config import __addon_name__
from ..operators.AddonOperators import ExampleOperator, GenerateBonesOperator, AssignWeightOperator
from ....common.i18n.i18n import i18n
from ....common.types.framework import reg_order


class BasePanel(object):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ExampleAddon"

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True

@reg_order(0)
class ExampleAddonPanel(BasePanel, bpy.types.Panel):
    bl_label = "GenerateBone"
    bl_idname = "SCENE_PT_sample"

    def draw(self, context: bpy.types.Context):
        addon_prefs = context.preferences.addons[__addon_name__].preferences
        scene = context.scene
        layout = self.layout

        row = layout.row()
        row.label(text="Armature Name:")
        row.prop(scene, "armature_name", text="")
        row = layout.row()
        row.label(text="Bone Prefix:")
        row.prop(scene, "bone_prefix", text="")

        generate_split = layout.split(factor=0.5)
        generate_split.operator(ExampleOperator.bl_idname)
        generate_split.operator(GenerateBonesOperator.bl_idname)

        row = layout.row()
        row.label(text="Target Armature:")
        row.prop(scene, "assign_weight_armature", text="")
        layout.operator(AssignWeightOperator.bl_idname)

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True
