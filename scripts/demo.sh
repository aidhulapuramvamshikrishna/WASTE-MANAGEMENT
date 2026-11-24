#!/usr/bin/env bash
# EcoSort Demo Script: 3-Minute Examiner Demonstration
# Usage: ./scripts/demo.sh
set -euo pipefail

echo "================================================================"
echo "  EcoSort: Municipal Solid Waste Classification (CNN + Grad-CAM)"
echo "  College Demonstration Runner"
echo "================================================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/5] Verifying environment & trained artifacts..."
test -f ml/artifacts/mobilenet_v3/best.pt || { echo "Error: MobileNetV3 model weights missing."; exit 1; }
test -f ml/artifacts/mobilenet_v3/metrics.json || { echo "Error: Metrics missing."; exit 1; }
test -d frontend/.next || { echo "Notice: Frontend not built yet. Building offline..."; (cd frontend && pnpm build); }

echo "[2/5] Starting FastAPI backend (port 8000)..."
(cd backend && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

cleanup() {
  echo ""
  echo "Shutting down servers..."
  kill "$BACKEND_PID" 2>/dev/null || true
  if [ -n "${FRONTEND_PID:-}" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Waiting for backend readiness..."
for i in {1..20}; do
  if curl -sf http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "[3/5] Starting Next.js production frontend (port 3000)..."
(cd frontend && NODE_ENV=production pnpm start) &
FRONTEND_PID=$!

echo "Waiting for frontend readiness..."
for i in {1..20}; do
  if curl -sf http://127.0.0.1:3000 >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "[4/5] Executing 3 Sample Demonstrations against Backend..."
SAMPLE_IMG="frontend/public/samples/cardboard_sample_01.jpg"
if [ ! -f "$SAMPLE_IMG" ]; then
  SAMPLE_IMG="$(find frontend/public/samples -name '*.jpg' | head -n 1)"
fi

echo "--> Sample 1: Confident Item Prediction ($SAMPLE_IMG)"
PRED_RES=$(curl -s -X POST http://127.0.0.1:8000/api/v1/predict \
  -F "file=@$SAMPLE_IMG;type=image/jpeg" \
  -F "model=mobilenet_v3")

PRED_ID=$(python3 -c "import json; print(json.loads('''$PRED_RES''')['id'])")
CLASS_NAME=$(python3 -c "import json; print(json.loads('''$PRED_RES''')['predicted_class'])")
CONF=$(python3 -c "import json; print(f\"{json.loads('''$PRED_RES''')['confidence']*100:.1f}%\")")
STREAM=$(python3 -c "import json; print(json.loads('''$PRED_RES''')['stream'])")
UNCERTAIN=$(python3 -c "import json; print(json.loads('''$PRED_RES''')['is_uncertain'])")

echo "    Result: ID=$PRED_ID | Class=$CLASS_NAME | Stream=$STREAM | Conf=$CONF | Uncertain=$UNCERTAIN"

echo "[5/5] All systems live! Demo navigation links ready:"
echo "----------------------------------------------------------------"
echo "  1. Live Web Console:       http://localhost:3000"
echo "  2. Inspection Heatmap:     http://localhost:3000/scan/$PRED_ID"
echo "  3. Operational History:    http://localhost:3000/history"
echo "  4. Municipal Insights:     http://localhost:3000/insights"
echo "  5. Model Benchmarks:       http://localhost:3000/model"
echo "  6. About & Methodology:    http://localhost:3000/about"
echo "  7. Interactive Swagger:    http://localhost:8000/docs (direct dev)"
echo "----------------------------------------------------------------"
echo "Press Ctrl+C to stop both servers."
wait
