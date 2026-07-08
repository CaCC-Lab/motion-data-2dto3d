"""BVH→VRMリターゲティング + アニメーションGLB/Blendエクスポート.

Usage:
    blender --background --python retarget_bvh_to_vrm.py -- \
        --bvh motion.bvh --vrm model.vrm \
        --output-glb animation.glb --output-blend animation.blend

v7.4リターゲティング:
- Hips回転: 3軸（lateral/up/forward）からbone座標系に正しくマッピング
  - bone Y = spine方向（up）、bone X = lateral、bone Z = forward
  - rest行列の逆でローカル変換
- Hips位置: armature.location に差分（BVH Hip - VRM Hips レスト位置）
- Spine/Chest/UpperChest: hip→shoulder間のtwistをローカルY軸回転で分配
- 四肢: compute_limb_rotation（parent_posed @ rest_offset逆 → rotation_difference）
- 処理順序: Hips → Spine chain → Neck → Shoulder → UpperArm → LowerArm
- 各レベル間でdepsgraph更新
"""

import argparse
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--bvh", required=True, help="BVHファイルパス")
    parser.add_argument("--vrm", required=True, help="VRMファイルパス")
    parser.add_argument("--output-glb", default="", help="アニメーションGLB出力パス")
    parser.add_argument("--output-blend", default="", help="Blendファイル出力パス")
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def import_bvh(path: str):
    bpy.ops.import_anim.bvh(filepath=path, use_fps_scale=True)
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE" and "bvh" in obj.name.lower():
            return obj
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if armatures:
        return armatures[-1]
    raise RuntimeError("BVH Armature not found")


def import_vrm(path: str):
    if path.endswith(".vrm"):
        try:
            bpy.ops.import_scene.vrm(filepath=path)
        except Exception:
            bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)

    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE" and "bvh" not in obj.name.lower():
            return obj
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if len(armatures) >= 2:
        return armatures[-1]
    raise RuntimeError("VRM Armature not found")


def get_bvh_positions(bvh_arm, frame: int):
    bpy.context.scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bvh_eval = bvh_arm.evaluated_get(depsgraph)
    positions = {}
    for pbone in bvh_eval.pose.bones:
        positions[pbone.name] = (bvh_arm.matrix_world @ pbone.head).copy()
    return positions


def direction(positions, from_j, to_j):
    if from_j not in positions or to_j not in positions:
        return None
    d = positions[to_j] - positions[from_j]
    return d.normalized() if d.length > 1e-8 else None


def update_pose():
    bpy.context.view_layer.update()


def set_bone_rot(vrm_arm, bone_name, quat, frame):
    bone = vrm_arm.pose.bones.get(bone_name)
    if bone:
        bone.rotation_quaternion = quat
        bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)


def compute_limb_rotation(vrm_arm, bone_name, target_world_dir):
    """四肢ボーンのローカル回転を計算.

    parent_posed @ rest_offset の逆で方向をローカル変換し、
    (0,1,0).rotation_difference で回転を求める。
    診断でdot=1.0000を確認済みの手法。
    """
    pbone = vrm_arm.pose.bones.get(bone_name)
    if not pbone:
        return Quaternion()

    # 親のposed world matrix
    if pbone.parent:
        parent_world = vrm_arm.matrix_world @ pbone.parent.matrix
    else:
        parent_world = vrm_arm.matrix_world

    # ボーンのレスト相対行列（親からの相対）
    if pbone.bone.parent:
        rest_offset = pbone.bone.parent.matrix_local.inverted() @ pbone.bone.matrix_local
    else:
        rest_offset = pbone.bone.matrix_local

    # ローカル回転なしでのボーンのワールド行列
    M = parent_world @ rest_offset

    # ターゲット方向をボーンのローカル空間に変換
    local_target = M.to_3x3().inverted() @ target_world_dir

    # ボーンのローカルY軸(0,1,0)からターゲットへの回転
    return Vector((0, 1, 0)).rotation_difference(local_target)


def compute_hips_rotation(vrm_arm, pos):
    """Hipsボーンの完全回転（方向+ツイスト）を計算.

    BVHの骨盤フレーム（lateral/up/forward）からボーンのローカル回転を求める。
    bone Y = spine方向(up)、bone X = lateral方向にマッピング。
    """
    if not all(k in pos for k in ("Hip", "LHip", "RHip", "Thorax")):
        return Quaternion()

    # 骨盤の3軸を構築
    lateral = (pos["LHip"] - pos["RHip"]).normalized()
    spine_up = (pos["Thorax"] - pos["Hip"]).normalized()
    forward = lateral.cross(spine_up).normalized()
    # 直交化
    spine_up = forward.cross(lateral).normalized()

    # ボーン座標系にマッピング: bone Y = up, bone Z = forward, bone X = lateral
    # Matrix columns = [bone_X_world, bone_Y_world, bone_Z_world]
    bone_x = lateral
    bone_y = spine_up
    bone_z = forward
    desired_world = Matrix((bone_x, bone_y, bone_z)).transposed()
    desired_world_q = desired_world.to_quaternion()

    # ボーンのレスト行列からローカル回転に変換（compute_limb_rotationと同じ手法）
    pbone = vrm_arm.pose.bones.get("J_Bip_C_Hips")
    if not pbone:
        return Quaternion()

    if pbone.parent:
        parent_world = vrm_arm.matrix_world @ pbone.parent.matrix
    else:
        parent_world = vrm_arm.matrix_world

    if pbone.bone.parent:
        rest_offset = pbone.bone.parent.matrix_local.inverted() @ pbone.bone.matrix_local
    else:
        rest_offset = pbone.bone.matrix_local

    M = parent_world @ rest_offset
    M_q = M.to_3x3().to_quaternion()

    return M_q.inverted() @ desired_world_q


