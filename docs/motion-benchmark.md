# モーション抽出ベンチマーク

動画から3Dモーションを抽出する複数パイプライン（**motion-data-2dto3d** / **ComfyUI-Video2MotionCapture** 等）を、同じ入力動画で比較するための手順書です。

## 目的

- 品質（骨盤向き・手足・接地）を定性的・定量的に比較する
- 処理時間・依存の重さを記録する
- 「どの出口（BVH / VRM / Mixamo / UE）に載せやすいか」を判断する

## 推奨テストクリップ（3本）

| ID | ファイル | 内容 | 見るポイント |
|---|---|---|---|
| `clip_a` | `data/input/test_clip.mp4` | 野球スイング（既存サンプル） | 高速回転・上半身ツイスト・体重移動 |
| `clip_b` | 自作: その場で90°振り向き（5〜10秒） | 任意パス | **骨盤 yaw** の復元 |
| `clip_c` | 自作: 歩行 or ジャンプ（5〜10秒） | 任意パス | **接地・足滑り** |

`clip_b` / `clip_c` はスマホ撮影で十分です。詳細は **`docs/benchmark-clips-guide.md`** を参照。

一括実行:

```bash
# 事前検証
python scripts/validate_benchmark_clip.py data/benchmark/clips/*.mp4 --deep

./scripts/run_benchmark_suite.sh
```

ComfyUI 比較のセットアップ:

```bash
./scripts/setup_comfyui_v2mc.sh
```

## 自動ベンチ（motion-data-2dto3d）

```bash
# 依存（GPU推論する場合）
pip install -e ".[gpu,web]"

# 単一動画
python scripts/benchmark_motion.py data/input/test_clip.mp4

# 複数動画 + rotation BVH で root yaw も計測
python scripts/benchmark_motion.py \
  data/input/test_clip.mp4 \
  /path/to/turn_90deg.mp4 \
  --bvh-mode rotation \
  --output-dir data/benchmark/reports
```

出力: `data/benchmark/reports/<clip_stem>_<timestamp>.json`

### 収集メトリクス

| メトリクス | 説明 |
|---|---|
| `processing_time_sec` | パイプライン全体の所要時間 |
| `frame_count` | 出力フレーム数 |
| `quality_score` | Converter3D の品質スコア（0〜1） |
| `root_yaw_range_deg` | BVH root Y 回転の幅（rotation モード時） |
| `foot_slide_proxy` | 足首高さ差分の平均（小さいほど滑りが少ない目安） |
| `joint_jitter` | 主要関節速度の変動（小さいほど滑らか） |

## 手動ベンチ（ComfyUI-Video2MotionCapture）

[ComfyUI-Video2MotionCapture](https://github.com/AKASubaz/ComfyUI-Video2MotionCapture) は ComfyUI ノードとして動かす前提です。

1. ComfyUI + カスタムノード + Blender 4.0+ をセットアップ
2. 上記3クリップを同じ解像度・FPS目安で入力
3. `GVHMRInference` → `SaveSMPLAsRiggedFBX`（必要なら `RetargetSMPLToMixamo`）
4. 下記チェックリストを `data/benchmark/reports/comfyui_<clip>_<date>.md` に記録

### 定性チェックリスト（5段階: 1=悪い 〜 5=良い）

| 項目 | motion-data-2dto3d | ComfyUI-V2MC | メモ |
|---|---|---|---|
| 骨盤 yaw（振り向き） | | | |
| 肩・肘の自然さ | | | |
| 膝・足首の自然さ | | | |
| 接地（足滑り） | | | |
| Mixamo/UE への載せやすさ | | | |
| セットアップの楽さ | | | |

## 出口比較（リターゲット）

motion-data-2dto3d 側の出口:

```bash
# BVH 抽出（CLI）
python -m video_motion_extraction.cli data/input/test_clip.mp4 \
  --output /tmp/out.bvh --format bvh --bvh-mode rotation

# BVH → VRM（既存）
blender --background --python blender_scripts/retarget_bvh_to_vrm.py -- \
  --bvh /tmp/out.bvh --vrm model.vrm --output-glb /tmp/anim.glb

# BVH → Mixamo FBX（新規）
blender --background --python blender_scripts/retarget_bvh_to_mixamo.py -- \
  --bvh /tmp/out.bvh --target-fbx mixamo_character.fbx \
  --output-fbx /tmp/anim_mixamo.fbx
```

Integration API:

```bash
curl -X POST http://127.0.0.1:8090/api/integration/retarget-mixamo \
  -H 'Content-Type: application/json' \
  -d '{"bvh_path": "/path/to/motion.bvh", "target_fbx_path": "/path/to/character.fbx"}'
```

スモークテスト（テストリグ生成 → リターゲット）:

```bash
blender --background --python blender_scripts/create_mixamo_test_rig.py -- \
  --output data/benchmark/fixtures/mixamo_test_rig.fbx

blender --background --python blender_scripts/retarget_bvh_to_mixamo.py -- \
  --bvh data/output/kitty_tshirt.bvh \
  --target-fbx data/benchmark/fixtures/mixamo_test_rig.fbx \
  --output-fbx data/benchmark/output/test_mixamo.fbx
```

## 判断ガイド

| 状況 | おすすめ |
|---|---|
| Web API・本番運用・VRM/Blender | **motion-data-2dto3d** |
| Mixamo / UE Mannequin 直行 | **Mixamo リターゲット**（本リポジトリ）＋ ComfyUI版をベンチ参照 |
| メッシュ付き SMPL・研究用途 | ComfyUI-V2MC（**ライセンス確認後**） |
| 商用案件 | SMPL/GVHMR は利用規約を必ず確認。安全策は BVH + 自前 Blender リターゲット |

## ライセンス注意

- **motion-data-2dto3d**: MIT（本リポジトリ）
- **ComfyUI-Video2MotionCapture**: リポジトリ表示と README でライセンス表記が食い違う可能性あり
- **SMPL / GVHMR チェックポイント**: 研究・非商用制限の可能性 — 商用前に必ず確認

## 関連ファイル

- `scripts/benchmark_motion.py` — 自動計測スクリプト
- `blender_scripts/retarget_bvh_to_mixamo.py` — BVH→Mixamo FBX
- `data/benchmark/reports/` — 計測結果（gitignore）
