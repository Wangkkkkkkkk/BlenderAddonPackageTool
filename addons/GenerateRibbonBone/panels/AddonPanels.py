import bpy

from ..config import __addon_name__
from ..operators.AddonOperators import (
    GetSelectVertexOperator,
    CancelSelectVertexOperator,
    GenerateBonesOperator,
    AssignWeightOperator
)
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

        # select vertex box
        select_vertex_box = layout.box()
        select_vertex_box.label(text="Step 1: Edit mode select vertex")
        select_vertex_box_split = select_vertex_box.split(factor=0.5)
        select_vertex_box_split.operator(GetSelectVertexOperator.bl_idname)
        select_vertex_box_split.operator(CancelSelectVertexOperator.bl_idname)
        select_vertex_box.label(text=f"Selected vertex count: {scene.selected_vertex_count}")

        # generate bones box
        generate_bones_box = layout.box()
        generate_bones_box.label(text="Step 2: Generate bones by select vertex")
        generate_bones_box_armature_row = generate_bones_box.row()
        generate_bones_box_armature_row.label(text="Armature Name:")
        generate_bones_box_armature_row.prop(scene, "armature_name", text="")
        generate_bones_box_bone_row = generate_bones_box.row()
        generate_bones_box_bone_row.label(text="Bone Prefix:")
        generate_bones_box_bone_row.prop(scene, "bone_prefix", text="")
        generate_bones_box.operator(GenerateBonesOperator.bl_idname)

        # assign weight box
        assign_weight_box = layout.box()
        assign_weight_box.label(text="Step 3: Edit mode select vertex to assign weight")
        assign_weight_box_row = assign_weight_box.row()
        assign_weight_box_row.label(text="Target Armature:")
        assign_weight_box_row.prop(scene, "assign_weight_armature", text="")
        assign_weight_box.operator(AssignWeightOperator.bl_idname)

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True
