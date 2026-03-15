# AWS EC2 デプロイ手順

## 前提条件

- AWSアカウント
- EC2起動権限（g4dnインスタンス）

## 1. EC2インスタンスの起動

| 設定 | 値 |
|---|---|
| AMI | Deep Learning AMI GPU PyTorch (Ubuntu 22.04) |
| インスタンスタイプ | g4dn.xlarge |
| ストレージ | 50GB gp3 |
| セキュリティグループ | TCP 7860 (0.0.0.0/0), SSH 22 |

> Deep Learning AMIにはNVIDIAドライバ、Docker、NVIDIA Container Toolkitが全てプリインストール済み。

## 2. SSH接続

```bash
ssh -i your-key.pem ubuntu@<EC2のパブリックIP>
```

## 3. リポジトリのクローンとビルド

```bash
git clone https://github.com/CaCC-Lab/motion-data-2dto3d.git
cd motion-data-2dto3d

# モデル重みの配置（GitHubには含まれない場合）
# scp経由でアップロード or S3からダウンロード
# cp pretrained_h36m_cpn.bin src/video_motion_extraction/weights/

# Dockerイメージのビルド（初回10〜15分）
docker compose build
```

## 4. 起動

```bash
docker compose up -d
```

## 5. アクセス

ブラウザで `http://<EC2のパブリックIP>:7860` を開く。

## 6. 停止

```bash
docker compose down
```

## コスト目安

| リソース | 料金（東京リージョン） |
|---|---|
| g4dn.xlarge オンデマンド | 約 $0.71/時間 |
| 50GB gp3 | 約 $4.80/月 |
| **使用時のみ起動の場合** | **月30時間利用で約 $26** |

> 使わない時はインスタンスを停止すれば課金はストレージのみ。

## トラブルシューティング

### GPUが認識されない

```bash
nvidia-smi  # ドライバ確認
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi  # コンテナ内確認
```

### ポート7860にアクセスできない

- セキュリティグループでTCP 7860が許可されているか確認
- `docker compose logs` でエラーを確認
