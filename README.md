# יונתן הפסיכו-בוט 🤖

בוט חינוכי מתקדם המבוסס על עקרונות טיפול קוגניטיבי-התנהגותי (CBT) לעזרה והכוונה להורים של מתבגרים.

## 🚀 תכונות עיקריות

- **AI מתקדם**: מבוסס על Google Gemini עם מערכת fallback חכמה
- **CBT מותאם**: עקרונות טיפול קוגניטיבי-התנהגותי מותאמים לבעיות הורות
- **אבטחה מתקדמת**: Rate limiting, input validation, CSRF protection
- **ממשק מודרני**: עיצוב responsive עם אנימציות וUX מתקדם
- **רב-לשוני**: תמיכה מלאה בעברית עם RTL support
- **מערכת fallback**: פעולה רציפה גם כשה-AI לא זמין

## 📋 דרישות מערכת

- **Python**: 3.8 ומעלה
- **מסד נתונים**: PostgreSQL (או SQLite לפיתוח)
- **API Key**: Google Gemini API
- **אופציונלי**: Redis (לcaching וrate limiting)

## 🛠️ התקנה מהירה

### 1. הורדת הפרויקט
```bash
git clone <repository-url>
cd yonatan-bot
```

### 2. התקנת תלותות
```bash
pip install -r requirements.txt
```

### 3. הגדרת משתני סביבה
```bash
# העתק את קובץ הדוגמה
cp .env.example .env

# ערוך את הקובץ והכנס את הערכים האמיתיים
nano .env
```

### 4. יצירת מסד הנתונים
```bash
python create_tables.py
```

### 5. הפעלת השרת
```bash
# לפיתוח
python run.py

# או
python app.py

# לפרודקשן
gunicorn app:app
```

## 🔧 הגדרות .env

צור קובץ `.env` בתיקיית הפרויקט:

```env
# הגדרות Flask
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-here
DEBUG=True

# Google API
GOOGLE_API_KEY=your-google-gemini-api-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost/yonatan_db
# או לפיתוח:
# DATABASE_URL=sqlite:///yonatan.db

# Redis (אופציונלי)
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATELIMIT_STORAGE_URL=memory://

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/yonatan.log

# Session
SESSION_TIMEOUT=1800

# הגדרות צ'אט
MAX_MESSAGE_LENGTH=5000
MAX_SESSIONS_PER_IP=10
CHAT_RATE_LIMIT=30

# הגדרות מערכת fallback
FALLBACK_ENABLED=True
FALLBACK_TIMEOUT=10

# אבטחה
ENABLE_CSRF=True
SECURE_COOKIES=False
```

## 📁 מבנה הפרויקט

```
yonatan-bot/
├── app.py                      # אפליקציית Flask הראשית
├── config.py                   # הגדרות המערכת
├── models.py                   # מודלים של מסד הנתונים
├── errors.py                   # מערכת שגיאות מותאמת
├── utils.py                    # פונקציות עזר
├── advanced_fallback_system.py # מערכת fallback מתקדמת
├── requirements.txt            # תלותות Python
├── runtime.txt                 # גרסת Python
├── create_tables.py           # יצירת מסד נתונים
├── quick_check.py             # בדיקת מערכת
├── quick_test.py              # בדיקה מהירה
├── run.py                     # סקריפט הפעלה
├── test_key.py                # בדיקת API key
├── .env.example               # דוגמה למשתני סביבה
├── .gitignore                 # קבצים להתעלמות
├── README.md                  # התיעוד הזה
├── templates/
│   └── index.html            # דף הבית
├── static/
│   ├── css/
│   │   └── main.css          # עיצוב ראשי
│   └── js/
│       └── main.js           # JavaScript ראשי
└── logs/                     # קבצי לוגים (נוצר אוטומטית)
```

## 🌐 API Endpoints

### בריאות המערכת
- `GET /api/health` - בדיקת תקינות המערכת
- `GET /api/info` - מידע על המערכת

### ניהול סשן
- `POST /api/init` - אתחול סשן חדש
- `POST /api/reset_session` - איפוס סשן

