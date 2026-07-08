# ベンチマーク用クリップ

## 同梱クリップ

| ファイル | 説明 |
|---|---|
| `../../input/test_clip.mp4` | 野球スイング（clip_a） |

## 追加クリップ（ローカル配置）

撮影手順は **`docs/benchmark-clips-guide.md`** を参照。

| ID | 推奨ファイル名 | 目的 |
|---|---|---|
| clip_b | `clip_b_turn_90deg.mp4` | 骨盤 yaw |
| clip_c | `clip_c_walk.mp4` または `clip_c_jump.mp4` | 接地・足滑り |
| clip_c_ai | `clip_c_walk_ai.mp4`（任意） | 生成AI代用。`scripts/generate_clip_c_ai.py` |

配置先: このディレクトリ（`data/benchmark/clips/`）

## 一括ベンチ

```bash
chmod +x scripts/run_benchmark_suite.sh
./scripts/run_benchmark_suite.sh
```

存在しないクリップはスキップされます。

## 関連

- `docs/motion-benchmark.md` — ベンチ全体
- `docs/benchmark-clips-guide.md` — 撮影ガイド
- `data/benchmark/comparison_template.md` — 比較表テンプレート
