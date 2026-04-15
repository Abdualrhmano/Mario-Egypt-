#!/bin/bash

# 1. تنظيف العمليات القديمة
pkill -f uvicorn
pkill -f vite

# 2. تجهيز الباك إند
pip install fastapi uvicorn sqlalchemy passlib bcrypt python-jose pydantic pydantic-settings websockets python-multipart > /dev/null 2>&1
[ ! -f .env ] && echo 'JWT_SECRET="Khufu_Safe_2026"' > .env

# 3. إنشاء مجلد الفرانت إند لو مش موجود (حل المشكلة اللي في الصورة)
if [ ! -d "frontend" ]; then
    echo "📦 مجلد frontend غير موجود، جاري إنشاؤه..."
    npm create vite@latest frontend -- --template react > /dev/null 2>&1
fi

# 4. دخول المجلد وتثبيت المكتبات
cd frontend || exit
npm install axios jwt-decode react-router-dom lucide-react > /dev/null 2>&1
npm install -D tailwindcss @tailwindcss/postcss postcss autoprefixer > /dev/null 2>&1

# 5. تحديث ملفات الإعدادات
cat << 'EOF' > postcss.config.js
export default {
  plugins: {
    "@tailwindcss/postcss": {},
    autoprefixer: {},
  },
}
EOF

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

# 6. نقل ملف اللعبة وإصلاح الأخطاء
cd ..
if [ -f "frontend_game.jsx" ]; then
    cp -f frontend_game.jsx frontend/src/main.jsx
    sed -i 's/import jwtDecode from "jwt-decode";/import { jwtDecode } from "jwt-decode";/g' frontend/src/main.jsx
    sed -i 's/withRouter,//g' frontend/src/main.jsx
    sed -i '/<AppRoot \/>);/q' frontend/src/main.jsx
fi

# 7. التشغيل النهائي
uvicorn backend:app --reload --port 8000 &
cd frontend || exit
npm run dev -- --host
