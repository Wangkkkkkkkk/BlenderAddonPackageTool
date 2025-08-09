import bpy
import bmesh
from mathutils import Vector, kdtree
from mathutils.geometry import intersect_point_line

from math import radians

from ..config import __addon_name__
from ..preference.AddonPreferences import ExampleAddonPreferences


class GetSelectVertexOperator(bpy.types.Operator):
    '''ExampleAddon'''
    bl_idname = "object.get_select_vertex"
    bl_label = "GetSelectVertex"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        obj = context.active_object
        return (obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT')

    def execute(self, context: bpy.types.Context):
        # check if in edit mode and object is mesh
        obj = context.edit_object
        if obj is None or obj.type != 'MESH':
            self.report({"ERROR"}, str("Not in EDIT mode"))
            return {"CANCELLED"}

        # get selected vertices
        bm = bmesh.from_edit_mesh(obj.data)
        selected_local = [v.co for v in bm.verts if v.select]
        if not selected_local:
            self.report({"ERROR"}, "No vertices selected")
            return {"CANCELLED"}

        # get center of selected vertices
        center_local = sum(selected_local, Vector()) / len(selected_local)
        center_world = obj.matrix_world @ center_local

        # store center in scene custom properties
        scene = context.scene
        centers = list(scene.get('selection_centers', []))
        centers.append((center_world.x, center_world.y, center_world.z))
        scene['selection_centers'] = centers
        scene['selected_vertex_count'] = len(centers)

        self.report({'INFO'}, f"Selection center stored: {center_world}")
        return {'FINISHED'}

class CancelSelectVertexOperator(bpy.types.Operator):
    '''ExampleAddon'''
    bl_idname = "object.cancel_select_vertex"
    bl_label = "CancelSelectVertex"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        count = context.scene.get('selected_vertex_count', 0)
        return isinstance(count, int) and count > 0

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        scene['selection_centers'] = []
        scene['selected_vertex_count'] = 0
        self.report({'INFO'}, "已清空已记录的选择中心")
        return {'FINISHED'}

class GenerateBonesOperator(bpy.types.Operator):
    '''ExampleAddon'''
    bl_idname = "object.generate_bones"
    bl_label = "GenerateBones"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.scene.selected_vertex_count >= 2

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        props = scene.armature_select_props
        # 获取选中的骨架对象和父骨
        arm_obj = getattr(props, "Select_armature", None)
        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "No valid target armature selected!")
            return {'CANCELLED'}
        parent_bone_name = getattr(props, "Select_parent_bone", "NONE")
        if parent_bone_name == 'NONE':
            parent_bone_name = ""
        # 读取已记录的选区中心（世界坐标）
        if 'selection_centers' not in scene or not scene['selection_centers']:
            self.report({'ERROR'}, "No selection centers stored. Run 'Get Selection Center' first.")
            return {'CANCELLED'}
        centers_world = [Vector(c) for c in scene['selection_centers']]
        if len(centers_world) < 2:
            self.report({'ERROR'}, "Select centers number < 2")
            return {'CANCELLED'}
        # 世界 -> Armature 局部
        mw_inv = arm_obj.matrix_world.inverted()
        centers_local = [mw_inv @ c for c in centers_world]
        bone_prefix = scene.bone_prefix
        # 记录先前活动对象与模式
        prev_active = context.view_layer.objects.active
        prev_mode = prev_active.mode if prev_active else 'OBJECT'
        # 进入目标 Armature 的编辑模式
        context.view_layer.objects.active = arm_obj
        arm_obj.select_set(True)
        if arm_obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = arm_obj.data.edit_bones
        # 创建首骨
        first_name = f"{bone_prefix}00"
        bone_prev = edit_bones.new(first_name)
        bone_prev.head = centers_local[0]
        bone_prev.tail = centers_local[1]
        # 若选择了父骨，则设置父子关系（不强连）
        if parent_bone_name and parent_bone_name in edit_bones:
            bone_prev.parent = edit_bones[parent_bone_name]
            bone_prev.use_connect = False
        # 创建后续骨骼并与前一根相连
        for i in range(1, len(centers_local) - 1):
            bone = edit_bones.new(f"{bone_prefix}{i:02}")
            bone.head = centers_local[i]
            bone.tail = centers_local[i + 1]
            bone.parent = bone_prev
            bone.use_connect = True
            bone_prev = bone
        # 退出编辑并恢复先前活动对象与模式
        bpy.ops.object.mode_set(mode='OBJECT')
        if prev_active and prev_active != arm_obj:
            context.view_layer.objects.active = prev_active
            try:
                if prev_active.mode != prev_mode:
                    bpy.ops.object.mode_set(mode=prev_mode)
            except Exception:
                pass
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
        if not selected_verts:
            self.report({'ERROR'}, "No vertices selected")
            return {'CANCELLED'}

        bones = target_armature.data.bones
        if not bones:
            self.report({'ERROR'}, "Target armature has no bones")
            return {'CANCELLED'}

        # 预构建骨段（世界空间）与 KDTree（用段中点）
        M = target_armature.matrix_world
        segments = []  # [(bone_name, head_w, tail_w, mid_w)]
        for b in bones:
            head_w = M @ b.head_local
            tail_w = M @ b.tail_local
            mid_w  = (head_w + tail_w) * 0.5
            segments.append((b.name, head_w, tail_w, mid_w))
        
        seg_kd = kdtree.KDTree(len(segments))
        for i, (_, _, _, mid_w) in enumerate(segments):
            seg_kd.insert(mid_w, i)
        seg_kd.balance()

        # 混合参数
        k = 4              # 每个顶点采用最近的 k 个骨段（飘带/裙子/披风一般 3~6 效果较好）
        power = 2.0        # 距离衰减幂，2 越锐利，1 更平滑
        eps = 1e-8
        
         # 为每个选中顶点分配权重
        for vert in selected_verts:
            world_co = obj.matrix_world @ vert.co

            co_closest, seg_idx_closest, dist_closest = seg_kd.find(world_co)
            # 以最近距离自适应一个搜索半径，扩大以涵盖邻近多段
            radius = max(dist_closest * 2.5, 1e-6)
            neighbors = seg_kd.find_range(world_co, radius)

            if not neighbors:
                neighbors = [(co_closest, seg_idx_closest, dist_closest)]

            # 取距离最近的前 k 段
            neighbors.sort(key=lambda it: it[2])
            neighbors = neighbors[:k]

            accum = {}  # bone_name -> accumulated weight
            for _, seg_idx, _ in neighbors:
                bone_name, head_w, tail_w, _ = segments[seg_idx]
                # 投影到线段并截断 fac 到 [0,1]
                pt, fac = intersect_point_line(world_co, head_w, tail_w)
                if fac < 0.0:
                    pt = head_w
                    fac = 0.0
                elif fac > 1.0:
                    pt = tail_w
                    fac = 1.0
                dist_line = (world_co - pt).length
                w = 1.0 / ((dist_line ** power) + eps)
                accum[bone_name] = accum.get(bone_name, 0.0) + w

            # 局部归一化并写入权重
            total = sum(accum.values())
            if total > 0.0:
                for bone_name, w in accum.items():
                    vg = obj.vertex_groups.get(bone_name) or obj.vertex_groups.new(name=bone_name)
                    vert[deform_layer][vg.index] = max(0.0, min(1.0, w / total))

        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}


