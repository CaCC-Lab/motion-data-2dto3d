# motion-data-2dto3d

動画から人体モーションデータを抽出し、2Dポーズ推定→データ補完・加工→3D変換を行うPythonツール。
野球バッターのスイングなどの動画を入力とし、BVH/FBX/JSON形式の3Dモーションデータを出力する。

## デモ

### Video → Skeleton → BVH Motion Data

入力動画から3Dスケルトンモーションデータへの変換結果:

https://github.com/user-attachments/assets/670b35fb-600f-470a-9938-2b8948bac0d3

### スケルトンレンダリング

BVHモーションデータからBlenderで生成した3Dスケルトンアニメーション:

https://github.com/user-attachments/assets/3ab7ef67-0e80-4b95-bc0e-e0f2e6d48b76

### パイプラインデモ

入力動画から3Dモーションデータ抽出までの全工程:

https://github.com/user-attachments/assets/07ce5dd8-6285-45dc-804a-c694f78bfd8d

> サンプル: 動画入力 → 2Dポーズ推定 → データ補完 → 3D変換 → BVH出力 → Blenderでアニメーション再生

## 処理パイプライン

```
動画 → VideoExtractor → PoseEstimator → DataProcessor → Converter3D → BVH/FBX/JSON
         (CPU/OpenCV)    (GPU/MMPose)      (CPU/SciPy)    (GPU/VideoPose3D)
```

| ステージ | コンポーネント | 処理内容 | 実行環境 |
|---|---|---|---|
| 1 | VideoExtractor | フレーム抽出・FPS調整 | CPU (OpenCV) |
| 2 | PoseEstimator | 2Dポーズ推定 (17関節) | GPU (MMPose/RTMPose) |
| 3 | DataProcessor | 欠損補完・スムージング | CPU (SciPy) |
| 4 | Converter3D | 2D→3D変換・エクスポート | GPU (VideoPose3D) |

## セットアップ

### 基本インストール

```bash
pip install -e .
```

### 開発用（テスト含む）

```bash
pip install -e ".[dev]"
```

### GPU推論に必要な依存関係

```bash
# PyTorch (CUDA)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# MMPose (2Dポーズ推定)
pip install -U openmim
mim install mmengine mmcv mmdet mmpose
pip install xtcocotools chumpy json-tricks munkres

# VideoPose3D モデル重み
# pretrained_h36m_cpn.bin を プロジェクトルートに配置
```

### 依存ライブラリ一覧

- Python >= 3.8
- NumPy >= 1.20.0, SciPy >= 1.7.0
- OpenCV >= 4.5.0
- Click >= 8.0
- PyTorch >= 1.10.0 + CUDA >= 11.0
- MMPose >= 1.0.0 (RTMPose)
- (GUI) Gradio >= 4.0

## 使い方

### CLI

```bash
# 基本的な変換（動画 → BVH）
vme input.mp4 -o output.bvh

# フォーマット指定（bvh/fbx/json）
vme input.mp4 -o output.fbx -f fbx

# パラメータ調整
vme input.mp4 -o output.bvh \
    --fps 30 \
    --threshold 0.3 \
    --smoothing 5 \
    --batch-size 32

# BVHモード指定（position: 位置ベース / rotation: 回転ベース）
vme input.mp4 -o output.bvh --bvh-mode position

# 3Dスムージング強度の調整（σ値、0で無効）
vme input.mp4 -o output.bvh --smooth-3d 1.0

# ルートモーション補正係数の調整（移動量のスケール）
vme input.mp4 -o output.bvh --root-motion-scale 2.5

# 不要な関節を除外（ワイルドカード対応）
vme input.mp4 -o output.bvh --remove-joints "left_hand_*,right_hand_*"

# 動画メタデータのみ表示
vme input.mp4 --info

# ヘルプ
vme --help
```

### CLI オプション一覧

