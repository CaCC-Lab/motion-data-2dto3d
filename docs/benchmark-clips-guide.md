# ベンチマーク用クリップ撮影ガイド

`clip_b`（振り向き）と `clip_c`（歩行/ジャンプ）を撮影し、モーション抽出パイプラインの比較に使うためのガイドです。

## ファイル配置

撮影後、次のパスに配置してください（git には含めなくてよい）。

| ID | 推奨ファイル名 | パス |
|---|---|---|
| clip_a | （同梱済み） | `data/input/test_clip.mp4` |
| clip_b | `clip_b_turn_90deg.mp4` | `data/benchmark/clips/clip_b_turn_90deg.mp4` |
| clip_c | `clip_c_walk.mp4` または `clip_c_jump.mp4` | `data/benchmark/clips/` |

## 共通の撮影条件

- **全身が常にフレーム内**（頭〜足首）
- **10秒以内**（5〜8秒が理想）
- **30fps 以上**（スマホの 1080p30 で可）
- **1人のみ**映る（他の人・大きな動く物体は避ける）
- **背景はシンプル**（単色壁、コントラストがあると人物検出が安定）
- **カメラ固定**（三脚 or 置きっぱなし。手ブレは最小限に）
- **照明は均一**（強い逆光は避ける）

## clip_b: 90°振り向き（骨盤 yaw 用）

### 目的

ルート骨盤の **yaw（左右の向き）** が正しく復元されるかを見るクリップです。

### カメラ

- **正面またはやや斜め正面**（45°）から全身
- 振り向きが分かるよう、**腰〜肩の回転**が見える位置

### 演技手順（8秒例）

1. **0〜2秒**: T-pose に近い自然な立ち（正面を向く）
2. **2〜4秒**: その場で **右に90°** 振り向く（歩かない）
3. **4〜6秒**: 正面に戻る
4. **6〜8秒**: **左に90°** 振り向く

### 注意

- 足はできるだけ **その場で回転**（歩いて向きを変えない）
- 腕は体に近い自然な位置（大きく振らない）
- 速すぎる回転は避ける（1秒かけて90°程度）

### 期待されるベンチ結果（目安）

`--bvh-mode rotation` で:

- `root_yaw_range_deg` > **60°**
- `root_yaw_nonzero`: **true**

## clip_c: 歩行 or ジャンプ（接地・足滑り用）

### 目的

足の **接地・滑り（foot sliding）** と時間的な滑らかさを見るクリップです。

### パターン A: 歩行（推奨）

1. **0〜2秒**: 立ち
2. **2〜6秒**: カメラに向かって **4〜6歩** 歩く
3. **6〜8秒**: 立ち止まる

- カメラは正面、床と足首が見える高さ

### パターン B: ジャンプ

1. **0〜2秒**: 立ち
2. **2〜4秒**: その場で **小さめのジャンプ** 1〜2回
3. **4〜6秒**: 立ち

- 全身がフレーム外に出ないよう、カメラをやや引く

### 期待されるベンチ結果（目安）

- `foot_slide_proxy` < **0.02**（小さいほど良い）
- `joint_jitter` < **0.02**（小さいほど良い）
- `quality_score` > **0.5**

※ 絶対値は環境依存。重要なのは **clip_a/b/c 間の相対比較** と ComfyUI 版との比較です。

## ベンチ実行

```bash
# 事前検証（メタデータ + 任意でポーズ検出）
python scripts/validate_benchmark_clip.py data/benchmark/clips/clip_b_turn_90deg.mp4 --deep

# 一括（存在するクリップのみ実行）
./scripts/run_benchmark_suite.sh

# 手動
python scripts/benchmark_motion.py \
  data/input/test_clip.mp4 \
  data/benchmark/clips/clip_b_turn_90deg.mp4 \
  data/benchmark/clips/clip_c_walk.mp4 \
  --bvh-mode rotation
```

結果は `data/benchmark/reports/` に JSON で出力されます。

## ストック動画での代用（実写が難しい場合）

実写撮影の前にパイプラインを試す場合、Pexels 等の**全身・単色背景・1人のみ**の素材を 8秒/1080p30 にトリムして代用できます。

| ID | 推奨条件 | 代用例（2026-07-09 検証） |
|---|---|---|
| clip_b | その場で振り向き・白背景 | Pexels #9558217（スタジオ・全身・turn around） |
| clip_c | カメラに向かって歩行 | Pexels #5716913（全身・歩行） |

```bash
# 例: Pexels から取得（download リダイレクトを -L で追従）
curl -fsSL -A "Mozilla/5.0" -L -o /tmp/src.mp4 \
  "https://www.pexels.com/download/video/9558217/"
ffmpeg -y -ss 1 -t 8 -i /tmp/src.mp4 \
  -vf "scale=1920:1080,fps=30" -c:v libx264 -preset fast -crf 23 -an \
  data/benchmark/clips/clip_b_turn_90deg.mp4
```

**注意**: 代用素材でもガイド通りの演技でないと quality が 0.5 を下回ることがあります。本番比較は実写撮影を推奨します。

## 比較表の記入

`data/benchmark/comparison_template.md` をコピーし、ComfyUI-Video2MotionCapture 等の結果も併記してください。

## 関連

- `docs/motion-benchmark.md` — ベンチ全体の手順
- `scripts/run_benchmark_suite.sh` — 一括実行スクリプト
