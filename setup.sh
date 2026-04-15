#!/bin/bash

# 1. تنظيف السيرفرات
pkill -f uvicorn
pkill -f vite

# 2. تثبيت المكتبات
pip install fastapi uvicorn sqlalchemy passlib bcrypt python-jose pydantic pydantic-settings websockets python-multipart > /dev/null 2>&1
[ ! -f .env ] && echo 'JWT_SECRET="Khufu_Safe_2026"' > .env

# 3. تجهيز المجلدات
if [ ! -d "frontend" ]; then
    npm create vite@latest frontend -- --template react > /dev/null 2>&1
fi

cd frontend || exit
npm install axios jwt-decode react-router-dom lucide-react > /dev/null 2>&1
npm install -D tailwindcss postcss autoprefixer > /dev/null 2>&1

# 4. إجبار Tailwind على العمل (هنا الحل)
cat << 'EOF' > tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

cat << 'EOF' > postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF

cat << 'EOF' > src/index.css
@tailwind base;
@tailwind components;
@tailwind utilities;

body { 
  margin: 0; 
  background-color: #07070a; 
  color: white; 
  font-family: sans-serif; 
}
EOF

# 5. نقل الكود وإصلاح الأخطاء
cd ..
if [ -f "frontend_game.jsx" ]; then
    cp -f frontend_game.jsx frontend/src/main.jsx
    sed -i 's/import jwtDecode from "jwt-decode";/import { jwtDecode } from "jwt-decode";/g' frontend/src/main.jsx
    sed -i 's/withRouter,//g' frontend/src/main.jsx
    sed -i '/<AppRoot \/>);/q' frontend/src/main.jsx
fi

# 6. التشغيل النهائي
uvicorn backend:app --reload --port 8000 &
cd frontend || exit
npm run dev -- --host