| オプション | デフォルト | 説明 |
|---|---|---|
| `-o, --output` | (必須) | 出力ファイルパス |
| `-f, --format` | 自動判定 | 出力フォーマット (bvh/fbx/json) |
| `--fps` | 30.0 | ターゲットFPS |
| `--threshold` | 0.3 | 信頼度閾値 |
| `--smoothing` | 5 | スムージング窓サイズ |
| `--batch-size` | 32 | GPU バッチサイズ |
| `--bvh-mode` | position | BVH出力モード (position/rotation) |
| `--smooth-3d` | 1.0 | 3Dスムージングσ (0=無効) |
| `--root-motion-scale` | 2.5 | ルートモーション補正係数 (0.1〜10.0) |
| `--remove-joints` | なし | 除外する関節パターン (カンマ区切り) |
| `--device` | auto | 推論デバイス (auto/cpu/cuda/cuda:N) |
| `--strict / --no-strict` | 環境変数 `VME_STRICT` | 推論モデル未ロード時にエラー終了 |
| `--angular-velocity` | なし | 角速度データのJSON出力パス (指定時のみ算出) |
| `--info` | - | 動画メタデータのみ表示 |

### Web GUI (Gradio)

```bash
# 起動（ブラウザで http://localhost:7860 を開く）
vme-gui
```

動画をアップロードし、各種パラメータを設定して実行。処理完了後にBVHファイルをダウンロードできる。

### Python API

推奨: `MotionExtractor` によるパイプライン実行（CLI/GUI/Web APIと同一実装）。

```python
from video_motion_extraction import MotionExtractor, PipelineOptions

options = PipelineOptions(
    fps=30.0,
    threshold=0.3,
    smoothing=5,
    bvh_mode="position",
    smooth_3d=1.0,
    root_motion_scale=2.5,
    compute_angular_velocity=True,  # 角速度も算出する場合
    strict=True,                    # 本番: モデル未ロード時にエラー
    device="auto",                  # CUDA自動検出
)

extractor = MotionExtractor(options)
result = extractor.process("input.mp4")

print(f"quality score: {result.quality_score}")
extractor.export(result.motion_3d, "output.bvh", "bvh")
```

各コンポーネントを個別に使うことも可能:

```python
from video_motion_extraction import (
    VideoExtractor,
    PoseEstimator,
    DataProcessor,
    Converter3D,
    ProcessingConfig,
    Converter3DConfig,
)

# 1. 動画からフレーム抽出
extractor = VideoExtractor()
frames = extractor.extract_frames("input.mp4", target_fps=30.0)

# 2. 2Dポーズ推定
estimator = PoseEstimator()
pose_2d = estimator.estimate_2d_pose(frames, fps=30.0)

# 3. データ補完・加工
processor = DataProcessor(ProcessingConfig(
    confidence_threshold=0.3,
    smoothing_window=5,
))
pose_2d = processor.interpolate_missing(pose_2d)
pose_2d = processor.smooth_trajectory(pose_2d, window_size=5)

# 4. 3D変換 & エクスポート
converter = Converter3D(Converter3DConfig(
    bvh_mode="position",
    smooth_3d_sigma=1.0,
    root_motion_scale=2.5,
))
motion_3d = converter.convert_to_3d(pose_2d)
converter.export(motion_3d, "output.bvh", "bvh")
```

## 本番運用

### 環境変数

| 変数 | デフォルト | 説明 |
|---|---|---|
| `VME_STRICT` | (ローカル: 無効 / Docker: `1`) | 推論モデル未ロード時に `ModelNotAvailableError` で中断。スタブへのサイレントフォールバックを禁止 |
| `VME_DEVICE` | `auto` | 推論デバイス。`auto` はCUDA自動検出 |
| `VME_LOG_LEVEL` | `INFO` | ログレベル |
| `VME_LOG_FILE` | `logs/vme.log` | ローテーションログ出力先（空文字で無効、10MB×3世代） |
| `VME_HOST` / `VME_PORT` | `127.0.0.1` / `7860` | GUI/Web のバインド先 |
| `VME_UI` | `gui` | コンテナ起動モード（`gui` / `web`） |
| `VME_CORS_ORIGINS` | localhost:5173 | Web APIのCORS許可オリジン |

### ヘルスチェック

Web UIモード（`VME_UI=web`）では `/health` エンドポイントが利用できる。

```bash
curl http://localhost:7860/health
# {"status": "ok", "version": "0.1.0", "cuda_available": true, "videopose3d_weights": true}
```

DockerイメージにはHEALTHCHECKが組み込まれており、`docker ps` で状態を確認できる。

### 注意事項

- **FBXエクスポートは簡易ASCII形式**であり、DCCツール取り込みにはBVHを推奨
- モデル重みは `python scripts/download_weights.py` で取得（Dockerビルド時は自動実行、`--build-arg DOWNLOAD_WEIGHTS=0` でスキップ）
- Web APIのジョブ管理はインメモリ（単一プロセス前提）。マルチインスタンス構成にする場合は外部ジョブストアの導入が必要
- 公開運用時はリバースプロキシ等での認証・TLS終端を推奨（アプリ自体に認証機能はない）

