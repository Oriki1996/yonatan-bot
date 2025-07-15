# advanced_fallback_system.py - v2.0 - Enhanced with Type Hints and Better Structure
"""
מערכת fallback מתקדמת לצ'אט בוט הורות עם type hints מלאים
"""

import json
import re
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum

# Setup logging
logger = logging.getLogger(__name__)

class AgeGroup(Enum):
    """קבוצות גיל למתבגרים"""
    EARLY_TEEN = "early_teen"  # 11-14
    MID_TEEN = "mid_teen"      # 14-16
    LATE_TEEN = "late_teen"    # 16-18
    YOUNG_ADULT = "young_adult" # 18-21

class ChallengeCategory(Enum):
    """קטגוריות אתגרים בהורות"""
    COMMUNICATION = "communication"
    ACADEMICS = "academics"
    EMOTIONAL_REGULATION = "emotional_regulation"
    SCREEN_TIME = "screen_time"
    SOCIAL_ISSUES = "social_issues"
    BEHAVIORAL_ISSUES = "behavioral_issues"
    INDEPENDENCE = "independence"
    SLEEP_ROUTINE = "sleep_routine"
    FAMILY_DYNAMICS = "family_dynamics"
    SELF_ESTEEM = "self_esteem"
    ANXIETY_STRESS = "anxiety_stress"
    PEER_PRESSURE = "peer_pressure"
    IDENTITY_EXPLORATION = "identity_exploration"
    ROMANTIC_RELATIONSHIPS = "romantic_relationships"
    SUBSTANCE_USE = "substance_use"
    EATING_HABITS = "eating_habits"
    RESPONSIBILITIES = "responsibilities"
    FUTURE_PLANNING = "future_planning"
    AGGRESSION = "aggression"
    WITHDRAWAL = "withdrawal"

class ConversationStage(Enum):
    """שלבי השיחה"""
    GREETING = "greeting"
    PROBLEM_IDENTIFICATION = "problem_identification"
    EXPLORATION = "exploration"
    CBT_INTERVENTION = "cbt_intervention"
    ACTION_PLANNING = "action_planning"
    SUPPORT_RESOURCES = "support_resources"
    FOLLOW_UP = "follow_up"

class CBTTechnique(Enum):
    """טכניקות CBT זמינות"""
    COGNITIVE_RESTRUCTURING = "cognitive_restructuring"
    THOUGHT_CHALLENGING = "thought_challenging"
    BEHAVIORAL_ACTIVATION = "behavioral_activation"
    GROUNDING_TECHNIQUES = "grounding_techniques"
    COMMUNICATION_SKILLS = "communication_skills"
    PROBLEM_SOLVING = "problem_solving"
    EMOTION_REGULATION = "emotion_regulation"
    MINDFULNESS = "mindfulness"
    EXPOSURE_THERAPY = "exposure_therapy"
    POSITIVE_REINFORCEMENT = "positive_reinforcement"

@dataclass
class ResponseContext:
    """הקשר השיחה עם ההורה"""
    parent_name: str = "הורה יקר"
    child_name: str = "המתבגר שלך"
    child_age: int = 15
    child_gender: str = "לא צוין"
    main_challenge: str = "תקשורת וריבים"
    previous_attempts: List[str] = field(default_factory=list)
    conversation_stage: ConversationStage = ConversationStage.GREETING
    session_insights: Dict[str, Any] = field(default_factory=dict)
    
    def get_age_group(self) -> AgeGroup:
        """קביעת קבוצת גיל"""
        if self.child_age <= 14:
            return AgeGroup.EARLY_TEEN
        elif self.child_age <= 16:
            return AgeGroup.MID_TEEN
        elif self.child_age <= 18:
            return AgeGroup.LATE_TEEN
        else:
            return AgeGroup.YOUNG_ADULT

@dataclass
class SessionData:
    """נתוני סשן"""
    messages: List[str] = field(default_factory=list)
    identified_intents: List[str] = field(default_factory=list)
    conversation_stages: List[str] = field(default_factory=list)
    emotional_states: List[str] = field(default_factory=list)
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())
    session_start: str = field(default_factory=lambda: datetime.now().isoformat())
    interaction_count: int = 0

