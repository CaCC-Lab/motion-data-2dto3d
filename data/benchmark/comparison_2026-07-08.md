# モーション抽出 比較表

日付: 2026-07-09（v2 更新）  
実行者: Cursor Agent（ユーザー代行）  
環境: RTX 4090 / Blender 4.5.9 LTS / Python 3.10.12 / CUDA 有効

## クリップ一覧

| ID | ファイル | 内容 | 撮影メモ |
|---|---|---|---|
| clip_a | `data/input/test_clip.mp4` | 野球スイング | 同梱 |
| clip_b | `data/benchmark/clips/clip_b_turn_90deg.mp4` | 90°振り向き（代用 v2） | Pexels #9558217（白背景スタジオ・全身 turn） |
| clip_c | `data/benchmark/clips/clip_c_walk.mp4` | 歩行（代用 v2） | Pexels #5716913（屋外・カメラに向かって歩行） |

> v1（#7681049 / #3195394）から素材を差し替え。clip_b はガイド目安をほぼ達成。clip_c はポーズ検出は良好だが 3D 品質・接地メトリクスは実写撮影が必要。

## 定量比較（motion-data-2dto3d）

出典: `data/benchmark/reports/summary_20260708T154815Z.json`（`--bvh-mode rotation`）

| クリップ | frames | time(s) | quality | root_yaw° | foot_slide | jitter |
|---|---:|---:|---:|---:|---:|---:|
| clip_a | 339 | 87.9 | 0.677 | 102.1 | 0.0041 | 0.0026 |
| clip_b | 240 | 24.9 | **0.606** | **137.1** | 0.0026 | 0.0009 |
| clip_c | 240 | 26.1 | 0.413 | 53.4 | 0.981 | 0.228 |

### v1 → v2 の変化

| クリップ | quality (v1→v2) | 主な改善/課題 |
|---|---|---|
| clip_a | 0.677 → 0.677 | 変化なし（基準） |
| clip_b | 0.329 → **0.606** | 素材差し替えで大幅改善。yaw 137°・foot_slide 0.003 |
| clip_c | 0.317 → 0.413 | 微改善。屋外・手持ち荷物で接地メトリクスは未達 |

### ガイド目安との照合

| クリップ | 目安 | 結果 |
|---|---|---|
| clip_b `root_yaw_range_deg` | > 60° | **137.1° 達成** |
| clip_b `root_yaw_nonzero` | true | true |
| clip_b `quality_score` | > 0.5 | **0.606 達成** |
| clip_c `foot_slide_proxy` | < 0.02 | 0.981（未達。屋外歩行＋カメラ移動の影響） |
| clip_c `joint_jitter` | < 0.02 | 0.228（未達） |
| clip_c `quality_score` | > 0.5 | 0.413（未達） |

### 事前検証（validate_benchmark_clip.py --deep）

| クリップ | detection_rate | avg_confidence |
|---|---:|---:|
| clip_b | 100% | 0.66 |
| clip_c | 100% | 0.64 |

## 定量比較（ComfyUI-Video2MotionCapture）

| クリップ | frames | time(s) | SMPL export | Mixamo retarget | メモ |
|---|---:|---:|---|---|---|
| clip_a | — | — | セットアップ中 | — | ノード clone 済み。モデル DL は `scripts/setup_comfyui_v2mc.sh` |
| clip_b | — | — | 未実施 | 未実施 | |
| clip_c | — | — | 未実施 | 未実施 | |

**セットアップ状況（2026-07-09）**:
- ComfyUI 本体: `/home/ryu/ComfyUI/`
- カスタムノード: clone 済み（`custom_nodes/ComfyUI-Video2MotionCapture`）
- モデル DL: `comfy-env` バージョン不整合で要手動調整（requirements の 0.1.79 は PyPI 非公開）

## 定性比較（1=悪い 〜 5=良い）

| 項目 | motion-data-2dto3d | ComfyUI-V2MC | メモ |
|---|---:|---:|---|
| 骨盤 yaw（clip_b） | **4** | — | quality 0.61・yaw 137° |
| 肩・肘の自然さ | 4（clip_a/b） / 3（c） | — | |
| 膝・足首 | 4（a/b） / 2（c） | — | |
| 接地（clip_c） | 2 | — | ストック動画の限界 |
| Mixamo 載せやすさ | 4 | — | UnityChan リターゲット成功済み |
| セットアップの楽さ | 5 | 2（推定） | V2MC は ComfyUI+Blender+3.5GB モデル |

## Mixamo リターゲット（本番 FBX）

| キャラ FBX | BVH | 結果 | 問題点 |
|---|---|---|---|
| UnityChan | clip_a (`kitty_tshirt.bvh`) | OK | FBX 3.5MB |
| UnityChan | clip_b (`clip_b_turn_90deg.bvh`) | OK | FBX 3.5MB |
| Mixamo Y Bot | — | 未実施 | Adobe ログインが必要 |

## 結論

- **本番採用パイプライン**: motion-data-2dto3d（clip_a スイング + clip_b 振り向きで確認済み）
- **GVHMR/SMPL 導入の要否**: clip_a/b では不要。clip_c 接地評価と ComfyUI 比較のため V2MC セットアップを継続
- **次のアクション**:
  1. clip_c をガイド通り**実写撮影**（屋内・カメラ固定・床が見える）
  2. ComfyUI-V2MC モデル DL 完了後、clip_a で SMPL ベンチ
  3. 比較表の ComfyUI 列を埋める

## 追加ツール（v2 で導入）

| スクリプト | 用途 |
|---|---|
| `scripts/validate_benchmark_clip.py` | クリップ事前検証（ffprobe + ポーズ検出） |
| `scripts/setup_comfyui_v2mc.sh` | ComfyUI-V2MC セットアップ |
