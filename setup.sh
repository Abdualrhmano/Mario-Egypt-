#!/usr/bin/env bash
set -euo pipefail

# setup.sh - Robust setup for King Khufu frontend + backend
# - Creates frontend Vite app if missing
# - Installs required backend and frontend deps
# - Configures Tailwind/PostCSS correctly (uses @tailwindcss/postcss)
# - Writes safe src/main.jsx (avoids duplicate imports)
# - Integrates optional frontend_game.jsx if present (without duplicating imports)
# - Starts backend (uvicorn) in background and then starts frontend dev server
#
# Usage: bash setup.sh
# Note: Ensure Python, pip, Node (>=16), npm are installed.

ROOT_DIR="$(pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
ENV_FILE="$ROOT_DIR/.env"

echo "🔧 Starting setup at $(date)"
echo "Project root: $ROOT_DIR"

# -------------------------
# 0. Basic checks
# -------------------------
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 not found in PATH"; exit 1; }
command -v pip >/dev/null 2>&1 || { echo "❌ pip not found in PATH"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ node not found in PATH"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm not found in PATH"; exit 1; }

# -------------------------
# 1. Backend Python deps
# -------------------------
echo "📦 Installing backend Python packages (fastapi, uvicorn, sqlalchemy, auth libs)..."
# Use --upgrade to ensure latest compatible versions
pip install --upgrade fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] pydantic pydantic-settings websockets python-multipart >/dev/null 2>&1 || {
  echo "⚠️ pip install had warnings/errors (continuing)"; 
}

# -------------------------
# 2. Ensure .env exists with JWT secret
# -------------------------
if [ ! -f "$ENV_FILE" ]; then
  echo "🔐 Creating .env with a default JWT secret (please change for production)..."
  cat > "$ENV_FILE" <<EOF
KHUFU_JWT_SECRET="ENGINEER_ABDULRAHMAN_KHUFU_PRO_2026"
KHUFU_DATABASE_URL="sqlite:///./khufu.db"
# Optional: REDIS_URL="redis://localhost:6379/0"
EOF
else
  echo "✅ .env already exists"
fi

# -------------------------
# 3. Create frontend app if missing
# -------------------------
if [ ! -d "$FRONTEND_DIR" ]; then
  echo "🏗️ Creating Vite React frontend in ./frontend ..."
  npm create vite@latest frontend --yes -- --template react >/dev/null 2>&1
  echo "✅ Frontend scaffolded"
else
  echo "✅ Frontend directory exists"
fi

cd "$FRONTEND_DIR"

# -------------------------
# 4. Install frontend deps
# -------------------------
echo "📦 Installing frontend dependencies (axios, jwt-decode, react-router-dom, lucide-react)..."
npm install --silent axios jwt-decode react-router-dom lucide-react >/dev/null 2>&1 || {
  echo "⚠️ npm install (runtime deps) had warnings/errors (continuing)";
}

echo "📦 Installing Tailwind/PostCSS dev dependencies..."
npm install --silent -D tailwindcss postcss autoprefixer @tailwindcss/postcss >/dev/null 2>&1 || {
  echo "⚠️ npm install (dev deps) had warnings/errors (continuing)";
}

# -------------------------
# 5. Write PostCSS & Tailwind config (idempotent)
# -------------------------
echo "🎨 Writing postcss.config.js and tailwind.config.js (safe overwrite)..."

cat > postcss.config.js <<'EOF'
export default {
  plugins: {
    "@tailwindcss/postcss": {},
    autoprefixer: {},
  },
}
EOF

cat > tailwind.config.js <<'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        khufuBg: "#07070a",
        khufuGold: "#f6c85f",
      }
    }
  },
  plugins: [],
}
EOF

# -------------------------
# 6. Ensure src and index.css exist
# -------------------------
mkdir -p src

if [ ! -f src/index.css ]; then
  cat > src/index.css <<'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Basic dark theme + gold accents */
:root {
  --khufu-bg: #07070a;
  --khufu-gold: #f6c85f;
}
body {
  @apply bg-khufuBg text-white min-h-screen;
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
}
EOF
  echo "✅ src/index.css created"
else
  echo "✅ src/index.css already exists"
fi

# -------------------------
# 7. Prepare src/main.jsx safely (avoid duplicate imports)
# -------------------------
MAIN_FILE="src/main.jsx"
BACKUP_MAIN="${MAIN_FILE}.bak"

echo "🧩 Ensuring src/main.jsx is present and clean (no duplicate imports)..."

# If user has frontend_game.jsx in project root, integrate it safely
ROOT_FRONTEND_GAME="$ROOT_DIR/frontend_game.jsx"
INTEGRATED_GAME="src/frontend_game.jsx"

if [ -f "$ROOT_FRONTEND_GAME" ]; then
  echo "🔁 Found frontend_game.jsx at project root — copying to $INTEGRATED_GAME"
  cp "$ROOT_FRONTEND_GAME" "$INTEGRATED_GAME"
fi

