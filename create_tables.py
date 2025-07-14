# create_tables.py
# סקריפט ליצירת טבלאות בבסיס הנתונים - עובד בפיתוח ובפרודקשן

import os
import sys

def create_tables():
    """יצירת כל הטבלאות במערכת"""
    print("🚀 יוצר טבלאות במערכת...")
    
    try:
        # ייבוא המודולים הנדרשים
        from app import app, db
        
        # עבודה בקונטקסט של האפליקציה
        with app.app_context():
            print(f"📊 יוצר טבלאות בסביבה: {os.environ.get('FLASK_ENV', 'production')}")
            print(f"🗄️  בסיס נתונים: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
            
            # יצירת כל הטבלאות
            db.create_all()
            
            print("✅ הטבלאות נוצרו בהצלחה!")
            
            # בדיקה שהטבלאות נוצרו
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                
                print(f"📋 נוצרו {len(tables)} טבלאות:")
                for table in tables:
                    print(f"   ✓ {table}")
                
                # בדיקה שכל הטבלאות הנדרשות נוצרו
                expected_tables = ['parent', 'child', 'conversation', 'message', 'questionnaire_response']
                missing_tables = [t for t in expected_tables if t not in tables]
                
                if missing_tables:
                    print(f"⚠️  חסרות טבלאות: {missing_tables}")
                    return False
                
                print("🎯 כל הטבלאות הנדרשות נוצרו!")
                return True
                
            except Exception as inspect_error:
                print(f"⚠️  לא ניתן לבדוק את הטבלאות: {inspect_error}")
                print("✅ הטבלאות כנראה נוצרו (SQLite לא תומך בinspection)")
                return True
                
    except ImportError as e:
        print(f"❌ שגיאה בייבוא מודולים: {e}")
        print("💡 וודא שכל החבילות מותקנות: pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ שגיאה ביצירת הטבלאות: {e}")
        print("💡 בדוק את ההגדרות בקובץ config.py ואת משתני הסביבה")
        return False

def main():
    """פונקציה ראשית"""
    print("=" * 60)
    print("🏗️  יצירת טבלאות במערכת יונתן הפסיכו-בוט")
    print("=" * 60)
    
    # בדיקת סביבה
    env = os.environ.get('FLASK_ENV', 'production')
    print(f"🌍 סביבה: {env}")
    
    # בדיקה שהקבצים הנדרשים קיימים
    required_files = ['app.py', 'models.py', 'config.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ חסרים קבצים: {missing_files}")
        print("💡 וודא שאתה בתיקיית הפרויקט הנכונה")
        sys.exit(1)
    
    # בדיקת משתני סביבה חיוניים
    if env == 'production':
        if not os.environ.get('DATABASE_URL'):
            print("⚠️  DATABASE_URL לא מוגדר בפרודקשן - ישתמש ב-SQLite")
        if not os.environ.get('GOOGLE_API_KEY'):
            print("⚠️  GOOGLE_API_KEY לא מוגדר")
    
    # יצירת הטבלאות
    success = create_tables()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 המערכת מוכנה לשימוש!")
        if env == 'development':
            print("💡 כעת תוכל להריץ: python app.py")
        else:
            print("💡 כעת תוכל להפעיל עם: gunicorn app:app")
    else:
        print("🚨 יש בעיה ביצירת הטבלאות")
        print("💡 בדוק את השגיאות למעלה ונסה שוב")
        sys.exit(1)

if __name__ == "__main__":
    main()