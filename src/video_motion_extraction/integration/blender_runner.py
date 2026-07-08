"""Blenderをサブプロセスとして実行するランナー."""

import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from video_motion_extraction.integration.config import BLENDER_PATH, SCRIPTS_DIR


def _to_win_path(posix_path: str) -> str:
    """WSLパスをWindows側Blenderが読めるパスに変換.

    /mnt/c/... → C:/...
    /home/... → \\\\wsl.localhost\\Ubuntu\\home\\...
    """
    p = str(posix_path)
    if p.startswith("/mnt/"):
        # /mnt/c/Users/... → C:/Users/...
        parts = p.split("/")
        drive = parts[2].upper()
        rest = "/".join(parts[3:])
        return f"{drive}:/{rest}"
    # WSL内部パス → UNCパス
    try:
        result = subprocess.run(
            ["wslpath", "-w", p],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return p


def _is_wsl_windows_blender() -> bool:
    """WSL上からWindows側Blenderを使っているか判定."""
    return (
        "microsoft" in platform.release().lower()
        and BLENDER_PATH.endswith(".exe")
    )


def _run_blender_script(
    script_name: str,
    args: List[str],
    timeout: int = 600,
) -> subprocess.CompletedProcess:
    """Blenderスクリプトをヘッドレスで実行."""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Blender script not found: {script_path}")

    blender = Path(BLENDER_PATH)
    if not blender.exists():
        raise FileNotFoundError(
            f"Blender not found at: {blender}\n"
            "Set BLENDER_PATH environment variable to the correct path."
        )

    # WSL→Windows Blenderの場合、全パスをWindows形式に変換
    use_win_paths = _is_wsl_windows_blender()

    script_str = _to_win_path(str(script_path)) if use_win_paths else str(script_path)

    if use_win_paths:
        # args内のファイルパス（--input, --output, --bvh, --vrm等の値）も変換
        converted_args = []
        for arg in args:
            if arg.startswith("/") and not arg.startswith("--"):
                converted_args.append(_to_win_path(arg))
            else:
                converted_args.append(arg)
        args = converted_args

    cmd = [
        str(blender),
        "--background",
        "--python", script_str,
        "--",
        *args,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Blender script failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout[-2000:] if result.stdout else ''}\n"
            f"stderr: {result.stderr[-2000:] if result.stderr else ''}"
        )

    return result


def rig_glb_to_vrm(input_glb: str, output_vrm: str, timeout: int = 300) -> str:
    """GLBメッシュを自動リギングしてVRM出力.

    Returns:
        出力ファイルパス
    """
    result = _run_blender_script(
        "rig_glb_to_vrm.py",
        ["--input", input_glb, "--output", output_vrm],
        timeout=timeout,
    )
    # VRM Addonがない場合は .glb にフォールバックされる
    vrm_path = Path(output_vrm)
    glb_fallback = vrm_path.with_suffix(".glb")
    if vrm_path.exists():
        return str(vrm_path)
    elif glb_fallback.exists():
        return str(glb_fallback)
    else:
        raise RuntimeError(
            f"Output file not found.\n"
            f"Expected: {output_vrm} or {glb_fallback}\n"
            f"Blender stdout:\n{result.stdout[-1500:]}\n"
            f"Blender stderr:\n{result.stderr[-500:] if result.stderr else '(none)'}"
        )


def retarget_bvh_to_vrm(
    bvh_path: str,
    vrm_path: str,
    output_glb: Optional[str] = None,
    output_blend: Optional[str] = None,
    timeout: int = 600,
) -> Dict[str, str]:
    """BVH→VRMリターゲティング + エクスポート.

    Returns:
        {"glb": path, "blend": path} の辞書（出力されたもののみ）
    """
    args = ["--bvh", bvh_path, "--vrm", vrm_path]
    if output_glb:
        args.extend(["--output-glb", output_glb])
    if output_blend:
        args.extend(["--output-blend", output_blend])

    _run_blender_script(
        "retarget_bvh_to_vrm.py",
        args,
        timeout=timeout,
    )

    outputs = {}
    if output_glb and Path(output_glb).exists():
        outputs["glb"] = output_glb
    if output_blend and Path(output_blend).exists():
        outputs["blend"] = output_blend

    if not outputs:
        raise RuntimeError("No output files generated")

    return outputs


def retarget_bvh_to_mixamo(
    bvh_path: str,
    target_fbx_path: str,
    output_fbx: Optional[str] = None,
    output_blend: Optional[str] = None,
    timeout: int = 600,
) -> Dict[str, str]:
    """BVH→Mixamo FBXリターゲティング + エクスポート.

    Returns:
        {"fbx": path, "blend": path} の辞書（出力されたもののみ）
    """
    args = ["--bvh", bvh_path, "--target-fbx", target_fbx_path]
    if output_fbx:
        args.extend(["--output-fbx", output_fbx])
    if output_blend:
        args.extend(["--output-blend", output_blend])

    _run_blender_script(
        "retarget_bvh_to_mixamo.py",
        args,
        timeout=timeout,
    )

    outputs: Dict[str, str] = {}
    if output_fbx and Path(output_fbx).exists():
        outputs["fbx"] = output_fbx
    if output_blend and Path(output_blend).exists():
        outputs["blend"] = output_blend

    if not outputs:
        raise RuntimeError("No output files generated")

    return outputs
