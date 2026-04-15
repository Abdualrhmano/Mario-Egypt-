#!/bin/bash

# 1. تنظيف شامل وجذري
echo "🧹 تنظيف العمليات القديمة والكاش..."
pkill -f uvicorn
pkill -f vite
npm cache clean --force > /dev/null 2>&1

# 2. تجهيز الباك إند وملف البيئة
echo "📦 تثبيت مكتبات الباك إند..."
pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] pydantic pydantic-settings websockets python-multipart > /dev/null 2>&1

if [ ! -f .env ]; then
    echo 'JWT_SECRET="ENGINEER_ABDULRAHMAN_KHUFU_PRO_2026"' > .env
fi

# 3. إنشاء وإعداد مجلد الفرانت إند (بشكل آلي صامت بالكامل)
if [ ! -d "frontend" ]; then
    echo "🏗️ جاري إنشاء مجلد frontend من الصفر..."
    # استخدمنا --yes لضمان عدم توقف السكريبت للسؤال عن اسم المشروع واختيار React تلقائياً
    npm create vite@latest frontend --yes -- --template react > /dev/null 2>&1
fi

# التأكد التام من الدخول للمجلد الصحيح
cd "$(pwd)/frontend" || exit

# 4. تثبيت المكاتب وإصلاح التصميم
echo "📦 تثبيت مكتبات الواجهة (برجاء الانتظار قليلاً)..."
npm install --silent axios jwt-decode react-router-dom lucide-react > /dev/null 2>&1
npm install --silent -D tailwindcss postcss autoprefixer > /dev/null 2>&1

echo "🎨 ضبط Tailwind و CSS..."
# إنشاء ملفات الإعدادات بالقوة (Overwrite)
cat << 'EOF' > postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
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
body { margin: 0; background-color: #07070a !important; color: white; min-height: 100vh; overflow-x: hidden; }
EOF

# 5. نقل الكود وإصلاح الأخطاء (الجراحة البرمجية الآلية)
echo "🛠️ نقل ملف اللعبة وإصلاح الأكواد..."
cd ..
if [ -f "frontend_game.jsx" ]; then
    # بناء main.jsx من الصفر لضمان الربط الصحيح
    echo "import React from 'react';" > frontend/src/main.jsx
    echo "import { createRoot } from 'react-dom/client';" >> frontend/src/main.jsx
    echo "import './index.css';" >> frontend/src/main.jsx
    cat frontend_game.jsx >> frontend/src/main.jsx
    
    # إصلاح الأخطاء الشهيرة تلقائياً
    sed -i 's/import jwtDecode from "jwt-decode";/import { jwtDecode } from "jwt-decode";/g' frontend/src/main.jsx
    sed -i 's/withRouter,//g' frontend/src/main.jsx
    # منع تكرار استدعاء index.css لو كان موجود أصلاً
    sed -i '2,10s/import ".\/index.css";//' frontend/src/main.jsx 
    
    # ضمان قفلة الملف الصحيحة (قطع أي زيادات بعد كود التشغيل)
    sed -i '/<AppRoot \/>);/q' frontend/src/main.jsx
else
    echo "⚠️ تحذير: ملف frontend_game.jsx غير موجود في المسار الرئيسي!"
fi

# 6. الانطلاق النهائي
echo "🚀 تشغيل النظام بالكامل..."
# تشغيل الباك إند في الخلفية
uvicorn backend:app --host 0.0.0.0 --port 8000 & 

# الانتظار لثانية للتأكد من استقرار الباك إند
sleep 2

# تشغيل الفرانت إند مع إجبار التحديث
cd frontend || exit
npm run dev -- --host --force
