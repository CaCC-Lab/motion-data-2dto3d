"""BVH→Mixamo FBXリターゲティング + アニメーションFBX/Blendエクスポート.

Usage:
    blender --background --python retarget_bvh_to_mixamo.py -- \
        --bvh motion.bvh --target-fbx mixamo_character.fbx \
        --output-fbx animation.fbx --output-blend animation.blend

H36M BVH（motion-data-2dto3d 出力）の関節位置から、Mixamo互換リグへ
方向ベースでリターゲティングする。retarget_bvh_to_vrm.py と同系の手法。
"""

import argparse
import sys
from typing import Dict, Optional

import bpy
from mathutils import Matrix, Quaternion, Vector

# Mixamo ボーン名候補（mixamorig: / 無印 / Unity FBX の Character1_ ）
MIXAMO_BONES = {
    "hips": ("mixamorig:Hips", "Hips", "Character1_Hips"),
    "spine": ("mixamorig:Spine", "Spine", "Character1_Spine"),
    "spine1": ("mixamorig:Spine1", "Spine1", "Character1_Spine1"),
    "spine2": ("mixamorig:Spine2", "Spine2", "Character1_Spine2"),
    "neck": ("mixamorig:Neck", "Neck", "Character1_Neck"),
    "head": ("mixamorig:Head", "Head", "Character1_Head"),
    "left_shoulder": ("mixamorig:LeftShoulder", "LeftShoulder", "Character1_LeftShoulder"),
    "right_shoulder": ("mixamorig:RightShoulder", "RightShoulder", "Character1_RightShoulder"),
    "left_arm": ("mixamorig:LeftArm", "LeftArm", "Character1_LeftArm"),
    "right_arm": ("mixamorig:RightArm", "RightArm", "Character1_RightArm"),
    "left_forearm": ("mixamorig:LeftForeArm", "LeftForeArm", "Character1_LeftForeArm"),
    "right_forearm": ("mixamorig:RightForeArm", "RightForeArm", "Character1_RightForeArm"),
    "left_hand": ("mixamorig:LeftHand", "LeftHand", "Character1_LeftHand"),
    "right_hand": ("mixamorig:RightHand", "RightHand", "Character1_RightHand"),
    "left_upleg": ("mixamorig:LeftUpLeg", "LeftUpLeg", "Character1_LeftUpLeg"),
    "right_upleg": ("mixamorig:RightUpLeg", "RightUpLeg", "Character1_RightUpLeg"),
    "left_leg": ("mixamorig:LeftLeg", "LeftLeg", "Character1_LeftLeg"),
    "right_leg": ("mixamorig:RightLeg", "RightLeg", "Character1_RightLeg"),
    "left_foot": ("mixamorig:LeftFoot", "LeftFoot", "Character1_LeftFoot"),
    "right_foot": ("mixamorig:RightFoot", "RightFoot", "Character1_RightFoot"),
}


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--bvh", required=True, help="BVHファイルパス")
    parser.add_argument("--target-fbx", required=True, help="MixamoキャラクターFBX")
    parser.add_argument("--output-fbx", default="", help="アニメーションFBX出力パス")
    parser.add_argument("--output-blend", default="", help="Blendファイル出力パス")
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def resolve_bone(arm, role: str) -> Optional[str]:
    """ロール名から実際のボーン名を解決."""
    for candidate in MIXAMO_BONES[role]:
        if arm.pose.bones.get(candidate):
            return candidate
    return None


def resolve_all_bones(arm) -> Dict[str, str]:
    """利用可能な Mixamo ボーンを解決."""
    resolved = {}
    for role in MIXAMO_BONES:
        name = resolve_bone(arm, role)
        if name:
            resolved[role] = name
    return resolved


def import_bvh(path: str):
    bpy.ops.import_anim.bvh(filepath=path, use_fps_scale=True)
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE" and "bvh" in obj.name.lower():
            return obj
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if armatures:
        return armatures[-1]
    raise RuntimeError("BVH Armature not found")


def import_mixamo_fbx(path: str):
    bpy.ops.import_scene.fbx(filepath=path)
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE" and "bvh" not in obj.name.lower():
            return obj
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if len(armatures) >= 1:
        return armatures[-1]
    raise RuntimeError("Mixamo Armature not found")


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


def set_bone_rot(target_arm, bone_name, quat, frame):
    if not bone_name:
        return
    bone = target_arm.pose.bones.get(bone_name)
    if bone:
        bone.rotation_quaternion = quat
        bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)


