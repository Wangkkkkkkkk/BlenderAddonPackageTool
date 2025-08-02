import bpy
import os

from bpy.ops import scene

from ..config import __addon_name__
from ..preference.AddonPreferences import ExampleAddonPreferences


class Glb2fbxOperator(bpy.types.Operator):
    bl_idname = "object.glb2fbx_ops"
    bl_label = "glb_to_fbx"

    bl_options = {'REGISTER', 'UNDO'}

    def remove_armature(self, armature_name):
        """glb to fbx remove already export fbx armature"""
        armature_objs = [
            obj for obj in bpy.data.objects
            if obj.type == 'ARMATURE' and obj.name == armature_name
        ]
        for armature_obj in armature_objs:
            mesh_objs = [
                child for child in armature_obj.children
                if child.type == 'MESH'
            ]
            for mesh_obj in mesh_objs:
                bpy.data.objects.remove(mesh_obj, do_unlink=True)
            bpy.data.objects.remove(armature_obj, do_unlink=True)

    def import_glb(self, filepath, armature_name):
        """by filepath import glb armature"""
        self.remove_armature(armature_name)
        bpy.ops.import_scene.gltf(filepath=filepath)
        armature_obj = next(
            (obj for obj in bpy.context.selected_objects
             if obj.type == 'ARMATURE'),
            None
        )
        if armature_obj:
            armature_obj.name = armature_name
            armature_obj.data.name = f"{armature_name}_Data"

    def export_fbx_skeleton(self, filepath, armature_name):
        """glb armature to fbx skeleton"""
        scene = bpy.context.scene
        scene.frame_set(0)

        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # deselect all object
        bpy.ops.object.select_all(action='DESELECT')

        # fing name Armature
        armature_obj = bpy.data.objects.get(armature_name)

        if not armature_obj or armature_obj.type != 'ARMATURE':
            raise ValueError(f"未找到 Armature: {armature_name}")

        # select Armature
        armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = armature_obj

        # export armature
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,  # 仅导出选中的对象
            object_types={'ARMATURE'},  # 仅导出 Armature 类型
            use_mesh_modifiers=False,  # 不应用 Mesh 修改器（因为不导出 Mesh）

            bake_anim=True,  # 启用动画导出
            bake_anim_use_all_bones=True,  # 导出所有骨骼的动画
            bake_anim_use_nla_strips=False,  # 禁用NLA strips（直接导出Action）
            bake_anim_use_all_actions=False,  # 仅导出当前Action
            bake_anim_force_startend_keying=False,  # 强制使用时间轴范围
            bake_anim_step=1.0,  # 每帧采样

            add_leaf_bones=False,  # 不添加叶子骨骼
            armature_nodetype='NULL',  # 骨骼节点类型（保持默认）
            bake_space_transform=True,  # 应用变换
            use_armature_deform_only=True,  # 仅导出用于变形的骨骼
        )

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True

    def execute(self, context: bpy.types.Context):
        addon_prefs = bpy.context.preferences.addons[__addon_name__].preferences
        assert isinstance(addon_prefs, ExampleAddonPreferences)

        source_filepath = addon_prefs.glb2fbx_input_filepath
        print("Glb2fbxOperator== source_filepath:", source_filepath)

        for file_name in os.listdir(source_filepath):
            if ".glb" not in file_name:
                continue
            file_path = os.path.join(source_filepath, file_name)
            glb_name = file_name.split('.')[0]
            self.import_glb(file_path, glb_name)
            fbx_path = file_path.replace(".glb", ".fbx")
            self.export_fbx_skeleton(fbx_path, glb_name)
            self.remove_armature(glb_name)
        return {'FINISHED'}


