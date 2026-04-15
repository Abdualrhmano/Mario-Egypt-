#!/bin/bash

pkill -f uvicorn
pkill -f vite

pip install fastapi uvicorn sqlalchemy passlib bcrypt python-jose pydantic pydantic-settings websockets python-multipart > /dev/null 2>&1

if [ ! -f .env ]; then
    echo 'JWT_SECRET="Khufu_Project_Safe_Secret_2026_Engineers"' > .env
fi

if [ ! -d "frontend" ]; then
    npm create vite@latest frontend -- --template react > /dev/null 2>&1
fi

cd frontend || exit

npm install > /dev/null 2>&1
npm install axios jwt-decode react-router-dom > /dev/null 2>&1
npm install -D tailwindcss postcss autoprefixer > /dev/null 2>&1

npx tailwindcss init -p > /dev/null 2>&1

cat << 'EOF' > tailwind.config.js
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
EOF

cat << 'EOF' > src/index.css
@tailwind base;
@tailwind components;
@tailwind utilities;

body { margin: 0; background-color: #07070a; color: white; }
EOF

cd ..

if [ -f "frontend_game.jsx" ]; then
    cp -f frontend_game.jsx frontend/src/main.jsx
    
    sed -i 's/import jwtDecode from "jwt-decode";/import { jwtDecode } from "jwt-decode";/g' frontend/src/main.jsx
    
    sed -i '/<AppRoot \/>);/q' frontend/src/main.jsx
fi

uvicorn backend:app --reload --port 8000 &
cd frontend || exit
npm run dev -- --host

