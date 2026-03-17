# Cloudflare Tunnel によるローカル公開ガイド

## 概要

ローカルPCで動作するMotion Data 2D→3Dアプリケーションを、Cloudflare Tunnelを使ってインターネットに公開する手順をまとめたドキュメント。

ポートフォリオ用途の限定公開を想定しており、自宅PCから直接HTTPS公開できる。サーバー費用はかからない。

## アーキテクチャ

```
[ブラウザ] → https://xxx.trycloudflare.com → [Cloudflare] → [Tunnel] → localhost:7860
                                                                            ├── FastAPI (バックエンド)
                                                                            └── React (フロントエンド静的配信)
```

- FastAPIがポート7860でバックエンドAPIとフロントエンド(ビルド済みReact)を同時に配信
- Cloudflare Tunnelがローカルの7860番ポートをインターネットに公開
- HTTPS化はCloudflareが自動で行う

## 前提条件

### cloudflared のインストール

```bash
# インストール確認
cloudflared --version
# cloudflared version 2026.3.0

# 未インストールの場合（Ubuntu/WSL）
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared
```

### アプリケーション

- Node.js（フロントエンドビルド用）
- Python + FastAPI + 依存パッケージがインストール済み
- `frontend/` 配下の `npm run build` が通ること

## 公開方法（Quick Tunnel）

### 方法の選択について

Cloudflare Tunnelには2つの方式がある：

| 方式 | URL | 必要なもの | 用途 |
|------|-----|------------|------|
| **Quick Tunnel** | `https://xxx.trycloudflare.com`（毎回変わる） | cloudflaredのみ | ポートフォリオ、デモ |
| **Named Tunnel** | `https://自分のドメイン` | Cloudflareアカウント + ドメインのネームサーバー変更 | 本番運用 |

本プロジェクトでは **Quick Tunnel** を採用。理由：

- Cloudflareアカウント不要（ログイン不要）
- 既存ドメイン（cacc-lab.net）のDNS/ネームサーバー設定変更が不要
- 既存のウェブサイトやメールサーバーに一切影響しない
- コマンド1つで即座に公開可能

### Named Tunnel（カスタムドメイン）を使う場合の注意

カスタムドメイン（例: `motion.cacc-lab.net`）で公開したい場合は以下が必要：

1. Cloudflareダッシュボード（https://dash.cloudflare.com）でアカウント作成
2. 「サイトを追加」でドメインを登録（Freeプランで可）
3. Cloudflareが提示するネームサーバー2つを、ドメインレジストラ側で設定
4. `cloudflared tunnel login` でブラウザ認証
5. Named Tunnelを作成してドメインと紐付け

**重要**: ネームサーバーを変更すると、ドメインのDNS管理がCloudflareに移管される。既存のDNSレコード（A, CNAME, MX, TXTなど）はCloudflareが自動インポートするため、既存サービス（ウェブサイト、メール等）への影響はないが、以後のDNS管理はCloudflareダッシュボードで行うことになる。

## 使い方

### 起動

```bash
cd /home/ryu/projects/motion-data-2dto3d
./start-public.sh
```

出力例：

```
=== Motion Data 2D→3D 公開サーバー ===

[1/3] フロントエンドをビルド中...
  ✓ ビルド完了
[2/3] サーバーを確認中 (port: 7860)...
  ✓ サーバーは既に起動中
[3/3] Cloudflare Tunnel で公開中...

=========================================
  数秒後にURLが表示されます
  Ctrl+C で停止
=========================================

...
|  https://intelligent-because-notifications-powerseller.trycloudflare.com  |
```

表示されたURLをブラウザで開くか、共有相手に送る。

### スクリプトの動作

`start-public.sh` は以下を順番に実行する：

1. **フロントエンドビルド**: `frontend/` の React アプリを `npm run build` で最新化
2. **サーバー起動確認**: ポート7860が使用中ならスキップ、未起動なら `python -m video_motion_extraction.web` を起動
3. **Cloudflare Tunnel起動**: `cloudflared tunnel --url http://localhost:7860` でQuick Tunnelを開始

### 停止

```bash
# start-public.sh で起動した場合
Ctrl+C

# バックグラウンドで動いている場合
kill %1
```

### 注意事項

- **URLは毎回変わる**: Quick Tunnelは起動するたびに異なるURLが発行される。固定URLが必要な場合はNamed Tunnelを検討
- **PCの電源を切るとアクセス不可**: ローカルPCで動作しているため、PCがスリープ・シャットダウンするとアクセスできなくなる
- **GPU処理**: 動画からのモーション抽出にはGPU（CUDA）が必要。GPU非搭載PCではエラーになる可能性がある
- **同時アクセス**: Uvicornはシングルワーカーで動作しているため、大量の同時アクセスには向かない。ポートフォリオ用途であれば問題なし
- **アップタイム保証なし**: Quick Tunnelは実験用途であり、Cloudflareのサービス利用規約に従う。商用利用にはNamed Tunnelを推奨

## ファイル構成

```
motion-data-2dto3d/
├── start-public.sh          # 公開起動スクリプト
├── docs/
│   └── cloudflare-tunnel-setup.md  # このドキュメント
├── frontend/                # React フロントエンド
│   └── dist/                # ビルド成果物（FastAPIが配信）
└── src/video_motion_extraction/
    ├── web.py               # Uvicornエントリポイント（ポート7860）
    └── api/
        └── app.py           # FastAPIアプリ（CORS設定、静的ファイル配信）
```

## トラブルシューティング

### ポートが既に使用中

```
ERROR: [Errno 98] error while attempting to bind on address ('0.0.0.0', 7860): address already in use
```

→ `start-public.sh` は自動的に既存サーバーを検出してスキップするため、通常は問題にならない。手動でサーバーを再起動したい場合：

```bash
# 既存プロセスを確認
lsof -i :7860

# 停止してから再起動
kill <PID>
./start-public.sh
```

### cloudflaredが未インストール

```
./start-public.sh: line XX: cloudflared: command not found
```

→ 「前提条件」セクションのインストール手順を実行

### トンネルURLにアクセスできない

- 起動直後は数秒かかる場合がある。少し待ってからリロード
- ブラウザのキャッシュが古いURLを参照している可能性がある。URLをコピペして新しいタブで開く
- ローカルのFastAPIサーバーが停止している可能性がある。`curl http://localhost:7860` で確認

### フロントエンドの変更が反映されない

```bash
# 手動でフロントエンドを再ビルド
cd frontend && npm run build

# ブラウザでハードリロード（Ctrl+Shift+R）
```
