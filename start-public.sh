#!/bin/bash
# ローカルサーバーをCloudflare Tunnelで公開する
# 使い方: ./start-public.sh

set -e

PORT=7860
SERVER_PID=""

echo "=== Motion Data 2D→3D 公開サーバー ==="
echo ""

# 1. フロントエンドビルド（最新化）
echo "[1/3] フロントエンドをビルド中..."
(cd frontend && npm run build --silent 2>/dev/null)
echo "  ✓ ビルド完了"

# 2. サーバー起動（既に動いていればスキップ）
echo "[2/3] サーバーを確認中 (port: $PORT)..."
if lsof -i :$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "  ✓ サーバーは既に起動中"
else
  echo "  サーバーを起動します..."
  VME_HOST=0.0.0.0 VME_PORT=$PORT python -m video_motion_extraction.web &
  SERVER_PID=$!
  sleep 2
  if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "  ✗ サーバー起動失敗"
    exit 1
  fi
  echo "  ✓ サーバー起動完了 (PID: $SERVER_PID)"
fi

# 3. Cloudflare Tunnel で公開
echo "[3/3] Cloudflare Tunnel で公開中..."
echo ""
echo "========================================="
echo "  数秒後にURLが表示されます"
echo "  Ctrl+C で停止"
echo "========================================="
echo ""

trap "echo ''; echo 'シャットダウン中...'; [ -n \"$SERVER_PID\" ] && kill $SERVER_PID 2>/dev/null; exit 0" INT TERM

cloudflared tunnel --url http://localhost:$PORT