def compute_limb_rotation(target_arm, bone_name, target_world_dir):
    pbone = target_arm.pose.bones.get(bone_name)
    if not pbone:
        return Quaternion()

    if pbone.parent:
        parent_world = target_arm.matrix_world @ pbone.parent.matrix
    else:
        parent_world = target_arm.matrix_world

    if pbone.bone.parent:
        rest_offset = pbone.bone.parent.matrix_local.inverted() @ pbone.bone.matrix_local
    else:
        rest_offset = pbone.bone.matrix_local

    m = parent_world @ rest_offset
    local_target = m.to_3x3().inverted() @ target_world_dir
    return Vector((0, 1, 0)).rotation_difference(local_target)


def compute_hips_rotation(target_arm, hips_bone: str, pos):
    if not all(k in pos for k in ("Hip", "LHip", "RHip", "Thorax")):
        return Quaternion()

    lateral = (pos["LHip"] - pos["RHip"]).normalized()
    spine_up = (pos["Thorax"] - pos["Hip"]).normalized()
    forward = lateral.cross(spine_up).normalized()
    spine_up = forward.cross(lateral).normalized()

    bone_x = lateral
    bone_y = spine_up
    bone_z = forward
    desired_world = Matrix((bone_x, bone_y, bone_z)).transposed()
    desired_world_q = desired_world.to_quaternion()

    pbone = target_arm.pose.bones.get(hips_bone)
    if not pbone:
        return Quaternion()

    if pbone.parent:
        parent_world = target_arm.matrix_world @ pbone.parent.matrix
    else:
        parent_world = target_arm.matrix_world

    if pbone.bone.parent:
        rest_offset = pbone.bone.parent.matrix_local.inverted() @ pbone.bone.matrix_local
    else:
        rest_offset = pbone.bone.matrix_local

    m = parent_world @ rest_offset
    m_q = m.to_3x3().to_quaternion()
    return m_q.inverted() @ desired_world_q


def compute_spine_twist(pos):
    if not all(k in pos for k in ("Hip", "Thorax", "LHip", "RHip", "LShoulder", "RShoulder")):
        return 0.0

    hip_lateral = (pos["LHip"] - pos["RHip"]).normalized()
    shoulder_lateral = (pos["LShoulder"] - pos["RShoulder"]).normalized()
    spine_dir = pos["Thorax"] - pos["Hip"]
    if spine_dir.length < 1e-8:
        return 0.0
    spine_dir.normalize()

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


def retarget_frame(bvh_arm, target_arm, bones: dict, hips_rest_pos, frame: int):
    pos = get_bvh_positions(bvh_arm, frame)

    hips_rot = compute_hips_rotation(target_arm, bones.get("hips", ""), pos)
    set_bone_rot(target_arm, bones.get("hips"), hips_rot, frame)

    if "Hip" in pos:
        delta = pos["Hip"] - hips_rest_pos
        target_arm.location = delta
        target_arm.keyframe_insert(data_path="location", frame=frame)

    update_pose()

    twist_angle = compute_spine_twist(pos)
    spine_roles = ("spine", "spine1", "spine2")
    for role in spine_roles:
        bone_twist = Quaternion((0, 1, 0), twist_angle / 3.0)
        set_bone_rot(target_arm, bones.get(role), bone_twist, frame)

    update_pose()

    neck_dir = direction(pos, "Thorax", "Nose") or direction(pos, "Thorax", "Head")
    if neck_dir:
        rot = compute_limb_rotation(target_arm, bones.get("neck", ""), neck_dir)
        set_bone_rot(target_arm, bones.get("neck"), rot, frame)
    set_bone_rot(target_arm, bones.get("head"), Quaternion(), frame)

    update_pose()

    for side, center_j, shoulder_j, shoulder_role, arm_role in [
        ("L", "Thorax", "LShoulder", "left_shoulder", "left_arm"),
        ("R", "Thorax", "RShoulder", "right_shoulder", "right_arm"),
    ]:
        s_dir = direction(pos, center_j, shoulder_j)
        if s_dir:
            rot = compute_limb_rotation(target_arm, bones.get(shoulder_role, ""), s_dir)
            set_bone_rot(target_arm, bones.get(shoulder_role), rot, frame)
        elbow_j = "LElbow" if side == "L" else "RElbow"
        arm_dir = direction(pos, shoulder_j, elbow_j)
        if arm_dir:
            rot = compute_limb_rotation(target_arm, bones.get(arm_role, ""), arm_dir)
            set_bone_rot(target_arm, bones.get(arm_role), rot, frame)

    update_pose()

    for parent_j, child_j, role in [
        ("LHip", "LKnee", "left_upleg"),
        ("RHip", "RKnee", "right_upleg"),
        ("LKnee", "LFoot", "left_leg"),
        ("RKnee", "RFoot", "right_leg"),
    ]:
        d = direction(pos, parent_j, child_j)
        if d:
            rot = compute_limb_rotation(target_arm, bones.get(role, ""), d)
            set_bone_rot(target_arm, bones.get(role), rot, frame)

    update_pose()

    for parent_j, child_j, role in [
        ("LElbow", "LWrist", "left_forearm"),
        ("RElbow", "RWrist", "right_forearm"),
    ]:
        d = direction(pos, parent_j, child_j)
        if d:
            rot = compute_limb_rotation(target_arm, bones.get(role, ""), d)
            set_bone_rot(target_arm, bones.get(role), rot, frame)

    update_pose()
    set_bone_rot(target_arm, bones.get("left_foot"), Quaternion(), frame)
    set_bone_rot(target_arm, bones.get("right_foot"), Quaternion(), frame)