class AdvancedFallbackSystem:
    """מערכת fallback מתקדמת"""
    
    def __init__(self):
        """אתחול המערכת"""
        self.conversation_state: Dict[str, SessionData] = {}
        self.challenge_database: Dict[ChallengeCategory, Dict[str, Any]] = self._build_challenge_database()
        self.cbt_techniques: Dict[CBTTechnique, Dict[str, Any]] = self._build_cbt_techniques()
        self.response_templates: Dict[str, List[str]] = self._build_response_templates()
        self.intent_patterns: Dict[str, Any] = self._build_intent_patterns()
        self.conversation_flows: Dict[str, List[ConversationStage]] = self._build_conversation_flows()
        
        logger.info("🚀 מערכת Fallback מתקדמת אותחלה בהצלחה")
    
    def _build_challenge_database(self) -> Dict[ChallengeCategory, Dict[str, Any]]:
        """בניית מאגר האתגרים המקיף"""
        return {
            ChallengeCategory.COMMUNICATION: {
                "title": "קשיי תקשורת והתנגדות",
                "age_variations": {
                    AgeGroup.EARLY_TEEN: {
                        "common_issues": [
                            "לא מקשיב/ה כשאני מדבר/ת",
                            "עונה בגסות או בחוסר כבוד",
                            "נסגר/ת ולא רוצה לדבר",
                            "מתווכח/ת על הכל"
                        ],
                        "cbt_approach": "זיהוי דפוסי תקשורת לא יעילים והחלפתם בגישה חיובית",
                        "practical_tools": [
                            "טכניקת ההקשבה הפעילה",
                            "שיחה ברגע שקט, לא בעת משבר",
                            "שימוש ב'אני' במקום 'אתה'",
                            "קביעת זמן יומי לשיחה קצרה"
                        ]
                    },
                    AgeGroup.MID_TEEN: {
                        "common_issues": [
                            "חושב/ת שהוא/היא יודע/ת הכל",
                            "דוחה שיחות חשובות",
                            "מתבטא/ת בצורה פוגענית",
                            "מסתיר/ה דברים חשובים"
                        ],
                        "cbt_approach": "הבנת הצורך בעצמאות תוך שמירה על קשר",
                        "practical_tools": [
                            "מתן בחירות במסגרת גבולות",
                            "הכרה בדעותיו/יה גם אם לא מסכימים",
                            "שימוש בשאלות פתוחות",
                            "איזון בין תמיכה לעצמאות"
                        ]
                    },
                    AgeGroup.LATE_TEEN: {
                        "common_issues": [
                            "מתנהג/ת כמו מבוגר/ת אבל לא לוקח/ת אחריות",
                            "מבקש/ת פרטיות מוחלטת",
                            "מתעמת/ת על החלטות הורות",
                            "מתרחק/ת מהמשפחה"
                        ],
                        "cbt_approach": "מעבר הדרגתי לתקשורת מבוגרים תוך שמירה על גבולות",
                        "practical_tools": [
                            "דיונים כמו עם מבוגר צעיר",
                            "הסבר הגיון מאחורי כללים",
                            "מתן אחריות הדרגתית",
                            "כבוד הדדי בשיחה"
                        ]
                    }
                }
            },
            
            ChallengeCategory.ACADEMICS: {
                "title": "קשיים בלימודים והישגים",
                "age_variations": {
                    AgeGroup.EARLY_TEEN: {
                        "common_issues": [
                            "לא עושה שיעורי בית",
                            "ציונים יורדים",
                            "מתלונן/ת שהמקצועות קשים",
                            "דוחה הכנה למבחנים"
                        ],
                        "cbt_approach": "בניית הרגלי למידה חיוביים וטיפול בחרדת ביצוע",
                        "practical_tools": [
                            "חלוקת המשימות למקטעים קטנים",
                            "יצירת סביבת למידה נוחה",
                            "מערכת תגמולים והכרה",
                            "עזרה בארגון והתכנון"
                        ]
                    },
                    AgeGroup.MID_TEEN: {
                        "common_issues": [
                            "חוסר מוטיבציה ללמידה",
                            "השוואות לחברים",
                            "לחץ בנוגע לעתיד",
                            "בחירת מגמה או התמחות"
                        ],
                        "cbt_approach": "מציאת המוטיבציה הפנימית וקשר ללמידה",
                        "practical_tools": [
                            "קישור הלמידה למטרות אישיות",
                            "שיחה על חולשות וחוזקות",
                            "יצירת תכנית לימודים אישית",
                            "הפחתת לחץ והשוואות"
                        ]
                    },
                    AgeGroup.LATE_TEEN: {
                        "common_issues": [
                            "קושי בבחירת כיוון לעתיד",
                            "לחץ מבחני בגרות/פסיכומטרי",
                            "איזון בין לימודים לעבודה",
                            "החלטות לגבי שירות צבאי/לאומי"
                        ],
                        "cbt_approach": "תכנון אסטרטגי לעתיד עם ניהול חרדה",
                        "practical_tools": [
                            "מיפוי כישורים ותחומי עניין",
                            "תכנון שלבי לקראת המטרה",
                            "טכניקות להפחתת חרדה",
                            "שיחה על אפשרויות שונות"
                        ]
                    }
                }
            },
            
            ChallengeCategory.EMOTIONAL_REGULATION: {
                "title": "ויסות רגשי והתפרצויות",
                "age_variations": {
                    AgeGroup.EARLY_TEEN: {
                        "common_issues": [
                            "התפרצויות זעם בלתי צפויות",
                            "מצבי רוח משתנים",
                            "בכי או תסכול מהיר",
                            "קושי להרגע אחרי כעס"
                        ],
                        "cbt_approach": "זיהוי טריגרים וטכניקות הרגעה",
                        "practical_tools": [
                            "טכניקת הנשימה העמוקה",
                            "זיהוי רגשות בשלב מוקדם",
                            "יצירת מרחב בטוח להרגעה",
                            "שיחה על הרגש אחרי ההתפרצות"
                        ]
                    },
                    AgeGroup.MID_TEEN: {
                        "common_issues": [
                            "מתח רגשי קבוע",
                            "קושי לבטא רגשות במילים",
                            "התנהגות אימפולסיבית",
                            "רגשות אשמה אחרי התפרצות"
                        ],
                        "cbt_approach": "בניית מיומנויות ויסות רגשי מתקדמות",
                        "practical_tools": [
                            "יומן רגשות יומי",
                            "טכניקות מיינדפולנס",
                            "איזון בין הבנה לגבולות",
                            "פיתוח שפה רגשית"
                        ]
                    },
                    AgeGroup.LATE_TEEN: {
                        "common_issues": [
                            "חרדה מעתיד ולחצים",
                            "קושי בהתמודדות עם דחיות",
                            "מתח בזהות האישית",
                            "תחושת בדידות"
                        ],
                        "cbt_approach": "פיתוח חוסן רגשי ומיומנויות התמודדות",
                        "practical_tools": [
                            "שיחה על זהות ושינויים",
                            "טכניקות לניהול חרדה",
                            "בניית רשת תמיכה",
                            "עבודה על דימוי עצמי"
                        ]
                    }
                }
            },
            
            ChallengeCategory.SCREEN_TIME: {
                "title": "זמן מסך והתמכרויות דיגיטליות",
                "age_variations": {
                    AgeGroup.EARLY_TEEN: {
                        "common_issues": [
                            "מבלה שעות רצופות מול המסך",
                            "מתנגד/ת לסיום זמן המסך",
                            "מזניח/ה חובות בגלל המסך",
                            "התפרצויות כשמגבילים"
                        ],
                        "cbt_approach": "יצירת מודעות לשימוש והחלפת הרגלים",
                        "practical_tools": [
                            "הגדרת זמנים קבועים למסך",
                            "יצירת פעילויות חלופיות",
                            "שימוש באפליקציות בקרה",
                            "הסכמות ברורות וגבולות"
                        ]
                    },
                    AgeGroup.MID_TEEN: {
                        "common_issues": [
                            "עייפות מזמן מסך מופרז",
                            "השפעה על ציונים וחברויות",
                            "שימוש בלילה וקושי בשינה",
                            "התמכרות למשחקים או רשתות"
                        ],
                        "cbt_approach": "הבנת הצרכים מאחורי השימוש והחלפתם",
                        "practical_tools": [
                            "זיהוי מה המסך נותן (בריחה, חברות)",
                            "מציאת פעילויות שנותנות את אותו הדבר",
                            "קביעת זמנים ללא מסך",
                            "שיחה על איכות השינה"
                        ]
                    },
                    AgeGroup.LATE_TEEN: {
                        "common_issues": [
                            "שימוש כדרך בריחה מלחצים",
                            "השפעה על תפקוד יומיומי",
                            "קושי בריכוז במטלות",
                            "חששות לגבי עתיד דיגיטלי"
                        ],
                        "cbt_approach": "פיתוח איזון בריא עם טכנולוגיה",
                        "practical_tools": [
                            "הגדרת מטרות דיגיטליות",
                            "שימוש במסך לפעילויות חיוביות",
                            "טכניקות מיינדפולנס",
                            "תכנון קריירה הכוללת טכנולוגיה"
                        ]
                    }
                }
            }
        }
    
    def _build_cbt_techniques(self) -> Dict[CBTTechnique, Dict[str, Any]]:
        """בניית מאגר טכניקות CBT"""
        return {
            CBTTechnique.COGNITIVE_RESTRUCTURING: {
                "title": "שיחזור קוגניטיבי",
                "description": "זיהוי וטיפול במחשבות לא מועילות",
                "steps": [
                    "זיהוי המחשבה הבעייתית",
                    "בדיקת הראיות לטובת ונגד",
                    "יצירת מחשבה חלופית מאוזנת",
                    "תרגול המחשבה החדשה"
                ],
                "example_card": "CARD[מחשבות מועילות|במקום 'הילד שלי לעולם לא ישתנה', נסה לחשוב 'השינוי דורש זמן וסבלנות, ואני יכול/ה לעזור בתהליך']"
            },
            
            CBTTechnique.THOUGHT_CHALLENGING: {
                "title": "אתגור מחשבות",
                "description": "בדיקת מחשבות אוטומטיות",
                "steps": [
                    "זיהוי המחשבה האוטומטית",
                    "שאלת עצמך: האם זה אמיתי?",
                    "חיפוש ראיות וחלופות",
                    "יצירת מחשבה מאוזנת יותר"
                ],
                "example_card": "CARD[5 שאלות לאתגור מחשבות|1) האם זה באמת כל כך גרוע? 2) מה הכי רע יכול לקרות? 3) איך אני אייעץ לחבר/ה במצב כזה? 4) מה עבד בעבר? 5) איך אני ארגיש בעוד שנה?]"
            },
            
            CBTTechnique.COMMUNICATION_SKILLS: {
                "title": "כישורי תקשורת",
                "description": "שיפור דרך התקשורת במשפחה",
                "steps": [
                    "הקשבה פעילה",
                    "הבעת רגשות ב'אני' ולא ב'אתה'",
                    "הכרה ברגשות הילד",
                    "חיפוש פתרונות יחד"
                ],
                "example_card": "CARD[נוסחת התקשורת|1) אני רואה/ת ש... 2) אני מרגיש/ה... 3) אני צריך/ה... 4) בוא/י נמצא פתרון יחד]"
            },
            
            CBTTechnique.PROBLEM_SOLVING: {
                "title": "פתרון בעיות",
                "description": "גישה שיטתית לפתרון קונפליקטים",
                "steps": [
                    "הגדרת הבעיה בצורה ספציפית",
                    "רישום כל הפתרונות האפשריים",
                    "הערכת כל פתרון",
                    "בחירת הפתרון הטוב ביותר"
                ],
                "example_card": "CARD[שלבי פתרון בעיות|1) מה בדיוק הבעיה? 2) מה כל האפשרויות? 3) מה היתרונות והחסרונות? 4) מה נבחר לנסות? 5) איך נבדוק שזה עובד?]"
            },
            
            CBTTechnique.EMOTION_REGULATION: {
                "title": "ויסות רגשי",
                "description": "ניהול רגשות עזים",
                "steps": [
                    "זיהוי הרגש בשלב מוקדם",
                    "שימוש בטכניקות הרגעה",
                    "המתנה לפני פעולה",
                    "חזרה לשיחה בשקט"
                ],
                "example_card": "CARD[טכניקת 5-4-3-2-1 להרגעה|5 דברים שאתה רואה, 4 דברים שאתה נוגע, 3 דברים שאתה שומע, 2 דברים שאתה מריח, 1 דבר שאתה טועם]"
            },
            
            CBTTechnique.POSITIVE_REINFORCEMENT: {
                "title": "חיזוק חיובי",
                "description": "עידוד התנהגות רצויה",
                "steps": [
                    "זיהוי התנהגות חיובית",
                    "מתן הכרה מיידית",
                    "הסבר מדוע זה חשוב",
                    "יצירת מערכת הכרה"
                ],
                "example_card": "CARD[דרכים לחיזוק חיובי|1) הכרה מילולית ספציפית 2) זמן איכות נוסף 3) יתרונות מיוחדים 4) שיתוף בהצלחה עם אחרים]"
            }
        }
    
    def _build_response_templates(self) -> Dict[str, List[str]]:
        """בניית תבניות תגובה"""
        return {
            "greeting": [
                "שלום {parent_name}! אני יונתן, פסיכו-בוט חינוכי. שמחתי שבאת לדבר איתי על {main_challenge}. איך אני יכול לעזור לך היום?",
                "אהלן {parent_name}, נעים מאוד! ראיתי שאתה מתמודד/ת עם {main_challenge} עם {child_name}. בוא/י נתחיל מהתחלה - איך זה מרגיש לך?",
                "היי {parent_name}! זה יונתן. אני כאן כדי לעזור לך עם {main_challenge}. איך היום של {child_name} וכמה זה מאתגר לך?"
            ],
            
            "empathy": [
                "זה נשמע מאוד מתסכל, {parent_name}. הרבה הורים חווים את מה שאת/ה מתאר/ת.",
                "אני מבין/ה כמה זה יכול להיות קשה. זה לא קל להיות הורה של מתבגר.",
                "תחושת הכעס וההיאבקות שלך מובנת לחלוטין. אתה לא לבד במצב הזה.",
                "זה באמת מאתגר. אני מעריך שאת/ה מחפש/ת דרכים לשפר את המצב."
            ],
            
            "encouragement": [
                "אתה עושה עבודה מעולה, {parent_name}. זה לא קל מה שאתה עובר.",
                "איזה הבנה חשובה! זה כבר צעד גדול קדימה.",
                "אני רואה שאתה מתמיד ורוצה לשפר. זה באמת מעורר השראה.",
                "כל הכבוד על הנכונות לנסות דרכים חדשות!"
            ]
        }
    
    def _build_intent_patterns(self) -> Dict[str, Any]:
        """בניית דפוסים לזיהוי כוונות"""
        return {
            "greeting": [
                r"שלום|היי|אהלן|בוקר טוב|ערב טוב",
                r"רוצה לדבר|צריך עזרה|יש לי בעיה"
            ],
            
            "emotional_expression": [
                r"מרגיש|מתוסכל|כועס|עצוב|מתח|לחץ|עייף",
                r"נמאס לי|מספיק|לא יכול יותר|קשה לי"
            ],
            
            "problem_description": [
                r"הבעיה היא|הקושי הוא|מה שקורה|המצב הוא",
                r"הוא לא|היא לא|אנחנו לא|זה לא עובד"
            ],
            
            "seeking_advice": [
                r"מה עושים|איך מתמודדים|מה אפשר לעשות|יש רעיון",
                r"מה הייתם עושים|איך פותרים|מה הפתרון"
            ],
            
            "resistance": [
                r"לא יעבוד|כבר ניסיתי|זה לא עוזר|זה לא מתאים",
                r"אתה לא מבין|זה שונה|המצב שלי יוצא דופן"
            ],
            
            "urgency": [
                r"דחוף|מיידי|עכשיו|היום|לא יכול לחכות",
                r"עזרה|SOS|אני מתמוטט|בקריזה"
            ],
            
            "success_sharing": [
                r"עבד|הצלחתי|השתפר|טוב יותר|התקדמנו",
                r"תודה|עזרת|יופי|זה מעולה"
            ]
        }
    
    def _build_conversation_flows(self) -> Dict[str, List[ConversationStage]]:
        """בניית זרימות שיחה"""
        return {
            "standard_flow": [
                ConversationStage.GREETING,
                ConversationStage.PROBLEM_IDENTIFICATION,
                ConversationStage.EXPLORATION,
                ConversationStage.CBT_INTERVENTION,
                ConversationStage.ACTION_PLANNING,
                ConversationStage.SUPPORT_RESOURCES,
                ConversationStage.FOLLOW_UP
            ],
            
            "crisis_flow": [
                ConversationStage.GREETING,
                ConversationStage.PROBLEM_IDENTIFICATION,
                ConversationStage.CBT_INTERVENTION,
                ConversationStage.ACTION_PLANNING,
                ConversationStage.SUPPORT_RESOURCES
            ],
            
            "follow_up_flow": [
                ConversationStage.FOLLOW_UP,
                ConversationStage.EXPLORATION,
                ConversationStage.CBT_INTERVENTION,
                ConversationStage.ACTION_PLANNING
            ]
        }
    
    def identify_intent(self, user_input: str) -> Tuple[str, float]:
        """זיהוי כוונת המשתמש"""
        user_input_lower = user_input.lower()
        
        # בדיקת דחיפות
        urgency_score = self._calculate_pattern_score(user_input_lower, self.intent_patterns["urgency"])
        
        # זיהוי רגש כללי
        emotional_score = self._calculate_pattern_score(user_input_lower, self.intent_patterns["emotional_expression"])
        
        # זיהוי בקשה לעזרה
        advice_seeking_score = self._calculate_pattern_score(user_input_lower, self.intent_patterns["seeking_advice"])
        
        # זיהוי התנגדות
        resistance_score = self._calculate_pattern_score(user_input_lower, self.intent_patterns["resistance"])
        
        # החלטה על כוונה עיקרית
        scores = {
            "urgent_help": urgency_score,
            "emotional_expression": emotional_score,
            "seeking_advice": advice_seeking_score,
            "resistance": resistance_score
        }
        
        if max(scores.values()) > 0:
            intent = max(scores, key=scores.get)
            confidence = scores[intent]
            return intent, confidence
        
        return "general_conversation", 0.5
    
    def _calculate_pattern_score(self, text: str, patterns: List[str]) -> float:
        """חישוב ציון התאמה לדפוס"""
        score = 0
        for pattern in patterns:
            if re.search(pattern, text):
                score += 1
        return score / len(patterns) if patterns else 0
    
    def get_challenge_category(self, challenge_text: str) -> ChallengeCategory:
        """מיפוי טקסט לקטגוריית אתגר"""
        challenge_mapping = {
            "תקשורת וריבים": ChallengeCategory.COMMUNICATION,
            "קשיים בלימודים": ChallengeCategory.ACADEMICS,
            "ויסות רגשי והתפרצויות": ChallengeCategory.EMOTIONAL_REGULATION,
            "זמן מסך והתמכרויות": ChallengeCategory.SCREEN_TIME,
            "קשיים חברתיים": ChallengeCategory.SOCIAL_ISSUES,
            "התנהגות מרדנית": ChallengeCategory.BEHAVIORAL_ISSUES,
            "חרדה ולחץ": ChallengeCategory.ANXIETY_STRESS,
            "בעיות שינה": ChallengeCategory.SLEEP_ROUTINE,
            "עצמאות ואחריות": ChallengeCategory.INDEPENDENCE
        }
        return challenge_mapping.get(challenge_text, ChallengeCategory.COMMUNICATION)
    
    def get_contextual_response(self, 
                               context: ResponseContext, 
                               user_input: str, 
                               intent: str, 
                               confidence: float) -> str:
        """יצירת תגובה מותאמת אישית"""
        try:
            # קביעת קטגוריית האתגר וקבוצת הגיל
            challenge_category = self.get_challenge_category(context.main_challenge)
            age_group = context.get_age_group()
            
            # קבלת נתוני האתגר הספציפי
            challenge_data = self.challenge_database.get(challenge_category, {})
            age_specific_data = challenge_data.get("age_variations", {}).get(age_group, {})
            
            # בחירת טכניקת CBT מתאימה
            cbt_technique = self._select_cbt_technique(intent, challenge_category)
            
            # בניית התגובה לפי השלב בשיחה
            response_parts = []
            
            # התחלה עם אמפתיה
            if context.conversation_stage == ConversationStage.GREETING:
                response_parts.append(self._get_greeting_response(context))
            else:
                response_parts.append(self._get_empathy_response(context, intent))
            
            # הוספת תוכן ספציפי לפי הכוונה
            if intent in ["communication", "academics", "screen_time", "behavior"]:
                response_parts.append(self._get_specific_challenge_response(
                    challenge_category, age_group, age_specific_data, context
                ))
            
            # הוספת כלי CBT
            if cbt_technique:
                response_parts.append(self._get_cbt_response(cbt_technique, context))
            
            # הוספת צעדים פרקטיים
            response_parts.append(self._get_action_steps(challenge_category, age_group, context))
            
            # הוספת עידוד וסיכום
            response_parts.append(self._get_encouragement(context))
            
            return "\n\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            return self._get_fallback_error_response(context)
    
    def _select_cbt_technique(self, intent: str, challenge_category: ChallengeCategory) -> Optional[CBTTechnique]:
        """בחירת טכניקת CBT מתאימה"""
        technique_mapping = {
            "emotional_expression": CBTTechnique.EMOTION_REGULATION,
            "communication": CBTTechnique.COMMUNICATION_SKILLS,
            "academics": CBTTechnique.PROBLEM_SOLVING,
            "screen_time": CBTTechnique.BEHAVIORAL_ACTIVATION,
            "behavior": CBTTechnique.POSITIVE_REINFORCEMENT,
            "resistance": CBTTechnique.COGNITIVE_RESTRUCTURING,
            "urgent_help": CBTTechnique.GROUNDING_TECHNIQUES
        }
        
        return technique_mapping.get(intent, CBTTechnique.THOUGHT_CHALLENGING)
    
    def _get_greeting_response(self, context: ResponseContext) -> str:
        """יצירת תגובת פתיחה"""
        templates = self.response_templates["greeting"]
        template = random.choice(templates)
        return template.format(
            parent_name=context.parent_name,
            child_name=context.child_name,
            main_challenge=context.main_challenge
        )
    
    def _get_empathy_response(self, context: ResponseContext, intent: str) -> str:
        """יצירת תגובת אמפתיה"""
        templates = self.response_templates["empathy"]
        template = random.choice(templates)
        return template.format(parent_name=context.parent_name)
    
    def _get_specific_challenge_response(self, 
                                       challenge_category: ChallengeCategory, 
                                       age_group: AgeGroup,
                                       age_specific_data: Dict[str, Any],
                                       context: ResponseContext) -> str:
        """יצירת תגובה ספציפית לאתגר"""
        common_issues = age_specific_data.get("common_issues", [])
        cbt_approach = age_specific_data.get("cbt_approach", "")
        
        response = f"מה שאת/ה מתאר/ת מאוד נפוץ עם {context.child_name} בגיל {context.child_age}. "
        
        if common_issues:
            response += f"הרבה הורים מדווחים על דברים כמו: {', '.join(common_issues[:2])}. "
        
        if cbt_approach:
            response += f"הגישה שלי כאן היא {cbt_approach}. "
        
        return response
    
    def _get_cbt_response(self, technique: CBTTechnique, context: ResponseContext) -> str:
        """יצירת תגובה עם כלי CBT"""
        technique_data = self.cbt_techniques.get(technique, {})
        title = technique_data.get("title", "")
        description = technique_data.get("description", "")
        example_card = technique_data.get("example_card", "")
        
        response = f"אני רוצה לשתף איתך כלי שנקרא '{title}' - {description}. "
        
        if example_card:
            response += f"\n\n{example_card}"
        
        return response
    
    def _get_action_steps(self, 
                         challenge_category: ChallengeCategory,
                         age_group: AgeGroup,
                         context: ResponseContext) -> str:
        """יצירת צעדים פרקטיים"""
        challenge_data = self.challenge_database.get(challenge_category, {})
        age_specific_data = challenge_data.get("age_variations", {}).get(age_group, {})
        practical_tools = age_specific_data.get("practical_tools", [])
        
        if not practical_tools:
            return "הנה כמה צעדים שיכולים לעזור: [תתחיל לאט], [תהיה סבלן/ית], [תשמור על רוגע]"
        
        response = "הנה תוכנית פעולה פרקטית:\n\n"
        
        for i, tool in enumerate(practical_tools[:4], 1):
            response += f"[צעד {i}: {tool}]\n"
        
        response += f"\nמה דעתך שנתחיל עם אחד מהצעדים האלה עם {context.child_name}?"
        
        return response
    
    def _get_encouragement(self, context: ResponseContext) -> str:
        """יצירת מסר עידוד"""
        templates = self.response_templates["encouragement"]
        template = random.choice(templates)
        return template.format(parent_name=context.parent_name)
    
    def _get_fallback_error_response(self, context: ResponseContext) -> str:
        """תגובת שגיאה כשהכל נכשל"""
        return f"אני מתנצל {context.parent_name}, נתקלתי בקושי טכני. הדבר החשוב הוא שאת/ה פה ורוצה לעזור ל{context.child_name}. זה כבר הרבה! 🤗"
    
    def detect_emotional_state(self, user_input: str) -> Tuple[str, float]:
        """זיהוי מצב רגשי של המשתמש"""
        emotional_indicators = {
            "stress": {
                "keywords": ["מתח", "לחץ", "עייף", "מותש", "עמוס", "לא מספיק"],
                "patterns": [r"אין לי כוח", r"מספיק לי", r"נמאס לי"]
            },
            "anger": {
                "keywords": ["כועס", "זועם", "עצבני", "מתוסכל", "מרגיז"],
                "patterns": [r"מספיק כבר", r"לא יכול יותר", r"מטריף אותי"]
            },
            "sadness": {
                "keywords": ["עצוב", "מדוכא", "כואב", "קשה", "בוכה"],
                "patterns": [r"לא יודע מה לעשות", r"מרגיש רע", r"כל כך קשה"]
            },
            "anxiety": {
                "keywords": ["חרד", "דואג", "פחד", "מתרגש", "בהלה"],
                "patterns": [r"מה יהיה", r"איך אני", r"מה אם"]
            },
            "hope": {
                "keywords": ["מקווה", "רוצה לנסות", "יש אפשרות", "אולי"],
                "patterns": [r"אם רק", r"בואו ננסה", r"יש לי תקווה"]
            }
        }
        
        user_input_lower = user_input.lower()
        emotion_scores = {}
        
        for emotion, indicators in emotional_indicators.items():
            score = 0
            
            # בדיקת מילות מפתח
            for keyword in indicators["keywords"]:
                if keyword in user_input_lower:
                    score += 1
            
            # בדיקת דפוסים
            for pattern in indicators["patterns"]:
                if re.search(pattern, user_input_lower):
                    score += 2
            
            if score > 0:
                emotion_scores[emotion] = score / (len(indicators["keywords"]) + len(indicators["patterns"]))
        
        if not emotion_scores:
            return "neutral", 0.5
        
        # מציאת הרגש הדומיננטי
        dominant_emotion = max(emotion_scores, key=emotion_scores.get)
        confidence = emotion_scores[dominant_emotion]
        
        return dominant_emotion, confidence
    
    def analyze_conversation_pattern(self, session_id: str) -> Dict[str, Any]:
        """ניתוח דפוסי שיחה לתובנות"""
        if session_id not in self.conversation_state:
            return {
                "session_found": False,
                "primary_concerns": [],
                "conversation_flow": [],
                "recommendations": []
            }
        
        session_data = self.conversation_state[session_id]
        
        # ניתוח הדפוסים
        primary_concerns = list(set(session_data.identified_intents))
        conversation_flow = session_data.conversation_stages
        
        # יצירת המלצות
        recommendations = []
        
        if "resistance" in primary_concerns:
            recommendations.append("מומלץ להתמקד בבניית אמון")
        
        if "emotional_expression" in primary_concerns:
            recommendations.append("דרוש ליווי רגשי נוסף")
        
        if len(primary_concerns) > 3:
            recommendations.append("יש להתמקד בבעיה אחת בכל פעם")
        
        return {
            "session_found": True,
            "primary_concerns": primary_concerns,
            "conversation_flow": conversation_flow,
            "recommendations": recommendations,
            "session_length": len(session_data.messages),
            "last_interaction": session_data.last_update
        }
    
    def generate_personalized_summary(self, session_id: str, context: ResponseContext) -> str:
        """יצירת סיכום אישי של השיחה"""
        analysis = self.analyze_conversation_pattern(session_id)
        
        if not analysis["session_found"]:
            return f"היי {context.parent_name}, עדיין לא יש לנו מספיק מידע לסיכום. בוא/י נמשיך לדבר!"
        
        summary_parts = []
        
        # פתיחה אישית
        summary_parts.append(f"היי {context.parent_name}, אני רוצה לסכם את מה שדיברנו על {context.child_name}:")
        
        # נושאים עיקריים
        if analysis["primary_concerns"]:
            concerns_hebrew = {
                "communication": "תקשורת",
                "academics": "לימודים", 
                "emotional_expression": "ביטוי רגשי",
                "behavior": "התנהגות",
                "screen_time": "זמן מסך"
            }
            
            concern_names = [concerns_hebrew.get(c, c) for c in analysis["primary_concerns"][:3]]
            summary_parts.append(f"הנושאים העיקריים: {', '.join(concern_names)}")
        
        # המלצות
        if analysis["recommendations"]:
            summary_parts.append("המלצות שלי:")
            for rec in analysis["recommendations"][:2]:
                summary_parts.append(f"• {rec}")
        
        # סיום חיובי
        summary_parts.append(f"זכור/י, {context.parent_name}, אתה עושה עבודה חשובה. {context.child_name} בר מזל שיש לו/ה הורה כמוך.")
        
        return "\n\n".join(summary_parts)
    
    def get_fallback_response(self, 
                             user_input: str, 
                             session_id: Optional[str] = None,
                             questionnaire_data: Optional[Dict[str, Any]] = None) -> str:
        """נקודת הכניסה הראשית למערכת Fallback"""
        
        try:
            # קביעת קונטקסט
            if questionnaire_data:
                context = ResponseContext(
                    parent_name=questionnaire_data.get("parent_name", "הורה יקר"),
                    child_name=questionnaire_data.get("child_name", "המתבגר שלך"),
                    child_age=int(questionnaire_data.get("child_age", 15)),
                    child_gender=questionnaire_data.get("child_gender", "לא צוין"),
                    main_challenge=questionnaire_data.get("main_challenge", "תקשורת וריבים")
                )
            else:
                context = ResponseContext()
            
            # אתחול מצב שיחה
            if session_id:
                if session_id not in self.conversation_state:
                    self.conversation_state[session_id] = SessionData()
                
                session_data = self.conversation_state[session_id]
                session_data.messages.append(user_input)
                session_data.interaction_count += 1
                session_data.last_update = datetime.now().isoformat()
            
            # טיפול בהודעת התחלה
            if user_input == "START_CONVERSATION":
                context.conversation_stage = ConversationStage.GREETING
                response = self._get_greeting_response(context)
                return response
            
            # זיהוי כוונה ומצב רגשי
            intent, confidence = self.identify_intent(user_input)
            emotional_state, emotion_confidence = self.detect_emotional_state(user_input)
            
            # שמירת הכוונה והרגש במצב השיחה
            if session_id:
                session_data = self.conversation_state[session_id]
                session_data.identified_intents.append(intent)
                session_data.emotional_states.append(emotional_state)
                session_data.conversation_stages.append(context.conversation_stage.value)
            
            # יצירת תגובה מותאמת
            response = self.get_contextual_response(context, user_input, intent, confidence)
            
            # הוספת חותמת מערכת fallback
            response += "\n\n💡 *תגובה מהמערכת החכמה של יונתן הפסיכו-בוט*"
            
            logger.info(f"Generated fallback response for intent: {intent} (confidence: {confidence})")
            return response
            
        except Exception as e:
            logger.error(f"Error in fallback system: {e}")
            # תגובת חירום
            parent_name = questionnaire_data.get("parent_name", "הורה יקר") if questionnaire_data else "הורה יקר"
            return f"אני מתנצל, {parent_name}, נתקלתי בקושי טכני. בינתיים, זכור/י שאת/ה עושה עבודה חשובה כהורה. 🤗"

# יצירת מופע גלובלי
def create_advanced_fallback_system() -> Optional[AdvancedFallbackSystem]:
    """יצירת מערכת fallback מתקדמת עם טיפול בשגיאות"""
    try:
        return AdvancedFallbackSystem()
    except Exception as e:
        logger.error(f"שגיאה ביצירת מערכת fallback: {e}")
        return None

# Export
__all__ = [
    'AdvancedFallbackSystem',
    'ResponseContext',
    'AgeGroup',
    'ChallengeCategory',
    'ConversationStage',
    'CBTTechnique',
    'create_advanced_fallback_system'
]