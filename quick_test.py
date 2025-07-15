#!/usr/bin/env python3
# quick_test.py - בדיקה מהירה שהכל עובד

import requests

def test_bot():
    base_url = "https://yonatan-bot.onrender.com"
    
    print("🤖 בודק את יונתן...")
    
    try:
        # בדיקת בריאות
        health = requests.get(f"{base_url}/api/health", timeout=10)
        if health.status_code == 200:
            data = health.json()
            print(f"✅ השרת עובד - סטטוס: {data.get('status', 'לא ידוע')}")
            print(f"🤖 AI: {'✅' if data.get('ai_model_working') else '❌'}")
            print(f"🔄 Fallback: {'✅' if data.get('fallback_system_available') else '❌'}")
            
            if data.get('ai_model_working') or data.get('fallback_system_available'):
                print("🎉 הבוט מוכן לשימוש!")
            else:
                print("⚠️  הבוט חי אבל יש בעיות")
        else:
            print(f"❌ בעיה בשרת: {health.status_code}")
            
    except Exception as e:
        print(f"❌ לא ניתן להתחבר: {e}")

if __name__ == "__main__":
    test_bot()