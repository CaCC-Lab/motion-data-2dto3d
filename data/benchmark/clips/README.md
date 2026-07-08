# ベンチマーク用クリップ

## 同梱クリップ

| ファイル | 説明 |
|---|---|
| `../../input/test_clip.mp4` | 野球スイング（clip_a） |

## 追加推奨（手動配置）

以下はリポジトリに含めず、ローカルで用意してください。

| ID | 内容 | 目的 |
|---|---|---|
| clip_b | その場で90°振り向き（5〜10秒） | 骨盤 yaw 比較 |
| clip_c | 歩行 or ジャンプ（5〜10秒） | 接地・足滑り比較 |

実行例:

```bash
python scripts/benchmark_motion.py \
  data/input/test_clip.mp4 \
  /path/to/turn_90deg.mp4 \
  /path/to/walk.mp4 \
  --bvh-mode rotation
```

詳細は `docs/motion-benchmark.md` を参照。
