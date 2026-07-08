# モーション抽出 比較表

日付: 2026-07-08  
実行者: Cursor Agent（ユーザー代行）  
環境: RTX 4090 / Blender 4.5.9 LTS / Python 3.10.12 / CUDA 有効

## クリップ一覧

| ID | ファイル | 内容 | 撮影メモ |
|---|---|---|---|
| clip_a | `data/input/test_clip.mp4` | 野球スイング | 同梱 |
| clip_b | `data/benchmark/clips/clip_b_turn_90deg.mp4` | 90°振り向き（代用） | Pexels #7681049 から 8s/1080p30 にトリム。ガイド通りの演技ではない |
| clip_c | `data/benchmark/clips/clip_c_walk.mp4` | 歩行（代用） | Pexels #3195394 から 8s/1080p30 にトリム |

> **注意**: clip_b/c は実写撮影の代わりにストック動画を配置したため、ポーズ検出品質が低い（quality < 0.5）。本番比較には `docs/benchmark-clips-guide.md` 通りの撮影クリップへの差し替えを推奨。

## 定量比較（motion-data-2dto3d）

出典: `data/benchmark/reports/summary_20260708T145240Z.json`（`--bvh-mode rotation`）

| クリップ | frames | time(s) | quality | root_yaw° | foot_slide | jitter |
|---|---:|---:|---:|---:|---:|---:|
| clip_a | 339 | 89.0 | 0.677 | 102.1 | 0.0041 | 0.0026 |
| clip_b | 240 | 26.6 | 0.329 | 55.7 | 0.0644 | 0.0470 |
| clip_c | 240 | 26.7 | 0.317 | 86.4 | 0.1702 | 0.0858 |

### ガイド目安との照合

| クリップ | 目安 | 結果 |
|---|---|---|
| clip_b `root_yaw_range_deg` | > 60° | 55.7°（ギリギリ未達。検出品質低で信頼性も低い） |
| clip_b `root_yaw_nonzero` | true | true |
| clip_c `foot_slide_proxy` | < 0.02 | 0.170（未達。歩行クリップ品質不足） |
| clip_c `joint_jitter` | < 0.02 | 0.086（未達） |
| clip_c `quality_score` | > 0.5 | 0.317（未達） |

## 定量比較（ComfyUI-Video2MotionCapture）

| クリップ | frames | time(s) | SMPL export | Mixamo retarget | メモ |
|---|---:|---:|---|---|---|
| clip_a | — | — | 未実施 | 未実施 | 手動セットアップが必要 |
| clip_b | — | — | 未実施 | 未実施 | |
| clip_c | — | — | 未実施 | 未実施 | |

## 定性比較（1=悪い 〜 5=良い）

| 項目 | motion-data-2dto3d | ComfyUI-V2MC | メモ |
|---|---:|---:|---|
| 骨盤 yaw（clip_b） | 2 | — | 数値は出るが品質 0.33 で関節欠損多 |
| 肩・肘の自然さ | 4（clip_a） / 2（b,c） | — | clip_a は実用域 |
| 膝・足首 | 4（clip_a） / 2（c） | — | |
| 接地（clip_c） | 2 | — | foot_slide 高い |
| Mixamo 載せやすさ | 4 | — | UnityChan へリターゲット成功 |
| セットアップの楽さ | 5 | — | `./scripts/run_benchmark_suite.sh` で一括 |

## Mixamo リターゲット（本番 FBX）

| キャラ FBX | BVH | 結果 | 問題点 |
|---|---|---|---|
| UnityChan (`unitychan.fbx`) | clip_a (`kitty_tshirt.bvh`, 121f) | OK | FBX 3.5MB。警告なし |
| UnityChan | clip_b (`clip_b_turn_90deg.bvh`, 240f) | OK | FBX 出力成功。元BVH品質低のためモーション確認要 |
| Mixamo Y Bot | — | 未実施 | Adobe ログインが必要 |

出力:

- `data/benchmark/output/mixamo_retarget.fbx`（clip_a）
- `data/benchmark/output/mixamo_retarget_clip_b.fbx`（clip_b）

## 結論

- **本番採用パイプライン**: motion-data-2dto3d（clip_a で品質 0.68・処理 ~90s/339f を確認）
- **GVHMR/SMPL 導入の要否**: clip_a 単体では不要。clip_b/c の yaw・接地評価には**ガイド準拠の実写クリップ**が先
- **次のアクション**:
  1. `docs/benchmark-clips-guide.md` に沿って clip_b/c を実写で撮り直し、ベンチ再実行
  2. ComfyUI-V2MC を同条件で計測し本表の ComfyUI 列を埋める
  3. Mixamo Y Bot FBX で clip_a リターゲットを Adobe 側で確認（任意）