class RefineArmatureOperator(bpy.types.Operator):
    bl_idname = "object.refine_armature_ops"
    bl_label = "refine_armature"

    bl_options = {'REGISTER', 'UNDO'}

    # add constrains and link them with target bones
    def add_constraints(self, source, target):

        source_ob = bpy.data.objects[source]

        for bone in source_ob.pose.bones:
            sel_bone = source_ob.data.bones[bone.name]
            sel_bone.select = True
            bpy.context.object.data.bones.active = sel_bone

            trans_bone = bpy.context.object.pose.bones[bone.name]
            if trans_bone.constraints.find('Copy Transforms') == -1:
                if bpy.data.objects[target].pose.bones.get(bone.name) is not None:
                    bpy.ops.pose.constraint_add(type='COPY_TRANSFORMS')
                    trans_bone.constraints["Copy Transforms"].target = bpy.data.objects[target]
                    trans_bone.constraints["Copy Transforms"].subtarget = bone.name

    # delete previously created constrains
    def del_constraints(self):
        for bone in bpy.context.selected_pose_bones:
            copyLocConstraints = [c for c in bone.constraints if c.type == 'COPY_TRANSFORMS']
            # Iterate over all the bone's copy location constraints and delete them all
            for c in copyLocConstraints:
                bone.constraints.remove(c)  # Remove constraint

    def apply_animation(self, source, target):
        # set keying set to whole character
        # we have all bones selected
        scene = bpy.context.scene

        target_armature = bpy.data.objects[target]
        if target_armature.animation_data and target_armature.animation_data.action:
            target_action = target_armature.animation_data.action
            start_frame = int(target_action.frame_range[0])
            end_frame = int(target_action.frame_range[1])
        else:
            return False

        # set source armature frame 0 to rest pose
        source_armature = bpy.data.objects[source]
        bpy.context.view_layer.objects.active = source_armature
        bpy.ops.object.mode_set(mode='POSE')
        for pbone in source_armature.pose.bones:
            pbone.location = (0, 0, 0)
            pbone.rotation_quaternion = (1, 0, 0, 0)
            pbone.rotation_euler = (0, 0, 0)
            pbone.scale = (1, 1, 1)
        scene.frame_current = 0
        scene.frame_set(0)
        for pbone in source_armature.pose.bones:
            pbone.keyframe_insert(data_path="location", frame=0)
            pbone.keyframe_insert(data_path="rotation_quaternion", frame=0)
            pbone.keyframe_insert(data_path="rotation_euler", frame=0)
            pbone.keyframe_insert(data_path="scale", frame=0)

        for frame in range(1, end_frame):
            scene.frame_current = frame
            scene.frame_set(scene.frame_current)
            # apply visual transfrom to pose Ctrl+A
            bpy.ops.pose.visual_transform_apply()
            # insert all keyframes -> press I
            bpy.ops.anim.keyframe_insert_menu(type='__ACTIVE__')
        return True

    def select_all_bones(self, source):
        ob = bpy.data.objects[source]
        for bone in ob.pose.bones:
            b = ob.data.bones[bone.name]
            b.select = True
            bpy.context.object.data.bones.active = b

    def remove_armature(self, armature_name):
        armature_objs = [
            obj for obj in bpy.data.objects
            if obj.type == 'ARMATURE' and obj.name == armature_name
        ]
        for armature_obj in armature_objs:
            mesh_objs = [
                child for child in armature_obj.children
                if child.type == 'MESH'
            ]
            for mesh_obj in mesh_objs:
                bpy.data.objects.remove(mesh_obj, do_unlink=True)
            bpy.data.objects.remove(armature_obj, do_unlink=True)

    def import_fbx_animation(
            self,
            filepath,
            armature_name,
            rotation=(0, 0, 0)
    ):
        """import FBX armature animation"""
        if not os.path.exists(filepath):
            print(f"error: can't find - {filepath}")
            return False

        if not filepath.lower().endswith('.fbx'):
            print("error: file is FBX")
            return False

        try:
            bpy.ops.import_scene.fbx(
                filepath=filepath,
                use_anim=True,  # 导入动画
                anim_offset=1.0,  # 动画偏移
                ignore_leaf_bones=False,  # 忽略末端骨骼
                force_connect_children=False,  # 强制连接子骨骼
                automatic_bone_orientation=False,  # 自动骨骼方向
                primary_bone_axis="X",
                secondary_bone_axis="Y",
            )

        except Exception as e:
            print(f"import FBX animation fail: {str(e)}")
            return False

        armature_obj = bpy.data.objects.get(armature_name)

        if not armature_obj or armature_obj.type != 'ARMATURE':
            raise ValueError(f"can't find Armature: {armature_name}")

        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = armature_obj

        rotation_rad = [
            rotation[0] * 3.141592 / 180.0,
            rotation[1] * 3.141592 / 180.0,
            rotation[2] * 3.141592 / 180.0
        ]
        armature_obj.rotation_euler = rotation_rad

    def export_fbx_skeleton(self, filepath, armature_name):
        scene = bpy.context.scene
        scene.frame_set(0)

        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        armature_obj = bpy.data.objects.get(armature_name)

        if not armature_obj or armature_obj.type != 'ARMATURE':
            raise ValueError(f"can't find Armature: {armature_name}")

        armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = armature_obj

        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,  # 仅导出选中的对象
            object_types={'ARMATURE'},  # 仅导出 Armature 类型
            use_mesh_modifiers=False,  # 不应用 Mesh 修改器（因为不导出 Mesh）

            bake_anim=True,  # 启用动画导出
            bake_anim_use_all_bones=True,  # 导出所有骨骼的动画
            bake_anim_use_nla_strips=False,  # 禁用NLA strips（直接导出Action）
            bake_anim_use_all_actions=False,  # 仅导出当前Action
            bake_anim_force_startend_keying=False,  # 强制使用时间轴范围
            bake_anim_step=1.0,  # 每帧采样

            add_leaf_bones=False,  # 不添加叶子骨骼
            armature_nodetype='NULL',  # 骨骼节点类型（保持默认）
            bake_space_transform=True,  # 应用变换
            use_armature_deform_only=True,  # 仅导出用于变形的骨骼
        )

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True

    def execute(self, context: bpy.types.Context):
        addon_prefs = bpy.context.preferences.addons[__addon_name__].preferences
        assert isinstance(addon_prefs, ExampleAddonPreferences)

        input_filepath = addon_prefs.refine_armature_input_filepath
        output_filepath = addon_prefs.refine_armature_output_filepath
        print("Glb2fbxOperator== input_filepath:", input_filepath)
        print("Glb2fbxOperator== output_filepath:", output_filepath)

        scene = bpy.context.scene
        scene.frame_start = 0

        # import skeleton
        skeleton_path = os.path.join(input_filepath, "Skeleton.fbx")
        skeleton_name = "Skeleton"
        rotation_degrees = (180, 0, 0)
        self.import_fbx_animation(skeleton_path, skeleton_name, rotation_degrees)

        for input_name in os.listdir(input_filepath):
            if ".fbx" not in input_name:
                continue
            if "Skeleton" in input_name:
                continue

            # remove skeleton animation
            skeleton_armature = bpy.data.objects[skeleton_name]
            bpy.context.view_layer.objects.active = skeleton_armature
            bpy.ops.object.mode_set(mode='OBJECT')
            if skeleton_armature.animation_data:
                skeleton_armature.animation_data.action = None
                skeleton_armature.animation_data_clear()

            # import armature fbx
            armature_name = input_name.split(".")[0]
            fbx_file = os.path.join(input_filepath, input_name)
            self.import_fbx_animation(fbx_file, armature_name)

            # force armature frame 0 to skeleton pose
            ks = bpy.data.scenes["Scene"].keying_sets_all
            ks.active = ks['Whole Character']

            bpy.context.view_layer.objects.active = skeleton_armature
            bpy.ops.object.mode_set(mode='POSE')
            self.add_constraints(skeleton_name, armature_name)
            apply_animation_success = self.apply_animation(skeleton_name, armature_name)
            if not apply_animation_success:
                self.del_constraints()
                self.remove_armature(armature_name)
                continue
            self.del_constraints()

            # save fbx
            output_fbx_path = os.path.join(output_filepath, input_name)
            self.export_fbx_skeleton(output_fbx_path, skeleton_name)

            self.remove_armature(armature_name)

        return {'FINISHED'}

