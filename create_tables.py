# create_tables.py
# סקריפט ליצירת טבלאות בבסיס הנתונים - עובד בפיתוח ובפרודקשן

import os
import sys
from sqlalchemy.exc import OperationalError, ProgrammingError

def create_tables():
    """יצירת כל הטבלאות במערכת"""
    print("🚀 יוצר טבלאות במערכת...")
    
    try:
        # ייבוא המודולים הנדרשים
        # הייבוא מתבצע כאן כדי לוודא שהאפליקציה וה-db מאותחלים
        from app import app, db
        
        # עבודה בקונטקסט של האפליקציה
        with app.app_context():
            print(f"📊 יוצר טבלאות בסביבה: {os.environ.get('FLASK_ENV', 'production')}")
            print(f"🗄️  בסיס נתונים: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
            
            # בדיקת חיבור לבסיס הנתונים לפני יצירת טבלאות
            try:
                # ניסיון ליצור חיבור למסד הנתונים
                with db.engine.connect() as connection:
                    connection.execute(db.text("SELECT 1"))
                print("✅ חיבור לבסיס הנתונים תקין.")
            except (OperationalError, ProgrammingError) as conn_err:
                print(f"❌ שגיאת חיבור לבסיס הנתונים: {conn_err}")
                print("💡 וודא ש-DATABASE_URL מוגדר נכון ושהמסד נתונים נגיש.")
                return False
            except Exception as conn_err:
                print(f"❌ שגיאה בלתי צפויה בחיבור לבסיס הנתונים: {conn_err}")
                return False

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
                print("✅ הטבלאות כנראה נוצרו (ייתכן שזו סביבת SQLite ללא תמיכה מלאה ב-inspection).")
                return True
                
    except ImportError as e:
        # לכידת שגיאת ייבוא ספציפית כמו 'psycopg2'
        print(f"❌ שגיאה בייבוא מודולים: {e}")
        print("💡 וודא שכל החבילות מותקנות, במיוחד psycopg2-binary אם אתה משתמש ב-PostgreSQL.")
        return False
        
    except Exception as e:
        print(f"❌ שגיאה כללית ביצירת הטבלאות: {e}")
        print("💡 בדוק את ההגדרות בקובץ config.py ואת משתני הסביבה (DATABASE_URL, FLASK_ENV).")
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
