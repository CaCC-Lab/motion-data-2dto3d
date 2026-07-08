"""GLBメッシュに自動リギングしてVRMとして出力するBlenderスクリプト.

Usage:
    blender --background --python rig_glb_to_vrm.py -- \
        --input model.glb --output model.vrm

このスクリプトはBlenderのPythonインタープリタで実行される。
ヒューマノイドメッシュに対して:
1. メッシュの寸法からボーン位置を推定
2. Armatureを作成してVRMヒューマノイドボーン構造を構築
3. メッシュにArmature Modifierを設定
4. 自動ウェイトペイントを適用
5. VRM Addonを使ってVRMとしてエクスポート
"""

import argparse
import sys

import bpy
import mathutils


def parse_args():
    """コマンドライン引数を解析."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="入力GLBファイルパス")
    parser.add_argument("--output", required=True, help="出力VRMファイルパス")
    return parser.parse_args(argv)


def clear_scene():
    """シーンをクリア."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def import_glb(path: str):
    """GLBファイルをインポート."""
    bpy.ops.import_scene.gltf(filepath=path)

    # インポートで生成された既存のArmatureを削除（後で新しく作り直す）
    imported_armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if imported_armatures:
        bpy.ops.object.select_all(action="DESELECT")
        for arm in imported_armatures:
            arm.select_set(True)
        bpy.ops.object.delete()
        print(f"  Removed {len(imported_armatures)} existing armature(s)")

    # インポートされたメッシュを取得
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("GLBにメッシュが含まれていません")
    # 複数メッシュがある場合は結合
    if len(meshes) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for m in meshes:
            m.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
    mesh_obj = bpy.context.view_layer.objects.active or meshes[0]
    return mesh_obj


def estimate_bone_positions(mesh_obj):
    """メッシュの寸法からVRMヒューマノイドボーン位置を推定.

    メッシュのバウンディングボックスから比率で骨格を推定する。
    直立したヒューマノイドモデルを前提とする。
    """
    bbox = [mesh_obj.matrix_world @ mathutils.Vector(v) for v in mesh_obj.bound_box]
    xs = [v.x for v in bbox]
    ys = [v.y for v in bbox]
    zs = [v.z for v in bbox]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    height = max_z - min_z
    width = max_x - min_x

    # ヒューマノイド比率（身長に対する割合）
    # 参考: 人体プロポーション（7.5頭身基準）
    bones = {}

    # 体幹
    bones["hips"] = (cx, cy, min_z + height * 0.53)
    bones["spine"] = (cx, cy, min_z + height * 0.58)
    bones["chest"] = (cx, cy, min_z + height * 0.66)
    bones["upper_chest"] = (cx, cy, min_z + height * 0.72)
    bones["neck"] = (cx, cy, min_z + height * 0.82)
    bones["head"] = (cx, cy, min_z + height * 0.87)
    bones["head_top"] = (cx, cy, min_z + height * 1.0)

    # 左腕
    shoulder_w = width * 0.22
    bones["left_shoulder"] = (cx + shoulder_w * 0.3, cy, min_z + height * 0.78)
    bones["left_upper_arm"] = (cx + shoulder_w, cy, min_z + height * 0.77)
    bones["left_lower_arm"] = (cx + width * 0.35, cy, min_z + height * 0.60)
    bones["left_hand"] = (cx + width * 0.45, cy, min_z + height * 0.47)

    # 右腕
    bones["right_shoulder"] = (cx - shoulder_w * 0.3, cy, min_z + height * 0.78)
    bones["right_upper_arm"] = (cx - shoulder_w, cy, min_z + height * 0.77)
    bones["right_lower_arm"] = (cx - width * 0.35, cy, min_z + height * 0.60)
    bones["right_hand"] = (cx - width * 0.45, cy, min_z + height * 0.47)

    # 左脚
    hip_w = width * 0.10
    bones["left_upper_leg"] = (cx + hip_w, cy, min_z + height * 0.50)
    bones["left_lower_leg"] = (cx + hip_w, cy, min_z + height * 0.27)
    bones["left_foot"] = (cx + hip_w, cy, min_z + height * 0.04)
    bones["left_toes"] = (cx + hip_w, cy - height * 0.06, min_z)

    # 右脚
    bones["right_upper_leg"] = (cx - hip_w, cy, min_z + height * 0.50)
    bones["right_lower_leg"] = (cx - hip_w, cy, min_z + height * 0.27)
    bones["right_foot"] = (cx - hip_w, cy, min_z + height * 0.04)
    bones["right_toes"] = (cx - hip_w, cy - height * 0.06, min_z)

    return bones