# If main.jsx exists, back it up
if [ -f "$MAIN_FILE" ]; then
  echo "📦 Backing up existing $MAIN_FILE to $BACKUP_MAIN"
  cp "$MAIN_FILE" "$BACKUP_MAIN"
fi

# Write a clean main.jsx that avoids duplicate imports and is idempotent
cat > "$MAIN_FILE" <<'EOF'
import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

const rootEl = document.getElementById("root");
if (!rootEl) {
  const el = document.createElement("div");
  el.id = "root";
  document.body.appendChild(el);
}
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
EOF

echo "✅ src/main.jsx written"

# -------------------------
# 8. Provide a minimal App.jsx if missing (single-file safe fallback)
# -------------------------
APP_FILE="src/App.jsx"
if [ ! -f "$APP_FILE" ]; then
  echo "🧩 Creating minimal src/App.jsx (you can replace with full UI later)..."
  cat > "$APP_FILE" <<'EOF'
import React from "react";
import { Routes, Route, Link } from "react-router-dom";
import Leaderboard from "./components/Leaderboard";

export default function App() {
  return (
    <div className="min-h-screen bg-khufuBg text-white">
      <header className="p-4 border-b border-gray-800">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-yellow-400 to-amber-600 flex items-center justify-center text-black font-bold">K</div>
            <div>
              <div className="font-bold">King Khufu Adventure</div>
              <div className="text-xs text-slate-400">Ancient Egypt meets modern gaming</div>
            </div>
          </div>
          <nav className="space-x-4">
            <Link to="/leaderboard" className="text-slate-300">Leaderboard</Link>
          </nav>
        </div>
      </header>

      <main className="container mx-auto p-6">
        <Routes>
          <Route path="/" element={<div>Welcome to King Khufu Adventure</div>} />
          <Route path="/leaderboard" element={<Leaderboard />} />
        </Routes>
      </main>
    </div>
  );
}
EOF
  echo "✅ src/App.jsx created"
else
  echo "✅ src/App.jsx already exists"
fi

# -------------------------
# 9. Create a simple Leaderboard component if missing
# -------------------------
mkdir -p src/components
LB_FILE="src/components/Leaderboard.jsx"
if [ ! -f "$LB_FILE" ]; then
  cat > "$LB_FILE" <<'EOF'
import React, { useEffect, useState } from "react";

export default function Leaderboard() {
  const [players, setPlayers] = useState([]);
  useEffect(() => {
    async function fetchLB() {
      try {
        const res = await fetch("/leaderboard");
        const data = await res.json();
        setPlayers(data.top_players || []);
      } catch (e) {
        // ignore
      }
    }
    fetchLB();
  }, []);
  return (
    <section className="max-w-3xl mx-auto">
      <h2 className="text-2xl font-extrabold mb-4">Leaderboard</h2>
      <div className="space-y-3">
        {players.length === 0 ? <div className="text-slate-400">No data</div> : players.map((p, i) => (
          <div key={p.username} className="flex justify-between p-3 bg-[#0f0f12] rounded">
            <div>{i+1}. {p.username}</div>
            <div className="text-yellow-300">{p.coins} ✦</div>
          </div>
        ))}
      </div>
    </section>
  );
}
EOF
  echo "✅ src/components/Leaderboard.jsx created"
else
  echo "✅ src/components/Leaderboard.jsx already exists"
fi

# -------------------------
# 10. Fix common duplicate-import issues in any existing files
# -------------------------
echo "🔎 Scanning for duplicate import lines in src files and removing obvious duplicates..."

# Remove exact duplicate import lines within a file (simple heuristic)
find src -type f -name "*.jsx" -o -name "*.js" | while read -r f; do
  # create a temp file with duplicates removed (preserve order)
  awk '!seen[$0]++' "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
done

# -------------------------
# 11. Build / Dev scripts: ensure package.json has dev script
# -------------------------
if ! grep -q "\"dev\":" package.json 2>/dev/null; then
  echo "⚙️ Ensuring package.json has dev script"
  # try to add dev script using jq if available, else warn
  if command -v jq >/dev/null 2>&1; then
    tmp=$(mktemp)
    jq '.scripts.dev = "vite"' package.json > "$tmp" && mv "$tmp" package.json
  else
    echo "⚠️ jq not found; please ensure package.json has a dev script (e.g., \"dev\": \"vite\")"
  fi
fi

# -------------------------
# 12. Start backend and frontend
# -------------------------
cd "$ROOT_DIR"

echo "🚀 Starting backend (uvicorn) in background..."
# Use nohup to keep it running; redirect logs to backend.log
nohup uvicorn backend:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# Wait for backend to be up (simple check)
echo "⏳ Waiting for backend to start (up to 10s)..."
for i in {1..10}; do
  if curl -sS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "✅ Backend is up"
    break
  fi
  sleep 1
done

cd "$FRONTEND_DIR"

echo "🚀 Starting frontend dev server (vite)..."
# Use npm run dev; pass --host to allow network access
# Run in foreground so user sees output; if you prefer background, append & at end
npm run dev -- --host

# End