### CI

GitHub Actions（`.github/workflows/ci.yml`）で以下を実行:

- `ruff check src/`（lint）
- `pytest -m "not gpu"`（Python 3.10 / 3.11）
- フロントエンドビルド（`npm ci && npm run build`）

## 統合ワークフロー（Integrate モード）

テキストまたは GLB と動画から、アニメーション付きキャラクター（GLB）を生成する一連のワークフロー。

### 前提

- motion API（`vme-web`、ポート 7860）
- Integration API（`vme-integration`、ポート 8090）
- （プロンプトモード時）text2image2model API（ポート 8080）
- Windows 側 Blender + VRM Addon（`BLENDER_PATH` で指定）

### 起動

```bash
# ターミナル1: Motion API
pip install -e ".[web,gpu]"
vme-web

# ターミナル2: Integration API
vme-integration

# ターミナル3: フロントエンド（開発）
cd frontend && npm run dev
```

Web UI の **Integrate** タブから GLB（またはプロンプト）と動画を指定してワークフローを開始する。
進捗は SSE でリアルタイム表示され、完了後にアニメーション GLB をプレビュー・ダウンロードできる。

### 環境変数（Integration）

| 変数 | デフォルト | 説明 |
|---|---|---|
| `T2I3D_API_URL` | `http://localhost:8080` | text2image2model API |
| `VME_API_URL` | `http://localhost:7860` | motion API |
| `BLENDER_PATH` | Windows Blender 4.3 | Blender 実行ファイル |
| `INTEGRATION_PORT` | `8090` | Integration API ポート |

### モーションベンチマーク

複数パイプライン（本ツール / ComfyUI-Video2MotionCapture 等）の比較手順:

```bash
python scripts/benchmark_motion.py data/input/test_clip.mp4 --bvh-mode rotation
```

詳細は `docs/motion-benchmark.md` を参照。

### BVH → Mixamo リターゲット

```bash
blender --background --python blender_scripts/retarget_bvh_to_mixamo.py -- \
  --bvh motion.bvh --target-fbx mixamo_character.fbx \
  --output-fbx animation.fbx
```

Integration API: `POST /api/integration/retarget-mixamo`

## Blenderでの確認方法

出力されたBVHファイルをBlenderで確認する手順:

### 1. BVHインポート

Blender を起動し、`File > Import > Motion Capture (.bvh)` からBVHファイルを読み込む。

### 2. スケルトン表示スクリプト

Blenderの Scripting ワークスペースで以下を実行すると、アニメーション付きスティックフィギュアが表示される:

```python
import bpy
from mathutils import Vector

# BVHインポート後のアーマチュアを取得
armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        armature = obj
        break

armature.hide_set(True)

# H36Mスケルトン接続定義
BONES = [
    ("Hip", "RHip"), ("RHip", "RKnee"), ("RKnee", "RFoot"),
    ("Hip", "LHip"), ("LHip", "LKnee"), ("LKnee", "LFoot"),
    ("Hip", "Spine"), ("Spine", "Thorax"),
    ("Thorax", "Nose"), ("Nose", "Head"),
    ("Thorax", "LShoulder"), ("LShoulder", "LElbow"), ("LElbow", "LWrist"),
    ("Thorax", "RShoulder"), ("RShoulder", "RElbow"), ("RElbow", "RWrist"),
]

# マテリアル作成
mat = bpy.data.materials.new("SkelMat")
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()
emit = nodes.new('ShaderNodeEmission')
emit.inputs['Color'].default_value = (0.0, 1.0, 0.4, 1.0)
emit.inputs['Strength'].default_value = 5.0
output = nodes.new('ShaderNodeOutputMaterial')
mat.node_tree.links.new(emit.outputs[0], output.inputs[0])

# ボーン(シリンダー)と関節(球)を作成
root = bpy.data.objects.new("SkeletonRoot", None)
bpy.context.collection.objects.link(root)

for pn, cn in BONES:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=1.0, vertices=8)
    cyl = bpy.context.active_object
    cyl.name = f"Bone_{pn}_{cn}"
    cyl.data.materials.append(mat)
    cyl.parent = root

for jn in sorted({j for pair in BONES for j in pair}):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.02, segments=12, ring_count=6)
    s = bpy.context.active_object
    s.name = f"Joint_{jn}"
    s.data.materials.append(mat)
    s.parent = root

# フレーム更新ハンドラ（アニメーション駆動）
def update_skeleton(scene, depsgraph=None):
    arm = bpy.data.objects.get(armature.name)
    if not arm:
        return
    positions = {pb.name: arm.matrix_world @ pb.head for pb in arm.pose.bones}

    for jn in {j for pair in BONES for j in pair}:
        s = bpy.data.objects.get(f"Joint_{jn}")
        if s and jn in positions:
            s.location = positions[jn]

    for pn, cn in BONES:
        cy = bpy.data.objects.get(f"Bone_{pn}_{cn}")
        if not cy or pn not in positions or cn not in positions:
            continue
        p1, p2 = positions[pn], positions[cn]
        diff = p2 - p1
        length = diff.length
        if length < 0.001:
            cy.hide_set(True)
            continue
        cy.hide_set(False)
        cy.location = (p1 + p2) / 2
        cy.scale = (1, 1, length)
        cy.rotation_mode = 'QUATERNION'
        cy.rotation_quaternion = Vector((0,0,1)).rotation_difference(diff.normalized())

bpy.app.handlers.frame_change_post.clear()
bpy.app.handlers.frame_change_post.append(update_skeleton)
update_skeleton(bpy.context.scene)
```