### שאלון ראשוני
- `POST /api/questionnaire` - שמירת נתוני השאלון

### צ'אט
- `POST /api/chat` - שליחת הודעה (streaming response)

### אנליטיקה
- `GET /api/session_analysis/<session_id>` - ניתוח דפוסי שיחה
- `GET /api/session_summary/<session_id>` - סיכום השיחה

## 🔒 אבטחה

המערכת כוללת מספר שכבות אבטחה:

### Input Validation
```python
# דוגמה לvalidation
from marshmallow import Schema, fields

class ChatMessageSchema(Schema):
    session_id = fields.Str(required=True, validate=validate_session_id)
    message = fields.Str(required=True, validate=lambda x: 0 < len(x) <= 5000)
```

### Rate Limiting
```python
# הגבלת קצב בקשות
@limiter.limit("30 per minute")
def chat():
    pass
```

### CSRF Protection
```python
# הגנה מפני CSRF
csrf = CSRFProtect(app)
```

### Security Headers
```python
# כותרות אבטחה
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block'
}
```

## 🧠 מערכת CBT

הבוט מיישם טכניקות CBT מתקדמות:

### טכניקות זמינות
- **Cognitive Restructuring** - שיחזור קוגניטיבי
- **Thought Challenging** - אתגור מחשבות
- **Behavioral Activation** - הפעלה התנהגותית
- **Communication Skills** - כישורי תקשורת
- **Problem Solving** - פתרון בעיות
- **Emotion Regulation** - ויסות רגשי

### קטגוריות אתגרים
- תקשורת וריבים
- קשיים בלימודים
- ויסות רגשי והתפרצויות
- זמן מסך והתמכרויות
- קשיים חברתיים
- התנהגות מרדנית
- חרדה ולחץ
- בעיות שינה

## 🚀 מערכת Fallback מתקדמת

כאשר מודל ה-AI לא זמין, המערכת עוברת אוטומטית למצב fallback:

```python
# דוגמה לשימוש
fallback_response = advanced_fallback_system.get_fallback_response(
    user_message, 
    session_id, 
    questionnaire_data
)
```

### תכונות הfallback:
- **תגובות מותאמות אישית** לפי גיל הילד
- **CBT מובנה** עם כלים מעשיים
- **מעקב אחר דפוסי שיחה**
- **המלצות דינמיות**

## 📊 מודלים ומסד הנתונים

### מודלים עיקריים:
- **Parent** - נתוני הורה
- **Child** - נתוני ילד
- **Conversation** - שיחות
- **Message** - הודעות
- **QuestionnaireResponse** - תשובות שאלון

### דוגמה ליצירת Parent:
```python
parent = Parent(
    id=session_id,
    name="שם ההורה",
    gender="אמא",
    email="parent@example.com"
)
```

## 🔧 פיתוח וגדלוי

### הרצת בדיקות
```bash
# בדיקה כוללת
python quick_check.py

# בדיקת API key
python test_key.py

# בדיקת שרת
python quick_test.py
```

### לוגים
```bash
# צפייה בלוגים
tail -f logs/yonatan.log

# לוגים מפורטים
export LOG_LEVEL=DEBUG
python app.py
```

### מצבי הפעלה
```bash
# פיתוח
export FLASK_ENV=development
python app.py

# פרודקשן
export FLASK_ENV=production
gunicorn app:app --workers 4
```

## 🎨 עיצוב וUI

### CSS מתקדם
- **Responsive Design** - מותאם לכל הגודלים
- **Dark Mode Support** - תמיכה במצב כהה
- **RTL Support** - תמיכה מלאה בעברית
- **Animations** - אנימציות חלקות
- **Accessibility** - נגישות מתקדמת

### JavaScript מתקדם
- **Streaming Response** - הצגת תגובות בזמן אמת
- **Error Handling** - טיפול בשגיאות
- **Session Management** - ניהול סשן
- **Auto-resize** - התאמה אוטומטית של textarea

## 🚀 פרודקשן

### Render.com
```bash
# הגדרת משתני סביבה ב-Render
DATABASE_URL=postgresql://...
GOOGLE_API_KEY=...
SECRET_KEY=...
FLASK_ENV=production
```

### Heroku
```bash
# הוספת add-ons
heroku addons:create heroku-postgresql:hobby-dev
heroku addons:create heroku-redis:hobby-dev

# הגדרת משתנים
heroku config:set GOOGLE_API_KEY=...
heroku config:set SECRET_KEY=...
```

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "app:app"]
```

## 🔍 ניטור ובדיקות

### Health Check
```bash
curl http://localhost:5000/api/health
```

### מדדי ביצועים
```python
# צפייה בסטטיסטיקות
GET /api/info
```

### אנליטיקה
```python
# ניתוח דפוסי שיחה
GET /api/session_analysis/SESSION_ID
```

## 🛡️ אבטחה מתקדמת

### הגנות מובנות:
- **SQL Injection Protection** - הגנה מפני SQL injection
- **XSS Protection** - הגנה מפני XSS
- **CSRF Protection** - הגנה מפני CSRF
- **Rate Limiting** - הגבלת קצב בקשות
- **Input Sanitization** - ניקוי קלט
- **Session Security** - אבטחת סשן

### בדיקות אבטחה:
```bash
# בדיקת חוזק סיסמאות
python -c "from utils import generate_secure_session_id; print(generate_secure_session_id())"

# בדיקת rate limiting
for i in {1..50}; do curl -X POST http://localhost:5000/api/chat; done
```

## 📈 אופטימיזציה

### ביצועים:
- **Database Pooling** - מאגר חיבורים
- **Redis Caching** - מטמון מהיר
- **Streaming Response** - תגובות בזמן אמת
- **Async Processing** - עיבוד אסינכרוני

### זיכרון:
```python
# ניקוי סשנים פגי תוקף
cleanup_expired_sessions()
```

## 🆘 פתרון בעיות

### בעיות נפוצות:

#### 1. שגיאת Database
```bash
# בדיקת חיבור למסד הנתונים
python -c "from app import ensure_db_connection; print(ensure_db_connection())"

# יצירת טבלאות מחדש
python create_tables.py
```

#### 2. בעיות API Key
```bash
# בדיקת מפתח Google
python test_key.py
```

#### 3. בעיות Port
```bash
# בדיקת יציאה תפוסה
lsof -i :5000

# הרצה על יציאה אחרת
export PORT=8000
python app.py
```

#### 4. בעיות Memory
```bash
# בדיקת זיכרון
python -c "from utils import get_memory_usage; print(get_memory_usage())"
```

## 📞 תמיכה

### לתמיכה טכנית:
- בדוק את הלוגים: `logs/yonatan.log`
- הרץ בדיקת מערכת: `python quick_check.py`
- בדוק API health: `curl /api/health`

### שאלות נפוצות:
**ש: הבוט לא מגיב**
ת: בדוק את ה-API key ואת חיבור האינטרנט

**ש: שגיאות rate limiting**
ת: המתן דקה והנמך את קצב הבקשות

**ש: הדף לא נטען**
ת: בדוק שהשרת פועל על http://localhost:5000

## 🤝 תרומה לפרויקט

### הגדרת סביבת פיתוח:
```bash
# התקנת כלי פיתוח
pip install black flake8 pytest

# הרצת בדיקות
pytest tests/

# עיצוב קוד
black .
```

### הנחיות קוד:
- השתמש ב-type hints
- כתוב docstrings
- הוסף בדיקות
- עקוב אחר PEP 8

## 📝 רישיון

המערכת מפותחת לצרכים אקדמיים וחינוכיים. כל הזכויות שמורות.

---

## 🎯 מה הלאה?

עכשיו שהמערכת מוכנה, תוכל:

1. **להריץ את המערכת** עם `python run.py`
2. **לגשת לאתר** בכתובת http://localhost:5000
3. **לבדוק שהכל עובד** עם `python quick_check.py`
4. **לפרסם בפרודקשן** עם Render או Heroku

המערכת כוללת כל מה שצריך: אבטחה, fallback, UI מתקדם, ותמיכה מלאה בעברית!

צריך עזרה? הרץ `python quick_check.py` לבדיקה מהירה של המערכת.
