# test_key.py
import google.generativeai as genai

# 🔑 הכנס כאן את המפתח שלך במקום הנקודות
API_KEY = "AIzaSyCoWV2qHFjtMMT1l88Nf8Um16iMTvWdaHU"  # המפתח שלך

print("🔍 בודק את מפתח Google API...")
print("-" * 40)

try:
    # הגדרת המפתח
    genai.configure(api_key=API_KEY)
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
        print("\n🎉 אפשר להוסיף את המפתח ל-Render!")
    else:
        print("❌ המפתח לא מחזיר תגובה")
        
except Exception as e:
    print(f"❌ שגיאה: {e}")
    print("\n💡 בדוק שהמפתח נכון או נסה ליצור מפתח חדש")

print("-" * 40)