# VRMボーン名とBlender内部名の対応
VRM_BONE_MAP = {
    "hips": "J_Bip_C_Hips",
    "spine": "J_Bip_C_Spine",
    "chest": "J_Bip_C_Chest",
    "upper_chest": "J_Bip_C_UpperChest",
    "neck": "J_Bip_C_Neck",
    "head": "J_Bip_C_Head",
    "left_shoulder": "J_Bip_L_Shoulder",
    "left_upper_arm": "J_Bip_L_UpperArm",
    "left_lower_arm": "J_Bip_L_LowerArm",
    "left_hand": "J_Bip_L_Hand",
    "right_shoulder": "J_Bip_R_Shoulder",
    "right_upper_arm": "J_Bip_R_UpperArm",
    "right_lower_arm": "J_Bip_R_LowerArm",
    "right_hand": "J_Bip_R_Hand",
    "left_upper_leg": "J_Bip_L_UpperLeg",
    "left_lower_leg": "J_Bip_L_LowerLeg",
    "left_foot": "J_Bip_L_Foot",
    "left_toes": "J_Bip_L_ToeBase",
    "right_upper_leg": "J_Bip_R_UpperLeg",
    "right_lower_leg": "J_Bip_R_LowerLeg",
    "right_foot": "J_Bip_R_Foot",
    "right_toes": "J_Bip_R_ToeBase",
}

# ボーンの親子関係
BONE_HIERARCHY = {
    "hips": None,
    "spine": "hips",
    "chest": "spine",
    "upper_chest": "chest",
    "neck": "upper_chest",
    "head": "neck",
    "left_shoulder": "upper_chest",
    "left_upper_arm": "left_shoulder",
    "left_lower_arm": "left_upper_arm",
    "left_hand": "left_lower_arm",
    "right_shoulder": "upper_chest",
    "right_upper_arm": "right_shoulder",
    "right_lower_arm": "right_upper_arm",
    "right_hand": "right_lower_arm",
    "left_upper_leg": "hips",
    "left_lower_leg": "left_upper_leg",
    "left_foot": "left_lower_leg",
    "left_toes": "left_foot",
    "right_upper_leg": "hips",
    "right_lower_leg": "right_upper_leg",
    "right_foot": "right_lower_leg",
    "right_toes": "right_foot",
}

# ボーンの末端（tail）を次のボーンのheadにする対応
BONE_TAIL_TARGET = {
    "hips": "spine",
    "spine": "chest",
    "chest": "upper_chest",
    "upper_chest": "neck",
    "neck": "head",
    "head": "head_top",
    "left_shoulder": "left_upper_arm",
    "left_upper_arm": "left_lower_arm",
    "left_lower_arm": "left_hand",
    "right_shoulder": "right_upper_arm",
    "right_upper_arm": "right_lower_arm",
    "right_lower_arm": "right_hand",
    "left_upper_leg": "left_lower_leg",
    "left_lower_leg": "left_foot",
    "left_foot": "left_toes",
    "right_upper_leg": "right_lower_leg",
    "right_lower_leg": "right_foot",
    "right_foot": "right_toes",
}


def create_armature(bone_positions: dict):
    """VRMヒューマノイドArmatureを作成."""
    bpy.ops.object.armature_add(enter_editmode=True)
    armature_obj = bpy.context.active_object
    armature_obj.name = "VRM_Armature"
    armature = armature_obj.data
    armature.name = "VRM_Armature"

    # デフォルトボーンを削除
    for bone in armature.edit_bones:
        armature.edit_bones.remove(bone)

    # ボーンを作成
    edit_bones = {}
    for key, vrm_name in VRM_BONE_MAP.items():
        if key == "head_top":
            continue
        pos = bone_positions[key]
        bone = armature.edit_bones.new(vrm_name)
        bone.head = mathutils.Vector(pos)
        # tail は後で設定
        bone.tail = mathutils.Vector(pos) + mathutils.Vector((0, 0, 0.05))
        edit_bones[key] = bone

    # tail を次のボーンの head に設定
    for key, target_key in BONE_TAIL_TARGET.items():
        if key in edit_bones and target_key in bone_positions:
            edit_bones[key].tail = mathutils.Vector(bone_positions[target_key])

    # hand と toes は短いボーン（明確な tail ターゲットがない）
    for hand_key in ["left_hand", "right_hand"]:
        if hand_key in edit_bones:
            bone = edit_bones[hand_key]
            direction = (bone.head - edit_bones[hand_key.replace("hand", "lower_arm")].head).normalized()
            bone.tail = bone.head + direction * 0.08

    for toe_key in ["left_toes", "right_toes"]:
        if toe_key in edit_bones:
            bone = edit_bones[toe_key]
            bone.tail = bone.head + mathutils.Vector((0, -0.05, 0))

    # 親子関係を設定
    for key, parent_key in BONE_HIERARCHY.items():
        if parent_key and key in edit_bones and parent_key in edit_bones:
            edit_bones[key].parent = edit_bones[parent_key]
            # 体幹ボーンは connected
            if key in ("spine", "chest", "upper_chest", "neck", "head"):
                edit_bones[key].use_connect = True

    bpy.ops.object.mode_set(mode="OBJECT")
    return armature_obj