def compute_spine_twist(pos):
    """Hip lateralとShoulder lateral間のtwist角度を計算.

    spine方向に垂直な平面に射影してtwist角度を求める。
    """
    if not all(k in pos for k in ("Hip", "Thorax", "LHip", "RHip", "LShoulder", "RShoulder")):
        return 0.0

    hip_lateral = (pos["LHip"] - pos["RHip"]).normalized()
    shoulder_lateral = (pos["LShoulder"] - pos["RShoulder"]).normalized()
    spine_dir = (pos["Thorax"] - pos["Hip"])
    if spine_dir.length < 1e-8:
        return 0.0
    spine_dir.normalize()

    # spine方向に垂直な平面に射影
    hip_proj = hip_lateral - hip_lateral.dot(spine_dir) * spine_dir
    sho_proj = shoulder_lateral - shoulder_lateral.dot(spine_dir) * spine_dir

    if hip_proj.length < 1e-6 or sho_proj.length < 1e-6:
        return 0.0

    hip_proj.normalize()
    sho_proj.normalize()

    twist_angle = hip_proj.angle(sho_proj, 0)
    cross = hip_proj.cross(sho_proj)
    if cross.dot(spine_dir) < 0:
        twist_angle = -twist_angle

    return twist_angle


def retarget_frame(bvh_arm, vrm_arm, hips_rest_pos, frame: int):
    """1フレーム分のリターゲティング."""
    pos = get_bvh_positions(bvh_arm, frame)

    # === Level 0: Hips（回転 + 位置） ===
    hips_rot = compute_hips_rotation(vrm_arm, pos)
    set_bone_rot(vrm_arm, "J_Bip_C_Hips", hips_rot, frame)

    # Hips位置: BVH位置 - VRMレスト位置 = 差分
    if "Hip" in pos:
        delta = pos["Hip"] - hips_rest_pos
        vrm_arm.location = delta
        vrm_arm.keyframe_insert(data_path="location", frame=frame)

    update_pose()

    # === Level 1: Spine/Chest/UpperChest ===
    # hip→shoulder間のtwistをローカルY軸回転で3ボーンに均等分配
    twist_angle = compute_spine_twist(pos)
    for bone_name in ("J_Bip_C_Spine", "J_Bip_C_Chest", "J_Bip_C_UpperChest"):
        # 各ボーンに1/3のtwistを適用（ローカルY軸回り）
        bone_twist = Quaternion((0, 1, 0), twist_angle / 3.0)
        set_bone_rot(vrm_arm, bone_name, bone_twist, frame)

    update_pose()

    # === Level 2: Neck ===
    neck_dir = direction(pos, "Thorax", "Nose") or direction(pos, "Thorax", "Head")
    if neck_dir:
        rot = compute_limb_rotation(vrm_arm, "J_Bip_C_Neck", neck_dir)
        set_bone_rot(vrm_arm, "J_Bip_C_Neck", rot, frame)

    set_bone_rot(vrm_arm, "J_Bip_C_Head", Quaternion(), frame)
    update_pose()

    # === Level 3: Shoulders ===
    for side, center_j, shoulder_j in [("L", "Thorax", "LShoulder"), ("R", "Thorax", "RShoulder")]:
        s_dir = direction(pos, center_j, shoulder_j)
        if s_dir:
            rot = compute_limb_rotation(vrm_arm, f"J_Bip_{side}_Shoulder", s_dir)
            set_bone_rot(vrm_arm, f"J_Bip_{side}_Shoulder", rot, frame)

    update_pose()

    # === Level 4: UpperArm + UpperLeg ===
    for parent_j, child_j, bone_name in [
        ("LShoulder", "LElbow", "J_Bip_L_UpperArm"),
        ("RShoulder", "RElbow", "J_Bip_R_UpperArm"),
        ("LHip", "LKnee", "J_Bip_L_UpperLeg"),
        ("RHip", "RKnee", "J_Bip_R_UpperLeg"),
    ]:
        d = direction(pos, parent_j, child_j)
        if d:
            rot = compute_limb_rotation(vrm_arm, bone_name, d)
            set_bone_rot(vrm_arm, bone_name, rot, frame)

    update_pose()

    # === Level 5: LowerArm + LowerLeg ===
    for parent_j, child_j, bone_name in [
        ("LElbow", "LWrist", "J_Bip_L_LowerArm"),
        ("RElbow", "RWrist", "J_Bip_R_LowerArm"),
        ("LKnee", "LFoot", "J_Bip_L_LowerLeg"),
        ("RKnee", "RFoot", "J_Bip_R_LowerLeg"),
    ]:
        d = direction(pos, parent_j, child_j)
        if d:
            rot = compute_limb_rotation(vrm_arm, bone_name, d)
            set_bone_rot(vrm_arm, bone_name, rot, frame)

    update_pose()

    # === Level 6: Foot ===
    set_bone_rot(vrm_arm, "J_Bip_L_Foot", Quaternion(), frame)
    set_bone_rot(vrm_arm, "J_Bip_R_Foot", Quaternion(), frame)


