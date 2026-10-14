# モーション抽出 比較表

日付: 2026-07-09（v4 更新）  
実行者: Cursor Agent（ユーザー代行）  
環境: RTX 4090 / Blender 4.5.9 LTS / Python 3.10.12 / ComfyUI V2MC pixi Py3.11

## クリップ一覧

| ID | ファイル | 内容 | 撮影メモ |
|---|---|---|---|
| clip_a | `data/input/test_clip.mp4` | 野球スイング | 同梱 |
| clip_b | `data/benchmark/clips/clip_b_turn_90deg.mp4` | 90°振り向き（代用 v2） | Pexels #9558217（白背景スタジオ） |
| clip_c | `data/benchmark/clips/clip_c_walk.mp4` | 歩行（Pexels 代用） | Pexels #5716913 |
| clip_c_ai | `data/benchmark/clips/clip_c_walk_ai.mp4` | 歩行（生成AI） | SD 1.5 + SVD。`scripts/generate_clip_c_ai.py` |

> **clip_c 実写**: WSL 環境にカメラなし（`/dev/video0` 未検出）。スマホ撮影 or USB パススルー後に `capture_benchmark_clip.sh` で差し替え推奨。生成AI版は接地指標が Pexels 代用より改善。

## 定量比較（motion-data-2dto3d）

出典: `summary_20260708T162133Z.json`（a/b/c Pexels）, `clip_c_walk_ai_20260708T220300Z.json`（c_ai）

| クリップ | frames | time(s) | quality | root_yaw° | foot_slide | jitter |
|---|---:|---:|---:|---:|---:|---:|
| clip_a | 339 | 84.0 | 0.677 | 102.1 | 0.0041 | 0.0026 |
| clip_b | 240 | 23.6 | **0.606** | **137.1** | 0.0026 | 0.0009 |
| clip_c | 240 | 25.5 | 0.413 | 53.4 | 0.981 | 0.228 |
| clip_c_ai | 240 | 23.0 | 0.461 | 110.6 | **0.062** | **0.024** |

## 定量比較（ComfyUI-Video2MotionCapture）

出典: `data/benchmark/reports/comfyui_test_clip_20260708T162504Z.json`  
条件: frame_cap=120, 全画面マスク proxy（SAM3 未使用）, static_camera=true

| クリップ | frames | time(s) | SMPL export | Mixamo retarget | メモ |
|---|---:|---:|---|---|---|
| clip_a | 120 | 178.1 | **OK** (NPZ) | FBX NG | 推論 27s + 初回モデルDL 151s。FBX は SMPL .pkl パス要調整 |
| clip_b | — | — | 未実施 | — | |
| clip_c | — | — | 未実施 | — | |

### clip_a 速度比較（参考）

| パイプライン | frames | 実効 time | 備考 |
|---|---:|---:|---|
| motion-data-2dto3d | 339 | 84s | quality 0.677, BVH 直接出力 |
| ComfyUI-V2MC | 120 | 178s（初回）/ ~27s（推論のみ） | SMPL NPZ 出力。初回は HF モデル DL 含む |

## 定性比較（1=悪い 〜 5=良い）

| 項目 | motion-data-2dto3d | ComfyUI-V2MC | メモ |
|---|---:|---:|---|
| 骨盤 yaw（clip_b） | **4** | — | quality 0.61・yaw 137° |
| 肩・肘の自然さ | 4（a/b） / 3（c） | 3（clip_a 目視未） | |
| 膝・足首 | 4（a/b） / 2（c） | — | |
| 接地（clip_c） | 2（Pexels）/ **3（AI）** | — | AI 版 foot_slide 0.06。実写が最優先 |
| Mixamo 載せやすさ | 4 | 3（推定） | V2MC は SMPL→Mixamo ノードあり |
| セットアップの楽さ | **5** | 2 | V2MC は ComfyUI+pixi+3.5GB |

## Mixamo リターゲット（本番 FBX）

| キャラ FBX | BVH | 結果 | 問題点 |
|---|---|---|---|
| UnityChan | clip_a (`kitty_tshirt.bvh`) | OK | |
| UnityChan | clip_b | OK | |
| Mixamo Y Bot | — | 未実施 | Adobe ログイン要 |

## 結論

- **本番採用**: motion-data-2dto3d（速度・セットアップ・BVH/Mixamo 出口が揃っている）
- **ComfyUI-V2MC の位置づけ**: SMPL メッシュ出口が必要な場合の比較対象。clip_a で NPZ 出力確認済み
- **clip_c 生成AI**: SD 1.5 + SVD で試行済み。Pexels 代用より foot_slide/jitter 改善（quality は依然 0.5 未満）
- **次のアクション**:
  1. **clip_c 実写** — スマホ or `capture_benchmark_clip.sh`（カメラ接続後）
  2. ComfyUI clip_b/c ベンチ（`FRAME_CAP=120 ./scripts/run_comfyui_v2mc_benchmark.sh ...`）
  3. V2MC FBX 出力 — `SMPL_MALE.npz` パス対応を確認

## ツール一覧

| スクリプト | 用途 |
|---|---|
| `scripts/validate_benchmark_clip.py` | クリップ事前検証 |
| `scripts/run_benchmark_suite.sh` | motion-data-2dto3d 一括ベンチ |
| `scripts/capture_benchmark_clip.sh` | clip_c 実写録画（8秒） |
| `scripts/generate_clip_c_ai.py` | clip_c 生成AI（SD 1.5 + SVD） |
| `scripts/setup_comfyui_v2mc.sh` | ComfyUI-V2MC セットアップ |
| `scripts/run_comfyui_v2mc_benchmark.sh` | ComfyUI GVHMR ベンチ |
