#!/bin/bash

# 1. تنظيف شامل وجذري للعمليات والكاش
echo "🧹 Cleaning old processes and npm cache..."
pkill -f uvicorn
pkill -f vite
npm cache clean --force > /dev/null 2>&1

# 2. تثبيت مكتبات الباك إند (نسخة مستقرة)
echo "📦 Installing backend dependencies..."
pip install --upgrade fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] pydantic pydantic-settings websockets python-multipart > /dev/null 2>&1

# التأكد من وجود ملف البيئة
if [ ! -f .env ]; then
    echo 'JWT_SECRET="Khufu_Project_Safe_2026_Abdulrahman"' > .env
fi

# 3. إعداد مجلد الفرانت إند (بشكل آلي صامت)
if [ ! -d "frontend" ]; then
    echo "🏗️ Creating frontend folder..."
    npm create vite@latest frontend --yes -- --template react > /dev/null 2>&1
fi

# التأكد من الدخول للمجلد
cd "$(pwd)/frontend" || exit

# 4. تثبيت مكتبات الفرانت إند وتجهيز Tailwind
echo "📦 Installing frontend dependencies (Tailwind, Axios, etc.)..."
npm install --silent axios jwt-decode react-router-dom lucide-react > /dev/null 2>&1
npm install --silent -D tailwindcss postcss autoprefixer @tailwindcss/postcss > /dev/null 2>&1

# إعداد ملفات التكوين لـ Tailwind (Overwrite لضمان الصحة)
cat << 'EOF' > postcss.config.js
export default {
  plugins: {
    "@tailwindcss/postcss": {},
    autoprefixer: {},
  },
}
EOF

cat << 'EOF' > tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
EOF

mkdir -p src
cat << 'EOF' > src/index.css
@tailwind base;
@tailwind components;
@tailwind utilities;
body { margin: 0; background-color: #07070a !important; color: white; min-height: 100vh; }
EOF

# 5. نقل الكود وإصلاح الأخطاء (الجراحة البرمجية)
cd ..
if [ -f "frontend_game.jsx" ]; then
    echo "🛠️ Integrating frontend_game.jsx and fixing duplicate declarations..."
    
    # استخدام awk لحذف أي سطور مكررة تماماً (علاج خطأ React has already been declared)
    awk '!seen[$0]++' frontend_game.jsx > frontend/src/main.jsx
    
    # التأكد من استدعاء الـ CSS في أول سطر (بشرط عدم تكراره)
    sed -i "1i import './index.css';" frontend/src/main.jsx
    
    # الإصلاحات البرمجية الأساسية
    sed -i 's/import jwtDecode from "jwt-decode";/import { jwtDecode } from "jwt-decode";/g' frontend/src/main.jsx
    sed -i 's/withRouter,//g' frontend/src/main.jsx
    
    # ضمان إنهاء الملف عند AppRoot ومنع أي كود زائد في الأسفل
    sed -i '/<AppRoot \/>);/q' frontend/src/main.jsx
else
    echo "⚠️ Warning: frontend_game.jsx not found!"
fi

# 6. التشغيل النهائي
echo "🚀 Starting Backend and Frontend..."
# تشغيل الباك إند في الخلفية
uvicorn backend:app --host 0.0.0.0 --port 8000 & 

# تشغيل الفرانت إند مع إجبار الكاش على التحديث
cd frontend || exit
npm run dev -- --host --force
