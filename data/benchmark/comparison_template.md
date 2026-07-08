# モーション抽出 比較表（テンプレート）

日付: YYYY-MM-DD  
実行者:  
環境: GPU / Blender バージョン / Python バージョン

## クリップ一覧

| ID | ファイル | 内容 | 撮影メモ |
|---|---|---|---|
| clip_a | `data/input/test_clip.mp4` | 野球スイング | 同梱 |
| clip_b | `data/benchmark/clips/clip_b_turn_90deg.mp4` | 90°振り向き | |
| clip_c | `data/benchmark/clips/clip_c_walk.mp4` | 歩行 | |

## 定量比較（motion-data-2dto3d）

`data/benchmark/reports/*.json` から転記

| クリップ | frames | time(s) | quality | root_yaw° | foot_slide | jitter |
|---|---:|---:|---:|---:|---:|---:|
| clip_a | | | | | | |
| clip_b | | | | | | |
| clip_c | | | | | | |

## 定量比較（ComfyUI-Video2MotionCapture）

| クリップ | frames | time(s) | SMPL export | Mixamo retarget | メモ |
|---|---:|---:|---|---|---|
| clip_a | | | | | |
| clip_b | | | | | |
| clip_c | | | | | |

## 定性比較（1=悪い 〜 5=良い）

| 項目 | motion-data-2dto3d | ComfyUI-V2MC | メモ |
|---|---:|---:|---|
| 骨盤 yaw（clip_b） | | | |
| 肩・肘の自然さ | | | |
| 膝・足首 | | | |
| 接地（clip_c） | | | |
| Mixamo 載せやすさ | | | |
| セットアップの楽さ | | | |

## Mixamo リターゲット（本番 FBX）

| キャラ FBX | BVH | 結果 | 問題点 |
|---|---|---|---|
| Y Bot.fbx | clip_a | OK / NG | |
| | clip_b | | |

## 結論

- 本番採用パイプライン:
- GVHMR/SMPL 導入の要否:
- 次のアクション:
