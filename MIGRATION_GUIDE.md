# 🔄 دليل الانتقال من SQLite إلى PostgreSQL

إذا كنت تستخدم النسخة السابقة من البوت مع SQLite وتريد الانتقال إلى PostgreSQL، اتبع هذا الدليل.

## 📋 الخطوات المطلوبة

### 1. نسخ احتياطي من البيانات الحالية
```bash
# إنشاء نسخة احتياطية من قاعدة بيانات SQLite
cp bot_database.db bot_database_backup.db
```

### 2. تثبيت PostgreSQL
اتبع تعليمات التثبيت في README.md حسب نظام التشغيل الخاص بك.

### 3. تحديث متطلبات Python
```bash
pip install -r requirements.txt
```

### 4. إعداد قاعدة بيانات PostgreSQL
```bash
python setup_postgres.py
```

### 5. تحديث ملف .env
قم بتحديث `DATABASE_URL` في ملف `.env`:
```env
# القديم (SQLite)
DATABASE_URL=sqlite:///bot_database.db

# الجديد (PostgreSQL)
DATABASE_URL=postgresql://bot_user:secure_bot_password_123@localhost:5432/telegram_bot_db
```

### 6. ترحيل البيانات (اختياري)

إذا كان لديك بيانات مهمة في SQLite تريد نقلها إلى PostgreSQL:

#### الطريقة اليدوية:
1. صدّر البيانات من SQLite:
```bash
sqlite3 bot_database.db .dump > sqlite_backup.sql
```

2. قم بتعديل ملف SQL ليتوافق مع PostgreSQL
3. استورد البيانات إلى PostgreSQL:
```bash
psql -U bot_user -d telegram_bot_db -f converted_data.sql
```

#### سكريبت الترحيل التلقائي:
```python
# migrate_data.py
import sqlite3
import os
from dotenv import load_dotenv
from database import SessionLocal, Channel, ScheduledPost
from sqlalchemy import create_engine

load_dotenv()

def migrate_data():
    # الاتصال بـ SQLite
    sqlite_conn = sqlite3.connect('bot_database.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # الاتصال بـ PostgreSQL
    pg_session = SessionLocal()
    
    try:
        # ترحيل القنوات
        sqlite_cursor.execute("SELECT * FROM channels")
        channels = sqlite_cursor.fetchall()
        
        for channel_data in channels:
            channel = Channel(
                channel_id=channel_data[1],
                channel_name=channel_data[2],
                added_by=channel_data[3],
                added_at=channel_data[4],
                header_enabled=bool(channel_data[5]),
                header_text=channel_data[6] or "",
                footer_enabled=bool(channel_data[7]),
                footer_text=channel_data[8] or ""
            )
            pg_session.add(channel)
        
        # ترحيل المنشورات المجدولة
        sqlite_cursor.execute("SELECT * FROM scheduled_posts")
        posts = sqlite_cursor.fetchall()
        
        for post_data in posts:
            post = ScheduledPost(
                channel_id=post_data[1],
                content=post_data[2],
                buttons=post_data[3] or "",
                scheduled_time=post_data[4],
                auto_delete_time=post_data[5],
                silent=bool(post_data[6]),
                pin_message=bool(post_data[7]),
                created_at=post_data[8],
                sent=bool(post_data[9]),
                message_id=post_data[10]
            )
            pg_session.add(post)
        
        pg_session.commit()
        print("✅ تم ترحيل البيانات بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ في ترحيل البيانات: {e}")
        pg_session.rollback()
    finally:
        sqlite_conn.close()
        pg_session.close()

if __name__ == "__main__":
    migrate_data()
```

### 7. اختبار الإعداد الجديد
```bash
python test_setup.py
```

### 8. تشغيل البوت
```bash
python start.py
```

## ✅ التحقق من نجاح الانتقال

1. **اختبار الاتصال**: تأكد من أن البوت يتصل بقاعدة البيانات بنجاح
2. **اختبار القنوات**: تحقق من ظهور القنوات المضافة سابقاً
3. **اختبار النشر**: جرب إنشاء منشور جديد
4. **اختبار الجدولة**: تأكد من عمل جدولة المنشورات

## 🗑️ تنظيف الملفات القديمة

بعد التأكد من نجاح الانتقال، يمكنك حذف ملفات SQLite:
```bash
# احتفظ بنسخة احتياطية أولاً
mv bot_database.db old_sqlite_backup.db

# أو احذف نهائياً (بحذر!)
# rm bot_database.db
```

## 🎯 مزايا PostgreSQL

- **أداء أفضل** للاستعلامات المعقدة
- **استقرار أكبر** تحت الأحمال العالية
- **ميزات متقدمة** مثل الفهرسة والتحليل
- **دعم أفضل للتطبيقات متعددة المستخدمين**
- **نسخ احتياطي متقدم** وإمكانيات الاستعادة

## ⚠️ ملاحظات مهمة

- تأكد من إنشاء نسخة احتياطية قبل البدء
- اختبر الإعداد الجديد بعناية قبل الاستخدام الفعلي
- احتفظ بملف SQLite القديم كنسخة احتياطية لفترة
- تأكد من تشغيل PostgreSQL قبل تشغيل البوت

## 🆘 في حالة المشاكل

إذا واجهت مشاكل أثناء الانتقال:

1. **العودة للنسخة القديمة**:
   ```bash
   # في ملف .env
   DATABASE_URL=sqlite:///bot_database.db
   ```

2. **التحقق من سجلات الأخطاء**
3. **التأكد من إعدادات PostgreSQL**
4. **مراجعة دليل استكشاف الأخطاء في README.md**