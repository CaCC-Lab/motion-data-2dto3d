# Mixamo 本番リターゲット手順

BVH モーションを **本物のキャラクター FBX**（Mixamo / Unity ヒューマノイド）に載せる手順です。

## 対応リグ

`retarget_bvh_to_mixamo.py` は次のボーン命名を自動検出します。

| 形式 | 例 |
|---|---|
| Mixamo（標準） | `mixamorig:Hips`, `mixamorig:LeftArm` |
| Mixamo（無印） | `Hips`, `LeftArm` |
| Unity FBX | `Character1_Hips`, `Character1_LeftArm` |
| テストリグ | `blender_scripts/create_mixamo_test_rig.py` で生成 |

## 手順 A: Adobe Mixamo から FBX を取得（推奨）

1. [mixamo.com](https://www.mixamo.com/) にログイン（Adobe ID）
2. **Characters** からキャラを選ぶ（例: **Y Bot**, **X Bot**）
3. **Download** → Format: **FBX for Unity** または **FBX**、Pose: **T-pose**
4. 保存例: `~/Downloads/YBot.fbx`
5. プロジェクト外でも可（パスを指定するだけ）

> Mixamo の利用規約に従い、商用利用時は Adobe のライセンスを確認してください。

## 手順 B: ワンコマンドテスト

```bash
# 環境変数で Mixamo FBX を指定
export MIXAMO_FBX=~/Downloads/YBot.fbx
export BVH=data/output/kitty_tshirt.bvh   # または CLI で生成した BVH

./scripts/run_mixamo_retarget_test.sh
```

出力:

- `data/benchmark/output/mixamo_retarget.fbx`
- `data/benchmark/output/mixamo_retarget.blend`

## 手順 C: Blender で直接実行

```bash
blender --background --python blender_scripts/retarget_bvh_to_mixamo.py -- \
  --bvh data/output/kitty_tshirt.bvh \
  --target-fbx ~/Downloads/YBot.fbx \
  --output-fbx data/benchmark/output/ybot_anim.fbx \
  --output-blend data/benchmark/output/ybot_anim.blend
```

## 手順 D: Integration API

```bash
curl -X POST http://127.0.0.1:8090/api/integration/retarget-mixamo \
  -H 'Content-Type: application/json' \
  -d '{
    "bvh_path": "/absolute/path/to/motion.bvh",
    "target_fbx_path": "/absolute/path/to/YBot.fbx"
  }'
```

## 結果確認（Blender）

1. Blender を起動
2. `File > Import > FBX` で `mixamo_retarget.fbx` を読み込み
3. タイムラインで **Space** で再生
4. 確認ポイント:
   - 骨盤の向きがモーションと一致しているか
   - 膝・肘が不自然に折れていないか
   - 足が地面から浮きすぎ / 埋まりすぎしていないか

## 結果確認（Unity / UE）

- **Unity**: FBX をドラッグ＆ドロップ → Animation クリップを Preview
- **Unreal**: Import → Skeleton 互換を確認 → Animation エディタで再生

Mixamo キャラを使った場合、UE Mannequin への二次リターゲットも検討できます（将来の Export Hub 候補）。

## ローカル検証用（Mixamo FBX がない場合）

メッシュなしテストリグ:

```bash
blender --background --python blender_scripts/create_mixamo_test_rig.py -- \
  --output data/benchmark/fixtures/mixamo_test_rig.fbx
./scripts/run_mixamo_retarget_test.sh \
  data/benchmark/fixtures/mixamo_test_rig.fbx \
  data/output/kitty_tshirt.bvh
```

UnityChan 等のヒューマノイド FBX（`Character1_*` ボーン）でもスモークテスト可能です。

## トラブルシュート

| 症状 | 対処 |
|---|---|
| `Mixamo Hips bone not found` | FBX が T-pose リグ付きか確認。ボーン名が上表のいずれかか `blender` で確認 |
| 腕がねじれる | BVH が rotation モードか確認。`--bvh-mode rotation` で再抽出 |
| 足が滑る | `clip_c` ベンチの `foot_slide_proxy` を確認。`smooth_3d` を調整 |
| Blender not found | `export BLENDER_PATH=/path/to/blender`（WSL では Windows `.exe` も可） |

## 関連

- `docs/motion-benchmark.md`
- `scripts/run_mixamo_retarget_test.sh`
