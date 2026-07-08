"""Mixamo互換の最小テストリグを生成してFBX出力.

CI/ローカルで Mixamo リターゲットのスモークテストに使う。
メッシュなしの Armature のみ。

Usage:
    blender --background --python create_mixamo_test_rig.py -- \
        --output data/benchmark/fixtures/mixamo_test_rig.fbx
"""

import argparse
import sys
from mathutils import Vector

import bpy


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="data/benchmark/fixtures/mixamo_test_rig.fbx",
        help="出力FBXパス",
    )
    return parser.parse_args(argv)


# (name, parent, head, tail) — Mixamo 命名
BONES = [
    ("mixamorig:Hips", None, (0, 1.0, 0), (0, 1.1, 0)),
    ("mixamorig:Spine", "mixamorig:Hips", (0, 1.1, 0), (0, 1.25, 0)),
    ("mixamorig:Spine1", "mixamorig:Spine", (0, 1.25, 0), (0, 1.4, 0)),
    ("mixamorig:Spine2", "mixamorig:Spine1", (0, 1.4, 0), (0, 1.55, 0)),
    ("mixamorig:Neck", "mixamorig:Spine2", (0, 1.55, 0), (0, 1.65, 0)),
    ("mixamorig:Head", "mixamorig:Neck", (0, 1.65, 0), (0, 1.8, 0)),
    ("mixamorig:LeftShoulder", "mixamorig:Spine2", (0, 1.5, 0), (0.15, 1.5, 0)),
    ("mixamorig:LeftArm", "mixamorig:LeftShoulder", (0.15, 1.5, 0), (0.35, 1.5, 0)),
    ("mixamorig:LeftForeArm", "mixamorig:LeftArm", (0.35, 1.5, 0), (0.55, 1.5, 0)),
    ("mixamorig:LeftHand", "mixamorig:LeftForeArm", (0.55, 1.5, 0), (0.7, 1.5, 0)),
    ("mixamorig:RightShoulder", "mixamorig:Spine2", (0, 1.5, 0), (-0.15, 1.5, 0)),
    ("mixamorig:RightArm", "mixamorig:RightShoulder", (-0.15, 1.5, 0), (-0.35, 1.5, 0)),
    ("mixamorig:RightForeArm", "mixamorig:RightArm", (-0.35, 1.5, 0), (-0.55, 1.5, 0)),
    ("mixamorig:RightHand", "mixamorig:RightForeArm", (-0.55, 1.5, 0), (-0.7, 1.5, 0)),
    ("mixamorig:LeftUpLeg", "mixamorig:Hips", (0.1, 1.0, 0), (0.1, 0.55, 0)),
    ("mixamorig:LeftLeg", "mixamorig:LeftUpLeg", (0.1, 0.55, 0), (0.1, 0.1, 0)),
    ("mixamorig:LeftFoot", "mixamorig:LeftLeg", (0.1, 0.1, 0), (0.1, 0.0, 0.1)),
    ("mixamorig:RightUpLeg", "mixamorig:Hips", (-0.1, 1.0, 0), (-0.1, 0.55, 0)),
    ("mixamorig:RightLeg", "mixamorig:RightUpLeg", (-0.1, 0.55, 0), (-0.1, 0.1, 0)),
    ("mixamorig:RightFoot", "mixamorig:RightLeg", (-0.1, 0.1, 0), (-0.1, 0.0, 0.1)),
]


def main():
    args = parse_args()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    arm_data = bpy.data.armatures.new("MixamoTestArmature")
    arm_obj = bpy.data.objects.new("MixamoTest", arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = arm_data.edit_bones
    for name, parent, head, tail in BONES:
        bone = edit_bones.new(name)
        bone.head = Vector(head)
        bone.tail = Vector(tail)
        if parent and parent in edit_bones:
            bone.parent = edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")

    for bone in arm_obj.pose.bones:
        bone.rotation_mode = "QUATERNION"

    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.export_scene.fbx(
        filepath=args.output,
        use_selection=True,
        add_leaf_bones=False,
        armature_nodetype="NULL",
    )
    print(f"Mixamo test rig exported: {args.output}")


if __name__ == "__main__":
    main()