### 3. アニメーション再生

タイムラインで **Space** キーを押すとアニメーションが再生される。

## サンプルデータ

| ファイル | 説明 |
|---|---|
| `data/input/test_clip.mp4` | 入力サンプル: 野球バッターのスイング動画 |
| `data/output/batter_swing_v3.bvh` | 出力サンプル: 上記動画から生成した3Dモーションデータ (339フレーム, 17関節) |

## 出力フォーマット

| フォーマット | 拡張子 | 用途 |
|---|---|---|
| BVH | `.bvh` | モーションキャプチャ標準形式。Blender/Maya/MotionBuilder等で読み込み可 |
| FBX | `.fbx` | Unity/Unreal Engine等のゲームエンジン向け |
| JSON | `.json` | プログラムからの解析・加工用 |

### BVH出力モード

- **position** (デフォルト): 各関節の3D位置を直接記録。精度が高く、回転計算の誤差がない
- **rotation**: 関節回転(クォータニオン→Euler)で記録。一部のツールで必要な場合に使用

## プロジェクト構成

```
motion-data-2dto3d/
├── src/video_motion_extraction/
│   ├── cli.py              # CLIエントリポイント (click)
│   ├── gui.py              # Gradio WebUI
│   ├── video_extractor.py  # フレーム抽出 (OpenCV)
│   ├── pose_estimator.py   # 2Dポーズ推定 (MMPose/RTMPose)
│   ├── data_processor.py   # データ補完・スムージング
│   ├── converter_3d.py     # 2D→3D変換 (VideoPose3D) ・エクスポート
│   ├── videopose3d_model.py # VideoPose3Dモデル定義
│   ├── joint_mapping.py    # 関節マッピング (COCO↔H36M)
│   ├── quaternion_utils.py # クォータニオン計算ユーティリティ
│   ├── models.py           # データモデル
│   ├── config.py           # 設定クラス
│   ├── errors.py           # 例外定義
│   ├── validators.py       # 入力検証
│   ├── logger.py           # ロギング
│   ├── pipeline.py         # パイプライン統合（MotionExtractor）
│   ├── gpu_manager.py      # GPUリソース管理
│   ├── integration/        # 統合ワークフロー API
│   └── integration_web.py  # Integration API 起動
├── blender_scripts/        # Blender 自動リギング・リターゲティング
├── frontend/               # React Web UI
├── data/input/             # 入力動画
├── data/output/            # 出力ファイル (BVH/動画)
├── docs/                   # ドキュメント・画像
└── tests/                  # テスト
```

## テスト

```bash
# 全テスト実行
python -m pytest

# 詳細出力
python -m pytest -v

# GUI E2Eテスト（Playwright要、GPU不要テストのみ）
pip install playwright pytest-playwright
playwright install chromium
pytest tests/test_gui_e2e.py -m "not gpu" -v

# 全E2Eテスト（GPU環境）
pytest tests/test_gui_e2e.py -v
```

## ライセンス

MIT
