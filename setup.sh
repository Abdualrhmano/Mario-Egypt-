#!/bin/bash

# 1. تنظيف العمليات
pkill -f uvicorn
pkill -f vite

# 2. مكتبات الباك إند
pip install fastapi uvicorn sqlalchemy passlib bcrypt python-jose pydantic pydantic-settings websockets python-multipart > /dev/null 2>&1
[ ! -f .env ] && echo 'JWT_SECRET="Khufu_Safe_2026"' > .env

# 3. مكتبات الفرانت إند (الحل هنا: إضافة @tailwindcss/postcss)
cd frontend || exit
npm install axios jwt-decode react-router-dom lucide-react > /dev/null 2>&1
npm install -D tailwindcss @tailwindcss/postcss postcss autoprefixer > /dev/null 2>&1

# 4. تحديث ملف postcss.config.js للنسخة الجديدة
cat << 'EOF' > postcss.config.js
export default {
  plugins: {
    "@tailwindcss/postcss": {},
    autoprefixer: {},
  },
}
EOF

# 5. تحديث tailwind.config.js
cat << 'EOF' > tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
EOF

# 6. كتابة ملف CSS نظيف
cat << 'EOF' > src/index.css
@tailwind base;
@tailwind components;
@tailwind utilities;
body { margin: 0; background-color: #07070a; color: white; }
EOF

# 7. نقل وإصلاح الكود الرئيسي
cd ..
if [ -f "frontend_game.jsx" ]; then
    cp -f frontend_game.jsx frontend/src/main.jsx
    sed -i 's/import jwtDecode from "jwt-decode";/import { jwtDecode } from "jwt-decode";/g' frontend/src/main.jsx
    sed -i 's/withRouter,//g' frontend/src/main.jsx
    sed -i '/<AppRoot \/>);/q' frontend/src/main.jsx
fi

# 8. التشغيل
uvicorn backend:app --reload --port 8000 &
cd frontend || exit
npm run dev -- --host
