import bpy
import bmesh
from mathutils import Vector, kdtree
from mathutils.geometry import intersect_point_line

from ..config import __addon_name__
from ..preference.AddonPreferences import ExampleAddonPreferences


# This Example Operator will scale up the selected object
class ExampleOperator(bpy.types.Operator):
    '''ExampleAddon'''
    bl_idname = "object.get_select_center"
    bl_label = "GetSelectCenter"

    bl_options = {'REGISTER', 'UNDO'}

    select_center_position = []

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.active_object is not None

    def execute(self, context: bpy.types.Context):
        addon_prefs = bpy.context.preferences.addons[__addon_name__].preferences
        assert isinstance(addon_prefs, ExampleAddonPreferences)

        obj = context.edit_object
        if obj == None:
            self.report({"ERROR"}, str("Not in EDIT mode"))
            return {"CANCELLED"}
        world_matrix = obj.matrix_world
        bm = bmesh.from_edit_mesh(obj.data)
        select_coords = [world_matrix @ v.co for v in bm.verts if v.select]
        if not select_coords:
            self.report({"ERROR"}, "No vertices selected")
            return {"CANCELLED"}

        center = Vector()
        for v in select_coords:
            center += v
        center /= len(select_coords)
        print(f"center_select_coords: {center}")

        # Store in scene custom properties
        if 'selection_centers' not in context.scene:
            context.scene['selection_centers'] = []

        centers = list(context.scene['selection_centers'])
        centers.append((center.x, center.y, center.z))
        context.scene['selection_centers'] = centers

        return {'FINISHED'}

class GenerateBonesOperator(bpy.types.Operator):
    '''ExampleAddon'''
    bl_idname = "object.generate_bones"
    bl_label = "GenerateBones"

    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.active_object is not None

    def execute(self, context: bpy.types.Context):
        # get select centers
        if 'selection_centers' not in context.scene or not context.scene['selection_centers']:
            self.report({'ERROR'}, "No selection centers stored. Run 'Get Selection Center' first.")
            return {'CANCELLED'}
        centers = [Vector(center) for center in context.scene['selection_centers']]
        print(f"Centers: {centers}")
        if len(centers) < 2:
            self.report({'ERROR'}, "Select centers number < 2")
            return {'CANCELLED'}

        # Create armature and bones
        armature_name = context.scene.armature_name
        armature_data = bpy.data.armatures.new(armature_name)
        armature_obj = bpy.data.objects.new(armature_name, armature_data)
        context.collection.objects.link(armature_obj)
        context.view_layer.objects.active = armature_obj
        armature_obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature_data.edit_bones

        bone_name = context.scene.bone_prefix

        bones = []
        bone_prev = edit_bones.new(f"{bone_name}00")
        bone_prev.head = centers[0]
        bone_prev.tail = centers[1]
        bones.append(bone_prev)
        for i in range(1, len(centers) - 1):
            bone = edit_bones.new(f"{bone_name}{i:02}")
            bone.head = centers[i]
            bone.tail = centers[i + 1]
            bone.parent = bone_prev
            bones.append(bone)
            bone_prev = bone
        bpy.ops.object.mode_set(mode='OBJECT')

        # clear selection_centers
        context.scene['selection_centers'] = []
        return {'FINISHED'}


class AssignWeightOperator(bpy.types.Operator):
    '''ExampleAddon'''
    bl_idname = "object.assign_weight"
    bl_label = "AssignWeight"

    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return (context.active_object is not None and
                context.active_object.mode == 'EDIT')

    def execute(self, context: bpy.types.Context):
        obj = context.edit_object
        scene = context.scene

        target_armature = scene.assign_weight_armature
        if not target_armature or target_armature.type != 'ARMATURE':
            self.report({'ERROR'}, "No valid armature selected!")
            return {'CANCELLED'}
        if "Armature" not in obj.modifiers:
            mod = obj.modifiers.new("Armature", 'ARMATURE')
            mod.object = target_armature
        else:
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE':
                    mod.object = target_armature

        bm = bmesh.from_edit_mesh(obj.data)
        deform_layer = bm.verts.layers.deform.verify()
        selected_verts = [v for v in bm.verts if v.select]

        bones = target_armature.data.bones
        bone_kd = kdtree.KDTree(len(bones))
        for i, bone in enumerate(bones):
            bone_kd.insert(target_armature.matrix_world @ bone.head_local, i)
        bone_kd.balance()

        for vg in obj.vertex_groups:
            if vg.name in [bone.name for bone in bones]:
                for vert in bm.verts:
                    if vg.index in vert[deform_layer]:
                        del vert[deform_layer][vg.index]

        for vert in selected_verts:
            world_co = obj.matrix_world @ vert.co
            co, bone_idx, dist = bone_kd.find(world_co)
            bones_to_check = {max(0, bone_idx - 1), min(bone_idx, len(bones) - 1)}

            for b_idx in bones_to_check:
                bone = bones[b_idx]
                bone_head = target_armature.matrix_world @ bone.head_local
                bone_tail = target_armature.matrix_world @ bone.tail_local

                pt, fac = intersect_point_line(world_co, bone_head, bone_tail)

                vg_name = bone.name
                vg = obj.vertex_groups.get(vg_name)
                if not vg:
                    vg = obj.vertex_groups.new(name=vg_name)
                if b_idx == len(bones) - 1 and fac > 0.5:
                    weight = 1.0
                else:
                    x = abs(fac - 0.5)
                    weight = -x + 1
                vert[deform_layer][vg.index] = weight

        bmesh.update_edit_mesh(obj.data)
        bm.free()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.vertex_group_normalize_all()
        return {'FINISHED'}