def fix_quaternion_continuity(vrm_arm):
    action = vrm_arm.animation_data.action if vrm_arm.animation_data else None
    if not action:
        return

    for bone in vrm_arm.pose.bones:
        if bone.rotation_mode != "QUATERNION":
            continue
        data_path = f'pose.bones["{bone.name}"].rotation_quaternion'
        fcurves = [fc for fc in action.fcurves if fc.data_path == data_path]
        if len(fcurves) != 4:
            continue

        n = len(fcurves[0].keyframe_points)
        for i in range(1, n):
            prev = Quaternion([fcurves[j].keyframe_points[i - 1].co[1] for j in range(4)])
            curr = Quaternion([fcurves[j].keyframe_points[i].co[1] for j in range(4)])
            if prev.dot(curr) < 0:
                for j in range(4):
                    fcurves[j].keyframe_points[i].co[1] *= -1

    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"


def export_animation_glb(vrm_arm, output_path: str):
    bpy.ops.object.select_all(action="DESELECT")
    vrm_arm.select_set(True)
    for child in vrm_arm.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = vrm_arm

    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=True,
    )
    print(f"Animation GLB exported: {output_path}")


def main():
    args = parse_args()
    print("=== BVH->VRM Retargeting (v7.4) ===")
    print(f"BVH: {args.bvh}")
    print(f"VRM: {args.vrm}")

    clear_scene()

    # 1. VRMインポート
    print("Importing VRM...")
    vrm_arm = import_vrm(args.vrm)
    print(f"  VRM: {vrm_arm.name} ({len(vrm_arm.pose.bones)} bones)")

    for bone in vrm_arm.pose.bones:
        bone.rotation_mode = "QUATERNION"

    # VRMのHipsレスト位置を記録（位置差分計算用）
    hips_bone = vrm_arm.data.bones.get("J_Bip_C_Hips")
    hips_rest_pos = (vrm_arm.matrix_world @ hips_bone.head_local) if hips_bone else Vector((0, 0, 1))
    print(f"  Hips rest pos: ({hips_rest_pos.x:.3f}, {hips_rest_pos.y:.3f}, {hips_rest_pos.z:.3f})")

    # 2. BVHインポート
    print("Importing BVH...")
    bvh_arm = import_bvh(args.bvh)
    print(f"  BVH: {bvh_arm.name} ({len(bvh_arm.pose.bones)} bones)")
    bvh_arm.hide_viewport = False

    action = bvh_arm.animation_data.action if bvh_arm.animation_data else None
    if not action:
        raise RuntimeError("BVH has no animation data")

    frame_start = int(action.frame_range[0])
    frame_end = int(action.frame_range[1])
    total_frames = frame_end - frame_start + 1
    print(f"  Frames: {frame_start}-{frame_end} ({total_frames})")

    # 3. リターゲティング
    print("Retargeting...")
    for frame in range(frame_start, frame_end + 1):
        retarget_frame(bvh_arm, vrm_arm, hips_rest_pos, frame)
        if (frame - frame_start) % 50 == 0:
            print(f"  {(frame - frame_start) / total_frames * 100:.0f}% (frame {frame})")
    print("  100%")

    # 4. 後処理
    print("Post-processing...")
    fix_quaternion_continuity(vrm_arm)

    bvh_arm.hide_viewport = True
    bvh_arm.hide_render = True
    bpy.context.scene.frame_start = frame_start
    bpy.context.scene.frame_end = frame_end

    # 5. エクスポート
    if args.output_glb:
        print("Exporting GLB...")
        export_animation_glb(vrm_arm, args.output_glb)

    if args.output_blend:
        print("Saving blend...")
        bpy.ops.wm.save_as_mainfile(filepath=args.output_blend)
        print(f"Blend: {args.output_blend}")

    print("=== Done ===")


if __name__ == "__main__":
    main()
