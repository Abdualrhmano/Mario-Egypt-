#!/bin/bash

# 1. تنظيف العمليات القديمة تماماً
pkill -f uvicorn
pkill -f vite

# 2. تثبيت مكتبات الباك إند المطلوبة للنظام
pip install fastapi uvicorn sqlalchemy passlib bcrypt python-jose pydantic pydantic-settings websockets python-multipart > /dev/null 2>&1

# إنشاء ملف البيئة لمنع خطأ jwt_secret
if [ ! -f .env ]; then
    echo 'JWT_SECRET="Khufu_Project_Safe_Secret_2026_Engineers"' > .env
fi

# 3. تجهيز مجلد الفرانت إند وتثبيت المكتبات البرمجية
if [ ! -d "frontend" ]; then
    npm create vite@latest frontend -- --template react > /dev/null 2>&1
fi

cd frontend || exit
# تثبيت المكتبات الأساسية والأيقونات (lucide-react) لحل أخطاء الواجهة
npm install axios jwt-decode react-router-dom lucide-react > /dev/null 2>&1
npm install -D tailwindcss postcss autoprefixer > /dev/null 2>&1

# 4. مسح وإعادة كتابة ملفات الإعدادات (التصميم)
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
body { margin: 0; background-color: #07070a; color: white; font-family: sans-serif; }
EOF

# 5. نقل ملف اللعبة ومعالجة الأخطاء (علاج الشاشة البيضاء)
cd ..
if [ -f "frontend_game.jsx" ]; then
    # مسح main.jsx القديم ونقل الكود الجديد
    cp -f frontend_game.jsx frontend/src/main.jsx
    
    # إصلاح استدعاء jwt-decode للإصدار الحديث
    sed -i 's/import jwtDecode from "jwt-decode";/import { jwtDecode } from "jwt-decode";/g' frontend/src/main.jsx
    
    # حذف withRouter (لأنه غير مدعوم في الإصدارات الجديدة ويسبب شاشة بيضاء)
    sed -i 's/withRouter,//g' frontend/src/main.jsx
    
    # قص أي نصوص زائدة في نهاية الملف
    sed -i '/<AppRoot \/>);/q' frontend/src/main.jsx
fi

# 6. التشغيل النهائي للسيرفرين
uvicorn backend:app --reload --port 8000 &
cd frontend || exit
npm run dev -- --host