class AddCylinderColliderOperator(bpy.types.Operator):
    '''ExampleAddon'''
    bl_idname = "object.add_cylinder_collider"
    bl_label = "AddCylinderCollider"

    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context):
        scene = context.scene
        props = getattr(scene, "armature_select_props", None)
        if not props:
            return False
        arm = getattr(props, "Select_armature", None)
        if not arm or arm.type != 'ARMATURE' or not arm.data:
            return False
        bone_name = getattr(props, "Select_parent_bone", None)
        if not bone_name or bone_name == 'NONE':
            return False
        return bone_name in arm.data.bones

    def execute(self, context: bpy.types.Context):
        scene = context.scene
        props = scene.armature_select_props
        # 获取选中的骨架对象和父骨
        arm_obj = getattr(props, "Select_armature", None)
        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "No valid target armature selected!")
            return {'CANCELLED'}
        bone_name = getattr(props, "Select_parent_bone", None)
        if not bone_name or bone_name not in arm_obj.data.bones:
            self.report({'ERROR'}, "No valid parent bone selected!")
            return {'CANCELLED'}
        # 计算骨头长度（世界空间）
        b = arm_obj.data.bones[bone_name]
        M = arm_obj.matrix_world
        head_w = M @ b.head_local
        tail_w = M @ b.tail_local
        length = (tail_w - head_w).length
        if length <= 1e-6:
            self.report({'ERROR'}, "Bone length is zero")
            return {'CANCELLED'}
        # 创建圆柱（默认原点在几何中心，轴向为局部+Z）
        radius = 0.075
        depth = length
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16, radius=radius, depth=depth,
            enter_editmode=False, align='WORLD', location=(0, 0, 0)
        )
        cyl = context.active_object
        cyl.name = f"collider_{bone_name}"
        # 将几何整体下移 depth/2，使“顶面中心”成为对象原点
        bm = bmesh.new()
        bm.from_mesh(cyl.data)
        dz = depth * 0.5
        for v in bm.verts:
            v.co.z -= dz
        bm.to_mesh(cyl.data)
        bm.free()
        cyl.data.update()
        # 预设一个旋转偏移：让圆柱长轴（原本+Z）经偏移后适配骨轴（骨通常沿 +Y）
        # 旋转 +90° about X: +Z -> -Y，且因为我们把几何沿 -Z 延展，-Z -> +Y（与骨方向一致）
        cyl.rotation_euler = (radians(90.0), 0.0, 0.0)
        # 添加 Copy Location 约束（位置对齐到骨头）
        c_loc = cyl.constraints.new('COPY_LOCATION')
        c_loc.target = arm_obj
        c_loc.subtarget = bone_name
        c_loc.target_space = 'WORLD'
        c_loc.owner_space = 'WORLD'
        # 添加 Copy Rotation 约束（旋转对齐到骨头），保留上面的旋转作为偏移
        c_rot = cyl.constraints.new('COPY_ROTATION')
        c_rot.target = arm_obj
        c_rot.subtarget = bone_name
        c_rot.target_space = 'WORLD'
        c_rot.owner_space = 'WORLD'
        c_rot.use_offset = True  # 保留 cyl.rotation_euler 作为偏移，使长轴对齐骨轴
        # --- 添加碰撞物理（供布料/头发等使用） ---
        view_layer = context.view_layer
        prev_active = view_layer.objects.active
        view_layer.objects.active = cyl
        cyl.select_set(True)
        try:
            bpy.ops.object.modifier_add(type='COLLISION')
        except Exception:
            pass  # 已存在时忽略
        return {'FINISHED'}