class AddConstraintOperator(bpy.types.Operator):
    bl_idname = "object.add_constraint"
    bl_label = "AddConstraint"

    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return hasattr(context.scene, "armature_select_props")

    def execute(self, context: bpy.types.Context):
        addon_props = context.scene.armature_select_props
        target_armature = addon_props.target_armature
        source_armature = addon_props.source_armature
        if not target_armature or not source_armature:
            self.report({'ERROR'}, "Please select both target and source armatures.")
            return {'CANCELLED'}
        if target_armature == source_armature:
            self.report({'ERROR'}, "Target and Source armatures cannot be the same.")
            return {'CANCELLED'}
        print(f"Target Armature: {target_armature.name}")
        print(f"Source Armature: {source_armature.name}")
        
        constraints_added_count = 0
        for target_bone in target_armature.pose.bones:
            if target_bone.name in source_armature.pose.bones:
                constraint = target_bone.constraints.new(type='COPY_TRANSFORMS')
                constraint.target = source_armature
                constraint.subtarget = target_bone.name
                constraints_added_count += 1
        self.report({'INFO'}, f"Added {constraints_added_count} constraints to '{target_armature.name}'.")
        
        return {'FINISHED'}

class DeleteConstraintOperator(bpy.types.Operator):
    bl_idname = "object.delete_constraint"
    bl_label = "DeleteConstraint"

    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return hasattr(context.scene, "armature_select_props")

    def execute(self, context: bpy.types.Context):
        addon_props = context.scene.armature_select_props
        target_armature = addon_props.target_armature
        if not target_armature:
            self.report({'ERROR'}, "Please select a target armature.")
            return {'CANCELLED'}
        constraints_removed_count = 0
        for bone in target_armature.pose.bones:
            for constraint in list(bone.constraints):
                bone.constraints.remove(constraint)
                constraints_removed_count += 1
        self.report({'INFO'}, f"Removed {constraints_removed_count} constraints from '{target_armature.name}'.")
        return {'FINISHED'}