def parent_mesh_to_armature(mesh_obj, armature_obj):
    """メッシュをArmatureの子にして自動ウェイトを適用."""
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")


def setup_vrm_metadata(armature_obj):
    """VRM Addonが認識するメタデータを設定.

    VRM Addon for Blenderがインストールされている前提。
    """
    try:
        # VRM Addonのhumanoid設定
        vrm_props = getattr(armature_obj, "vrm_addon_extension", None)
        if vrm_props is None:
            print("WARNING: VRM Addon not found. Exporting as plain GLB with armature.")
            return False

        # VRM 1.0 humanoid bone mapping
        humanoid = vrm_props.vrm1.humanoid
        human_bones = humanoid.human_bones

        # VRM humanoid bone名 → Blenderボーン名の対応
        vrm_humanoid_map = {
            "hips": "J_Bip_C_Hips",
            "spine": "J_Bip_C_Spine",
            "chest": "J_Bip_C_Chest",
            "upperChest": "J_Bip_C_UpperChest",
            "neck": "J_Bip_C_Neck",
            "head": "J_Bip_C_Head",
            "leftShoulder": "J_Bip_L_Shoulder",
            "leftUpperArm": "J_Bip_L_UpperArm",
            "leftLowerArm": "J_Bip_L_LowerArm",
            "leftHand": "J_Bip_L_Hand",
            "rightShoulder": "J_Bip_R_Shoulder",
            "rightUpperArm": "J_Bip_R_UpperArm",
            "rightLowerArm": "J_Bip_R_LowerArm",
            "rightHand": "J_Bip_R_Hand",
            "leftUpperLeg": "J_Bip_L_UpperLeg",
            "leftLowerLeg": "J_Bip_L_LowerLeg",
            "leftFoot": "J_Bip_L_Foot",
            "leftToes": "J_Bip_L_ToeBase",
            "rightUpperLeg": "J_Bip_R_UpperLeg",
            "rightLowerLeg": "J_Bip_R_LowerLeg",
            "rightFoot": "J_Bip_R_Foot",
            "rightToes": "J_Bip_R_ToeBase",
        }

        for vrm_name, blender_name in vrm_humanoid_map.items():
            bone_prop = getattr(human_bones, vrm_name, None)
            if bone_prop is not None:
                bone_prop.node.bone_name = blender_name

        # VRMメタ情報
        meta = vrm_props.vrm1.meta
        meta.vrm_name = "Generated Character"
        meta.authors.clear()
        author = meta.authors.add()
        author.value = "MOTION LAB"
        meta.license_url = "https://vrm.dev/licenses/1.0/"

        return True
    except Exception as e:
        print(f"WARNING: VRM metadata setup failed: {e}")
        return False


def export_vrm(armature_obj, output_path: str):
    """VRMとしてエクスポート. 失敗時はGLBフォールバック."""
    bpy.ops.object.select_all(action="DESELECT")
    # Armatureとその子メッシュのみ選択
    armature_obj.select_set(True)
    for child in armature_obj.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj

    import os

    # VRM Addonのエクスポーターを試行
    vrm_exported = False
    try:
        bpy.ops.export_scene.vrm(filepath=output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"VRM exported: {output_path}")
            vrm_exported = True
        else:
            print("VRM export operator returned but file not created")
    except Exception as e:
        print(f"VRM export failed: {e}")

    if not vrm_exported:
        # GLBで出力
        print("Falling back to GLB export")
        glb_path = output_path.replace(".vrm", ".glb")
        bpy.ops.export_scene.gltf(
            filepath=glb_path,
            export_format="GLB",
            use_selection=True,
        )
        print(f"GLB exported: {glb_path}")


def main():
    args = parse_args()
    print("=== GLB→VRM Auto-Rigging ===")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")

    clear_scene()

    # 1. GLBインポート
    print("Importing GLB...")
    mesh_obj = import_glb(args.input)
    print(f"  Mesh: {mesh_obj.name}, verts={len(mesh_obj.data.vertices)}")

    # 2. ボーン位置推定
    print("Estimating bone positions...")
    bone_positions = estimate_bone_positions(mesh_obj)

    # 3. Armature作成
    print("Creating armature...")
    armature_obj = create_armature(bone_positions)

    # 4. メッシュをArmatureに関連付け
    print("Parenting mesh to armature (auto weights)...")
    parent_mesh_to_armature(mesh_obj, armature_obj)

    # 5. VRMメタデータ設定
    print("Setting up VRM metadata...")
    vrm_ok = setup_vrm_metadata(armature_obj)
    if vrm_ok:
        print("  VRM humanoid mapping configured")
    else:
        print("  VRM Addon not available, will export as rigged GLB")

    # 6. エクスポート
    print("Exporting...")
    export_vrm(armature_obj, args.output)
    print("=== Done ===")


if __name__ == "__main__":
    main()