def fix_quaternion_continuity(target_arm):
    action = target_arm.animation_data.action if target_arm.animation_data else None
    if not action:
        return

    for bone in target_arm.pose.bones:
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


def export_animation_fbx(target_arm, output_path: str):
    bpy.ops.object.select_all(action="DESELECT")
    target_arm.select_set(True)
    for child in target_arm.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = target_arm

    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        bake_anim=True,
        add_leaf_bones=False,
        armature_nodetype="NULL",
    )
    print(f"Animation FBX exported: {output_path}")


def main():
    args = parse_args()
    print("=== BVH->Mixamo Retargeting ===")
    print(f"BVH: {args.bvh}")
    print(f"Target: {args.target_fbx}")

    clear_scene()

    print("Importing Mixamo FBX...")
    target_arm = import_mixamo_fbx(args.target_fbx)
    print(f"  Target: {target_arm.name} ({len(target_arm.pose.bones)} bones)")

    bones = resolve_all_bones(target_arm)
    if "hips" not in bones:
        raise RuntimeError(
            "Mixamo Hips bone not found. Expected mixamorig:Hips or Hips."
        )
    print(f"  Resolved bones: {list(bones.keys())}")

    for bone in target_arm.pose.bones:
        bone.rotation_mode = "QUATERNION"

    hips_bone_name = bones["hips"]
    hips_bone = target_arm.data.bones.get(hips_bone_name)
    hips_rest_pos = (
        target_arm.matrix_world @ hips_bone.head_local
        if hips_bone
        else Vector((0, 0, 1))
    )
    print(f"  Hips rest pos: ({hips_rest_pos.x:.3f}, {hips_rest_pos.y:.3f}, {hips_rest_pos.z:.3f})")

    print("Importing BVH...")
    bvh_arm = import_bvh(args.bvh)
    print(f"  BVH: {bvh_arm.name} ({len(bvh_arm.pose.bones)} bones)")

    action = bvh_arm.animation_data.action if bvh_arm.animation_data else None
    if not action:
        raise RuntimeError("BVH has no animation data")

    frame_start = int(action.frame_range[0])
    frame_end = int(action.frame_range[1])
    total_frames = frame_end - frame_start + 1
    print(f"  Frames: {frame_start}-{frame_end} ({total_frames})")

    print("Retargeting...")
    for frame in range(frame_start, frame_end + 1):
        retarget_frame(bvh_arm, target_arm, bones, hips_rest_pos, frame)
        if (frame - frame_start) % 50 == 0:
            print(f"  {(frame - frame_start) / total_frames * 100:.0f}% (frame {frame})")
    print("  100%")

    print("Post-processing...")
    fix_quaternion_continuity(target_arm)

    bvh_arm.hide_viewport = True
    bvh_arm.hide_render = True
    bpy.context.scene.frame_start = frame_start
    bpy.context.scene.frame_end = frame_end

    if args.output_fbx:
        print("Exporting FBX...")
        export_animation_fbx(target_arm, args.output_fbx)

    if args.output_blend:
        print("Saving blend...")
        bpy.ops.wm.save_as_mainfile(filepath=args.output_blend)
        print(f"Blend: {args.output_blend}")

    print("=== Done ===")


if __name__ == "__main__":
    main()
