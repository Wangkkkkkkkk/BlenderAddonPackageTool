import bpy
from bpy.props import PointerProperty
from bpy.types import PropertyGroup, Panel

from ..config import __addon_name__
from ..operators.AddonOperators import (
    Glb2fbxOperator,
    RefineArmatureOperator,
    AddConstraintOperator,
    DeleteConstraintOperator
)
from ....common.i18n.i18n import i18n
from ....common.types.framework import reg_order

class ArmatureSelectorProperties(PropertyGroup):
    target_armature: PointerProperty(
        name="Target Armature",
        description="Select the armature to be processed",
        type=bpy.types.Object,
        # poll 函数用于过滤下拉列表，只显示骨架类型的对象
        poll=lambda self, obj: obj.type == 'ARMATURE',
    )
    source_armature: PointerProperty(
        name="Source Armature",
        description="Select the armature to be processed",
        type=bpy.types.Object,
        # poll 函数用于过滤下拉列表，只显示骨架类型的对象
        poll=lambda self, obj: obj.type == 'ARMATURE',
    )

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
        glb2fbx_box.operator(Glb2fbxOperator.bl_idname)

        refine_armature_box = layout.box()
        refine_armature_box.label(
            text=i18n("Input .fbx filepath, output refine .fbx file"))
        refine_armature_box.prop(
            addon_prefs, "refine_armature_input_filepath")
        refine_armature_box.prop(
            addon_prefs, "refine_armature_output_filepath")
        refine_armature_box.operator(RefineArmatureOperator.bl_idname)

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True

@reg_order(1)
class ExampleAddonPanel2(BasePanel, bpy.types.Panel):
    bl_label = "AddConstraint"
    bl_idname = "SCENE_PT_sample2"

    def draw(self, context: bpy.types.Context):
        addon_prefs = context.preferences.addons[__addon_name__].preferences
        scene = context.scene
        addon_props = scene.armature_select_props

        layout = self.layout

        add_constrain_box = layout.box()
        add_constrain_box.label(
            text=i18n("Target armature add constrain to source armature"))
        add_constrain_box.prop(addon_props, "target_armature", text="Target", icon='ARMATURE_DATA')
        add_constrain_box.prop(addon_props, "source_armature", text="Source", icon='ARMATURE_DATA')
        button_row = add_constrain_box.row()
        button_row.operator(AddConstraintOperator.bl_idname)
        button_row.operator(DeleteConstraintOperator.bl_idname)