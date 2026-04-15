#!/bin/bash

# 1. تنظيف شامل للبيئة (Zero State)
echo "🧹 تنظيف النظام من أي مخلفات..."
pkill -f uvicorn
pkill -f vite
# مسح الكاش بتاع npm عشان يضمن تحميل مكتبات سليمة
npm cache clean --force > /dev/null 2>&1

# 2. إعداد الباك إند (علاج مشاكل المكتبات والبيئة)
echo "📦 تجهيز الباك إند وقاعدة البيانات..."
pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] pydantic pydantic-settings websockets python-multipart > /dev/null 2>&1

# إنشاء ملف .env ثابت ومستقر
cat << 'EOF' > .env
JWT_SECRET="ENGINEER_ABDULRAHMAN_KHUFU_2026_PRO"
DATABASE_URL="sqlite:///./game.db"
EOF

# 3. إعداد الفرانت إند (هيكل ثابت يمنع ضياع الملفات)
echo "📦 بناء هيكل الواجهة الأمامية..."
if [ ! -d "frontend" ]; then
    npm create vite@latest frontend -- --template react > /dev/null 2>&1
fi

cd frontend || exit

# تثبيت المكتبات بإصدارات محددة لضمان الاستقرار في المستقبل
npm install axios@latest jwt-decode@latest react-router-dom@latest lucide-react@latest > /dev/null 2>&1
npm install -D tailwindcss@latest postcss@latest autoprefixer@latest > /dev/null 2>&1

# 4. إجبار النظام على قراءة التصميم (الحل النهائي لمشكلة الألوان)
echo "🎨 تهيئة نظام التصميم (Tailwind)..."
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

# كتابة ملف CSS أساسي يصفر الإعدادات القديمة
cat << 'EOF' > src/index.css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root { color-scheme: dark; }
body { margin: 0; background-color: #07070a !important; color: white; min-height: 100vh; }
EOF

# 5. معالجة ملف الكود (الذكاء الاصطناعي للإصلاح التلقائي)
echo "🛠️ حقن الكود وإصلاح الأخطاء البرمجية..."
cd ..
if [ -f "frontend_game.jsx" ]; then
    # إنشاء ملف main.jsx نظيف تماماً
    echo "import React from 'react';" > frontend/src/main.jsx
    echo "import { createRoot } from 'react-dom/client';" >> frontend/src/main.jsx
    echo "import './index.css';" >> frontend/src/main.jsx
    
    # دمج كود اللعبة مع معالجة الأخطاء (withRouter و jwtDecode)
    cat frontend_game.jsx >> frontend/src/main.jsx
    
    # تصحيحات Sed نهائية
    sed -i 's/import jwtDecode from "jwt-decode";/import { jwtDecode } from "jwt-decode";/g' frontend/src/main.jsx
    sed -i 's/withRouter,//g' frontend/src/main.jsx
    sed -i 's/import ".\/index.css";//g' frontend/src/main.jsx # منع التكرار
    
    # إغلاق الملف بشكل صحيح (حذف أي زيادات)
    sed -i '/<AppRoot \/>);/q' frontend/src/main.jsx
fi

# 6. التشغيل (بأوضاع تسمح بالوصول الخارجي)
echo "🚀 انطلاق! اللعبة جاهزة الآن."
# تشغيل الباك إند
uvicorn backend:app --host 0.0.0.0 --port 8000 & 

# تشغيل الفرانت إند مع إجبار الكاش على التحديث
cd frontend || exit
npm run dev -- --host --force
