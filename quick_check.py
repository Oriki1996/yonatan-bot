#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
סקריפט בדיקה מהירה לצ'אטבוט יונתן
"""

import os
import sys
from dotenv import load_dotenv

def check_env_variables():
    """בדיקת משתני סביבה"""
    print("🔍 בדיקת משתני סביבה...")
    
    load_dotenv()
    
    required_vars = ['GOOGLE_API_KEY', 'SECRET_KEY']
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: מוגדר")
        else:
            print(f"❌ {var}: חסר!")
    
    flask_env = os.environ.get('FLASK_ENV', 'development')
    print(f"🏗️  FLASK_ENV: {flask_env}")

def check_database():
    """בדיקת בסיס הנתונים"""
    print("\n🗄️  בדיקת בסיס הנתונים...")
    
    try:
        from app import app, db
        with app.app_context():
            # בדיקה שהטבלאות קיימות
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = ['parent', 'child', 'conversation', 'message', 'questionnaire_response']
            
            if not tables:
                print("❌ לא נמצאו טבלאות! הרץ: python create_tables.py")
                return False
            
            print(f"✅ נמצאו {len(tables)} טבלאות:")
            for table in tables:
                print(f"   - {table}")
            
            # בדיקה שכל הטבלאות הנדרשות קיימות
            missing_tables = [t for t in expected_tables if t not in tables]
            if missing_tables:
                print(f"❌ חסרות טבלאות: {missing_tables}")
                return False
            
            return True
    except Exception as e:
        print(f"❌ שגיאה בבדיקת בסיס הנתונים: {e}")
        return False

def check_ai_model():
    """בדיקת מודל AI"""
    print("\n🤖 בדיקת מודל AI...")
    
    try:
        from app import model
        if not model:
            print("❌ מודל AI לא מוגדר")
            return False
        
        # בדיקת תגובה
        response = model.generate_content("בדיקה")
        if response and response.text:
            print("✅ מודל AI עובד")
            print(f"   תגובה: {response.text[:50]}...")
            return True
        else:
            print("❌ מודל AI לא מחזיר תגובה")
            return False
    except Exception as e:
        print(f"❌ שגיאה במודל AI: {e}")
        return False

def check_static_files():
    """בדיקת קבצים סטטיים"""
    print("\n📁 בדיקת קבצים סטטיים...")
    
    static_files = [
        'static/widget.js',
        'static/articles.json',
        'templates/index.html'
    ]
    
    all_exist = True
    for file_path in static_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - חסר!")
            all_exist = False
    
    return all_exist

def check_server_health():
    """בדיקת בריאות השרת"""
    print("\n🏥 בדיקת בריאות השרת...")
    
    try:
        import requests
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ שרת פועל")
            print(f"   בסיס נתונים: {'✅' if health_data.get('database_connected') else '❌'}")
            print(f"   מודל AI: {'✅' if health_data.get('ai_model_working') else '❌'}")
            return True
        else:
            print(f"❌ שרת מחזיר סטטוס {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ שרת לא פועל או לא נגיש")
        return False
    except Exception as e:
        print(f"❌ שגיאה בבדיקת השרת: {e}")
        return False

def create_tables_if_needed():
    """יצירת טבלאות אם לא קיימות"""
    print("\n🔧 יצירת טבלאות...")
    
    try:
        from app import app, db
        with app.app_context():
            db.create_all()
            print("✅ טבלאות נוצרו/עודכנו בהצלחה")
            return True
    except Exception as e:
        print(f"❌ שגיאה ביצירת טבלאות: {e}")
        return False

def main():
    """פונקציה ראשית"""
    print("=" * 50)
    print("🚀 בדיקה מהירה של יונתן הצ'אטבוט")
    print("=" * 50)
    
    # בדיקות
    checks = [
        ("משתני סביבה", check_env_variables),
        ("יצירת טבלאות", create_tables_if_needed),
        ("בסיס נתונים", check_database),
        ("מודל AI", check_ai_model),
        ("קבצים סטטיים", check_static_files),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ שגיאה בבדיקת {name}: {e}")
            results.append((name, False))
    
    # בדיקת שרת (אם פועל)
    print("\n" + "=" * 50)
    print("🔄 בדיקת שרת (אם פועל)...")
    server_result = check_server_health()
    results.append(("שרת", server_result))
    
    # סיכום
    print("\n" + "=" * 50)
    print("📊 סיכום:")
    print("=" * 50)
    
    for name, result in results:
        status = "✅ עובר" if result else "❌ כשל"
        print(f"{name}: {status}")
    
    successful = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n📈 ציון כללי: {successful}/{total}")
    
    if successful == total:
        print("🎉 הכל עובד מצוין!")
    elif successful >= total * 0.8:
        print("⚠️  רוב הדברים עובדים, יש כמה בעיות קטנות")
    else:
        print("🚨 יש בעיות שצריך לפתור")
    
    # הצעות לפתרון
    print("\n" + "=" * 50)
    print("💡 הצעות לשלבים הבאים:")
    print("=" * 50)
    
    if not results[0][1]:  # משתני סביבה
        print("1. צור קובץ .env עם המפתחות הנדרשים")
    
    if not results[1][1] or not results[2][1]:  # בסיס נתונים
        print("2. הרץ: python create_tables.py")
    
    if not results[3][1]:  # מודל AI
        print("3. בדוק את מפתח Google API")
    
    if not results[4][1]:  # קבצים סטטיים
        print("4. וודא שכל הקבצים הסטטיים במקום")
    
    if not results[5][1]:  # שרת
        print("5. הפעל את השרת עם: python app.py")
    
    print("\n6. אחרי תיקון הבעיות, נסה לגשת ל: http://localhost:5000")

if __name__ == "__main__":
    main()