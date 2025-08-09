import bpy
from bpy.props import PointerProperty, EnumProperty
from bpy.types import PropertyGroup, Panel

from ..config import __addon_name__
from ..operators.AddonOperators import (
    GetSelectVertexOperator,
    CancelSelectVertexOperator,
    GenerateBonesOperator,
    AssignWeightOperator
)
from ....common.i18n.i18n import i18n
from ....common.types.framework import reg_order


def _bone_items(self, context):
    # 永远提供一个“无父骨”选项，避免空列表导致 UI 报错
    items = [('NONE', 'None', 'No parent bone', 'X', 0)]
    arm_obj = getattr(self, "Select_armature", None)
    if arm_obj and arm_obj.type == 'ARMATURE' and arm_obj.data:
        # 使用 Armature 的 data.bones（不是 pose bones）
        for i, b in enumerate(arm_obj.data.bones, start=1):
            items.append((b.name, b.name, "", 'BONE_DATA', i))
    return items


def _on_armature_change(self, context):
    # 切换目标骨架时，重置父骨为 None
    self.Select_parent_bone = 'NONE'

class ArmatureSelectorProperties(PropertyGroup):
    Select_armature: PointerProperty(
        name="Select Armature",
        description="Select the armature to be processed",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE',
        update=_on_armature_change,
    )
    Select_parent_bone: EnumProperty(
        name="Select Parent Bone",
        description="Select the parent bone to be processed",
        items=_bone_items,
    )


class BasePanel(object):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "RibbonAnimation"

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
        addon_props = scene.armature_select_props
        # select armature
        generate_bones_box_armature_row = generate_bones_box.row()
        generate_bones_box_armature_row.label(text="Select Armature:")
        generate_bones_box_armature_row.prop(addon_props, "Select_armature", text="", icon='ARMATURE_DATA')
        # select parent bone
        generate_bones_box_bone_row = generate_bones_box.row()
        generate_bones_box_bone_row.enabled = bool(getattr(addon_props, "Select_armature", None))
        generate_bones_box_bone_row.label(text="Select Parent Bone:")
        generate_bones_box_bone_row.prop(addon_props, "Select_parent_bone", text="", icon='BONE_DATA')
        # bone prefix
        generate_bones_box_prefix_row = generate_bones_box.row()
        generate_bones_box_prefix_row.label(text="Bone Prefix:")
        generate_bones_box_prefix_row.prop(scene, "bone_prefix", text="")
        generate_bones_box.operator(GenerateBonesOperator.bl_idname)

        # assign weight box
        assign_weight_box = layout.box()
        assign_weight_box.label(text="Step 3: Edit mode select vertex to assign weight")
        assign_weight_box_row = assign_weight_box.row()
        assign_weight_box_row.label(text="Target Armature:")
        assign_weight_box_row.prop(scene, "assign_weight_armature", text="", icon='ARMATURE_DATA')
        assign_weight_box.operator(AssignWeightOperator.bl_idname)

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True
