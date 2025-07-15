#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
סקריפט הפעלה פשוט ליונתן הצ'אטבוט
מריץ את כל הבדיקות הנדרשות ומפעיל את השרת
"""

import os
import sys
import subprocess
import platform

def print_header():
    """הדפסת כותרת יפה"""
    print("=" * 60)
    print("🤖 יונתן הפסיכו-בוט - הפעלה אוטומטית")
    print("=" * 60)

def check_python_version():
    """בדיקת גרסת פייתון"""
    print("🐍 בדיקת גרסת פייתון...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ נדרשת פייתון 3.8 ומעלה")
        print(f"הגרסה הנוכחית: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ פייתון {version.major}.{version.minor}.{version.micro}")
    return True

def check_env_file():
    """בדיקת קובץ .env"""
    print("\n🔧 בדיקת קובץ .env...")
    if not os.path.exists('.env'):
        print("❌ קובץ .env לא נמצא!")
        print("💡 צור קובץ .env בעזרת התבנית שסופקה")
        return False
    
    # קריאת התוכן ובדיקה בסיסית
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'GOOGLE_API_KEY=' not in content:
                print("❌ GOOGLE_API_KEY חסר בקובץ .env")
                return False
            if 'הכנס_כאן_את_המפתח' in content:
                print("❌ יש להחליף את GOOGLE_API_KEY במפתח אמיתי")
                return False
        print("✅ קובץ .env נמצא ונראה תקין")
        return True
    except Exception as e:
        print(f"❌ שגיאה בקריאת קובץ .env: {e}")
        return False

def install_requirements():
    """התקנת תלותות"""
    print("\n📦 בדיקת תלותות...")
    if not os.path.exists('requirements.txt'):
        print("❌ קובץ requirements.txt לא נמצא")
        return False
    
    try:
        # בדיקה אם החבילות מותקנות
        import flask
        import google.generativeai
        print("✅ החבילות העיקריות מותקנות")
        return True
    except ImportError:
        print("⏳ מתקין תלותות...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ תלותות הותקנו בהצלחה")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ שגיאה בהתקנת תלותות: {e}")
            return False

def create_database():
    """יצירת מסד הנתונים"""
    print("\n🗄️ יצירת מסד הנתונים...")
    try:
        subprocess.check_call([sys.executable, "create_tables.py"])
        print("✅ מסד הנתונים נוצר בהצלחה")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ שגיאה ביצירת מסד הנתונים: {e}")
        return False
    except FileNotFoundError:
        print("❌ קובץ create_tables.py לא נמצא")
        return False

def run_health_check():
    """בדיקת בריאות המערכת"""
    print("\n🏥 בדיקת בריאות המערכת...")
    try:
        result = subprocess.run([sys.executable, "quick_check.py"], 
                              capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            print("✅ בדיקת בריאות עברה בהצלחה")
            return True
        else:
            print("⚠️ בדיקת בריאות מצאה בעיות:")
            print(result.stdout)
            return False
    except FileNotFoundError:
        print("⚠️ קובץ quick_check.py לא נמצא, ממשיך בכל זאת...")
        return True
    except Exception as e:
        print(f"⚠️ שגיאה בבדיקת בריאות: {e}")
        return True

def start_server():
    """הפעלת השרת"""
    print("\n🚀 מפעיל את השרת...")
    print("📍 השרת יעלה על: http://localhost:5000")
    print("⏸️  לעצירה, לחץ Ctrl+C")
    print("=" * 60)
    
    try:
        # הפעלת השרת
        subprocess.call([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\n🛑 השרת נעצר בהצלחה")
    except Exception as e:
        print(f"\n❌ שגיאה בהפעלת השרת: {e}")

def open_browser():
    """פתיחת הדפדפן"""
    try:
        import webbrowser
        import time
        time.sleep(2)  # המתנה שהשרת יעלה
        webbrowser.open("http://localhost:5000")
    except Exception:
        pass

def main():
    """פונקציה ראשית"""
    print_header()
    
    # בדיקות מקדימות
    checks = [
        ("גרסת פייתון", check_python_version),
        ("קובץ .env", check_env_file),
        ("תלותות", install_requirements),
        ("מסד נתונים", create_database),
        ("בריאות המערכת", run_health_check)
    ]
    
    failed_checks = []
    for name, check_func in checks:
        if not check_func():
            failed_checks.append(name)
    
    if failed_checks:
        print("\n🚨 הבדיקות הבאות נכשלו:")
        for check in failed_checks:
            print(f"   - {check}")
        print("\n💡 תקן את הבעיות ונסה שוב")
        input("\nלחץ Enter ליציאה...")
        return
    
    print("\n🎉 כל הבדיקות עברו בהצלחה!")
    
    # שאלה אם לפתוח דפדפן
    try:
        response = input("\n🌐 לפתוח דפדפן אוטומטית? (y/n): ").strip().lower()
        if response in ['y', 'yes', 'כן', '']:
            # פתיחת דפדפן ברקע
            import threading
            threading.Thread(target=open_browser, daemon=True).start()
    except:
        pass
    
    # הפעלת השרת
    start_server()

if __name__ == "__main__":
    main()