# test_key.py - גרסה בטוחה
import google.generativeai as genai
import os
from dotenv import load_dotenv

def test_api_key():
    """בדיקה שמפתח Google API עובד (ללא חשיפת המפתח בקוד)"""
    
    # טעינת המפתח מקובץ .env או משתני סביבה
    load_dotenv()
    api_key = os.environ.get('GOOGLE_API_KEY')
    
    if not api_key:
        print("❌ לא נמצא מפתח GOOGLE_API_KEY")
        print("💡 צור קובץ .env עם השורה: GOOGLE_API_KEY=your_key_here")
        print("💡 או הגדר משתנה סביבה")
        return False
    
    print("🔍 בודק מפתח Google API...")
    print("-" * 40)

    try:
        # הגדרת המפתח
        genai.configure(api_key=api_key)
        print("✅ מפתח הוגדר")
        
        # יצירת מודל
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ מודל נוצר")
        
        # בדיקה פשוטה
        print("🤖 שולח הודעת בדיקה...")
        response = model.generate_content("אמור שלום בעברית")
        
        if response and response.text:
            print("✅ המפתח עובד מצוין!")
            print(f"📝 תגובת הבוט: {response.text}")
            return True
        else:
            print("❌ המפתח לא מחזיר תגובה")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False

if __name__ == "__main__":
    print("🔍 בדיקת מפתח Google API (בטוחה)")
    print("=" * 50)
    
    success = test_api_key()
    
    if success:
        print("\n🎉 המפתח עובד! אפשר להוסיף אותו ל-Render")
    else:
        print("\n🚨 יש בעיה במפתח או בהגדרות")
        
    print("=" * 50)