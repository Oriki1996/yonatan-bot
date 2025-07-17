// Yonatan Psycho-Bot Widget v15.0 - Enhanced with better UX and reliability
(function() {
    if (window.yonatanWidgetLoaded) return;
    window.yonatanWidgetLoaded = true;

    const API_URL = window.location.origin;
    let csrfToken = null;
    let connectionRetries = 0;
    const MAX_RETRIES = 3;

    let state = {
        uiState: 'closed',
        sessionId: localStorage.getItem('yonatan_session_id'),
        conversationHistory: JSON.parse(localStorage.getItem('yonatan_conversation') || '[]'),
        questionnaireStep: 0,
        questionnaireData: {},
        isTyping: false,
        lastActivity: Date.now(),
        systemHealth: null
    };

    const elements = {
        chatButton: null,
        widgetContainer: null,
        messagesContainer: null,
        chatInput: null,
        statusIndicator: null
    };

    const questionnaire = [
        { id: 'parent_name', question: "נעים מאוד, אני יונתן. איך קוראים לך?", type: 'text', placeholder: "השם שלך", validation: v => v.length >= 2 },
        { id: 'parent_gender', question: "באיזה מגדר לפנות אליך?", type: 'radio', options: ['זכר', 'נקבה', 'אחר'] },
        { id: 'child_name', question: "ומה שם המתבגר/ת שעליו/ה נרצה לדבר?", type: 'text', placeholder: "שם הילד/ה", validation: v => v.length >= 2 },
        { id: 'child_age', question: "בן/בת כמה הוא/היא?", type: 'number', placeholder: "לדוגמה: 15", validation: v => v >= 10 && v <= 25 },
        { id: 'child_gender', question: "ומה המגדר שלו/ה?", type: 'radio', options: ['זכר', 'נקבה', 'אחר'] },
        { id: 'main_challenge', question: "מהו האתגר המרכזי שבו את/ה רוצה להתמקד היום?", type: 'choice', options: ['תקשורת וריבים', 'קשיים בלימודים', 'ויסות רגשי והתפרצויות', 'זמן מסך והתמכרויות', 'קשיים חברתיים', 'התנהגות סיכונית', 'אחר'] },
        { id: 'challenge_context', question: "מתי הבעיה הזו מופיעה בדרך כלל?", type: 'text', placeholder: "למשל, בערבים, סביב הכנת שיעורים...", validation: v => v.length >= 3 },
        { id: 'past_solutions', question: "איך ניסית להתמודד עם זה עד עכשיו?", type: 'text', placeholder: "למשל, ניסיתי לדבר, לקחת את הטלפון...", validation: v => v.length >= 3 },
        { id: 'distress_level', question: "בסקאלה של 1 עד 10, כמה המצב הזה גורם לך למצוקה?", type: 'scale', min: 1, max: 10 },
        { id: 'goal', question: "ומה המטרה העיקרית שלך מהשיחה שלנו?", type: 'choice', options: ['לקבל כלים פרקטיים', 'להבין טוב יותר את הילד/ה', 'להרגיש יותר ביטחון בהורות', 'לפרוק ולשתף'] },
    ];

    // Enhanced CSRF functions
    async function getCSRFToken() {
        try {
            const response = await fetch(`${API_URL}/api/csrf-token`, {
                method: 'GET',
                credentials: 'same-origin'
            });
            if (response.ok) {
                const data = await response.json();
                csrfToken = data.csrf_token;
                console.log('✅ CSRF token received');
                return csrfToken;
            }
        } catch (error) {
            console.warn('⚠️ Failed to get CSRF token:', error);
        }
        return null;
    }

    async function fetchWithCSRF(url, options = {}) {
        if (options.method === 'POST' && !csrfToken) {
            await getCSRFToken();
        }
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (csrfToken && options.method === 'POST') {
            headers['X-CSRFToken'] = csrfToken;
        }
        
        return fetch(url, {
            ...options,
            headers,
            credentials: 'same-origin'
        });
    }

    // Enhanced styles with better UX
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            :root { 
                --primary: #4f46e5; 
                --secondary: #7c3aed; 
                --user-bubble: #eef2ff; 
                --bot-bubble: #f3f4f6;
                --success: #10b981;
                --warning: #f59e0b;
                --danger: #ef4444;
                --shadow: 0 10px 30px rgba(0,0,0,0.15);
            }
            
            #yonatan-widget-button { 
                position: fixed; 
                bottom: 20px; 
                right: 20px; 
                background: var(--primary); 
                color: white; 
                width: 60px; 
                height: 60px; 
                border-radius: 50%; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                box-shadow: var(--shadow); 
                cursor: pointer; 
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
                z-index: 9998; 
                border: none;
                font-size: 24px;
            }
            
            #yonatan-widget-button:hover { 
                transform: scale(1.1) translateY(-2px); 
                box-shadow: 0 15px 40px rgba(0,0,0,0.2); 
            }
            
            #yonatan-widget-button.api-error { 
                background: var(--danger); 
                animation: pulse-error 2s infinite; 
            }
            
            #yonatan-widget-button.fallback-mode { 
                background: var(--warning); 
                animation: pulse-warning 2s infinite; 
            }
            
            #yonatan-widget-button.loading {
                animation: spin 1s linear infinite;
            }
            
            @keyframes pulse-error {
                0%, 100% { box-shadow: var(--shadow); }
                50% { box-shadow: 0 0 20px rgba(239, 68, 68, 0.6); }
            }
            
            @keyframes pulse-warning {
                0%, 100% { box-shadow: var(--shadow); }
                50% { box-shadow: 0 0 20px rgba(245, 158, 11, 0.6); }
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            #yonatan-widget-container { 
                position: fixed; 
                bottom: 20px; 
                right: 20px; 
                width: 400px; 
                height: 600px; 
                max-width: calc(100vw - 40px);
                max-height: calc(100vh - 40px); 
                background: white; 
                border-radius: 16px; 
                box-shadow: var(--shadow); 
                display: flex; 
                flex-direction: column; 
                overflow: hidden; 
                transform: scale(0.5) translateY(100px); 
                opacity: 0; 
                transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); 
                pointer-events: none; 
                z-index: 9999;
            }
            
            #yonatan-widget-container.open { 
                transform: scale(1) translateY(0); 
                opacity: 1; 
                pointer-events: auto; 
            }
            
            .yonatan-header { 
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); 
                color: white; 
                padding: 16px; 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                flex-shrink: 0;
                position: relative;
            }
            
            .yonatan-header::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            }
            
            .yonatan-chat-window { 
                flex-grow: 1; 
                overflow-y: auto; 
                padding: 16px; 
                background: linear-gradient(to bottom, #f9fafb, #f3f4f6); 
                scroll-behavior: smooth;
                scrollbar-width: thin;
                scrollbar-color: var(--primary) transparent;
            }
            
            .yonatan-chat-window::-webkit-scrollbar {
                width: 6px;
            }
            
            .yonatan-chat-window::-webkit-scrollbar-track {
                background: transparent;
            }
            
            .yonatan-chat-window::-webkit-scrollbar-thumb {
                background: var(--primary);
                border-radius: 3px;
            }
            
            .yonatan-message-wrapper { 
                display: flex; 
                margin-bottom: 16px; 
                max-width: 90%; 
                align-items: flex-end; 
                animation: slideInMessage 0.4s ease-out;
            }
            
            .yonatan-message-wrapper.user { 
                margin-left: auto; 
                flex-direction: row-reverse; 
            }
            
            .yonatan-message-wrapper.bot { 
                margin-right: auto; 
            }
            
            @keyframes slideInMessage {
                from { 
                    opacity: 0; 
                    transform: translateY(20px); 
                }
                to { 
                    opacity: 1; 
                    transform: translateY(0); 
                }
            }
            
            .yonatan-avatar { 
                width: 32px; 
                height: 32px; 
                border-radius: 50%; 
                background: linear-gradient(135deg, var(--secondary), var(--primary)); 
                color: white; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                font-weight: bold; 
                flex-shrink: 0; 
                margin: 0 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            .yonatan-message { 
                padding: 12px 16px; 
                border-radius: 18px; 
                line-height: 1.5; 
                word-wrap: break-word;
                position: relative;
            }
            
            .yonatan-message.user { 
                background: linear-gradient(135deg, var(--user-bubble), #e0e7ff); 
                color: #312e81; 
                border-bottom-right-radius: 4px;
                box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1);
            }
            
            .yonatan-message.bot { 
                background: white; 
                color: #374151; 
                border-bottom-left-radius: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                border: 1px solid #e5e7eb;
            }
            
            .yonatan-message.fallback-mode { 
                border-left: 3px solid var(--warning); 
                background: linear-gradient(135deg, #fef3c7, #fde68a);
            }
            
            .fallback-indicator { 
                font-size: 11px; 
                color: #d97706; 
                font-weight: bold; 
                margin-bottom: 5px; 
                padding: 2px 6px; 
                background: rgba(245, 158, 11, 0.2); 
                border-radius: 8px; 
                display: inline-block;
            }
            
            .yonatan-footer { 
                padding: 16px; 
                border-top: 1px solid #e5e7eb; 
                background: white; 
                flex-shrink: 0;
            }
            
            .yonatan-input-area { 
                display: flex; 
                align-items: center; 
                gap: 8px;
            }
            
            .yonatan-input { 
                flex-grow: 1; 
                border: 2px solid #e5e7eb; 
                border-radius: 20px; 
                padding: 10px 16px; 
                font-size: 16px; 
                outline: none; 
                transition: all 0.2s; 
                font-family: inherit;
            }
            
            .yonatan-input:focus { 
                border-color: var(--primary); 
                box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
            }
            
            .yonatan-input:disabled {
                background: #f9fafb;
                cursor: not-allowed;
            }
            
            .yonatan-send-btn { 
                background: var(--primary); 
                color: white; 
                border: none; 
                width: 40px; 
                height: 40px; 
                border-radius: 50%; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                cursor: pointer; 
                transition: all 0.2s;
                flex-shrink: 0;
            }
            
            .yonatan-send-btn:hover:not(:disabled) { 
                background: var(--secondary); 
                transform: scale(1.1);
            }
            
            .yonatan-send-btn:disabled {
                background: #9ca3af;
                cursor: not-allowed;
            }
            
            .yonatan-typing-indicator { 
                display: flex; 
                align-items: center; 
                gap: 4px; 
                padding: 8px 12px;
            }
            
            .yonatan-typing-indicator span { 
                height: 8px; 
                width: 8px; 
                border-radius: 50%; 
                background-color: #9ca3af; 
                animation: typing-bounce 1.4s infinite ease-in-out both; 
            }
            
            .yonatan-typing-indicator span:nth-child(1) { animation-delay: -0.32s; } 
            .yonatan-typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
            
            @keyframes typing-bounce { 
                0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; } 
                40% { transform: scale(1.2); opacity: 1; } 
            }
            
            .yonatan-loader { 
                border: 4px solid #f3f3f3; 
                border-top: 4px solid var(--primary); 
                border-radius: 50%; 
                width: 40px; 
                height: 40px; 
                animation: spin 1s linear infinite; 
                margin: auto; 
            }
            
            .questionnaire-view { 
                padding: 24px; 
                text-align: center; 
                height: 100%; 
                display: flex; 
                flex-direction: column; 
                justify-content: center;
                background: linear-gradient(to bottom, #f9fafb, #f3f4f6);
            }
            
            .questionnaire-progress {
                width: 100%;
                height: 4px;
                background: #e5e7eb;
                border-radius: 2px;
                margin-bottom: 20px;
                overflow: hidden;
            }
            
            .questionnaire-progress-bar {
                height: 100%;
                background: linear-gradient(90deg, var(--primary), var(--secondary));
                border-radius: 2px;
                transition: width 0.3s ease;
            }
            
            .question-container {
                background: white;
                border-radius: 16px;
                padding: 24px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            
            .question-text {
                font-size: 18px;
                font-weight: 600;
                color: #1f2937;
                margin-bottom: 20px;
                line-height: 1.4;
            }
            
            .question-btn { 
                background-color: #f8fafc; 
                border: 2px solid #e2e8f0; 
                color: #475569; 
                padding: 12px 16px; 
                border-radius: 12px; 
                cursor: pointer; 
                transition: all 0.2s; 
                margin: 6px; 
                font-weight: 500;
                min-width: 120px;
            }
            
            .question-btn:hover { 
                background-color: #eef2ff; 
                border-color: var(--primary); 
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(79, 70, 229, 0.2);
            }
            
            .question-btn.selected { 
                background: linear-gradient(135deg, var(--primary), var(--secondary)); 
                border-color: var(--primary); 
                color: white;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
            }
            
            .question-input {
                width: 100%;
                max-width: 300px;
                padding: 12px 16px;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                font-size: 16px;
                text-align: center;
                transition: all 0.2s;
                margin: 10px auto;
                display: block;
            }
            
            .question-input:focus {
                border-color: var(--primary);
                box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
                outline: none;
            }
            
            .question-scale {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 15px;
                margin: 20px 0;
            }
            
            .scale-input {
                width: 200px;
                height: 6px;
                border-radius: 3px;
                background: #e2e8f0;
                outline: none;
                -webkit-appearance: none;
            }
            
            .scale-input::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: var(--primary);
                cursor: pointer;
                box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            }
            
            .scale-input::-moz-range-thumb {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: var(--primary);
                cursor: pointer;
                border: none;
                box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            }
            
            .scale-labels {
                font-weight: 600;
                color: #64748b;
                font-size: 14px;
            }
            
            .suggestion-btn { 
                background: rgba(255,255,255,0.9); 
                border: 1px solid var(--primary); 
                color: var(--primary); 
                padding: 6px 12px; 
                border-radius: 16px; 
                cursor: pointer; 
                transition: all 0.2s; 
                margin: 3px; 
                font-family: inherit; 
                font-size: 13px;
                font-weight: 500;
                backdrop-filter: blur(4px);
            }
            
            .suggestion-btn:hover:not(:disabled) { 
                background: var(--primary); 
                color: white;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
            }
            
            .suggestion-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                background: #f1f5f9;
                color: #94a3b8;
                border-color: #cbd5e1;
            }
            
            .yonatan-card { 
                background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.95) 100%); 
                border-radius: 12px; 
                border: 1px solid rgba(79, 70, 229, 0.2); 
                margin: 12px 0; 
                overflow: hidden;
                backdrop-filter: blur(8px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            
            .yonatan-card-header { 
                background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); 
                color: white; 
                padding: 10px 15px; 
                font-weight: 600; 
                font-size: 14px;
            }
            
            .yonatan-card-body { 
                padding: 15px; 
                color: #374151;
                line-height: 1.6;
            }
            
            .error-message { 
                color: var(--danger); 
                padding: 12px; 
                margin: 8px 0; 
                background: linear-gradient(135deg, #fee2e2, #fecaca); 
                border-radius: 8px; 
                font-size: 14px;
                border: 1px solid #fca5a5;
            }
            
            .success-message {
                color: var(--success);
                padding: 12px;
                margin: 8px 0;
                background: linear-gradient(135deg, #d1fae5, #a7f3d0);
                border-radius: 8px;
                font-size: 14px;
                border: 1px solid #6ee7b7;
            }
            
            .retry-button { 
                background: var(--danger); 
                color: white; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 8px; 
                cursor: pointer; 
                margin-top: 8px; 
                font-size: 14px;
                font-weight: 500;
                transition: all 0.2s;
            }
            
            .retry-button:hover {
                background: #dc2626;
                transform: translateY(-1px);
            }
            
            .system-status-indicator { 
                position: fixed; 
                top: 20px; 
                right: 20px; 
                background: var(--success); 
                color: white; 
                padding: 6px 12px; 
                border-radius: 20px; 
                font-size: 12px; 
                font-weight: 600; 
                z-index: 10001; 
                opacity: 0.9;
                transition: all 0.3s ease;
            }
            
            .system-status-indicator.fallback { 
                background: var(--warning); 
            }
            
            .system-status-indicator.error { 
                background: var(--danger); 
            }
            
            .system-status-indicator.hidden {
                opacity: 0;
                transform: translateY(-10px);
            }
            
            .connection-status {
                position: absolute;
                top: 8px;
                left: 16px;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: var(--success);
                box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
            }
            
            .connection-status.warning {
                background: var(--warning);
                box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
            }
            
            .connection-status.error {
                background: var(--danger);
                box-shadow: 0 0 8px rgba(239, 68, 68, 0.6);
            }
            
            .validation-error {
                color: var(--danger);
                font-size: 12px;
                margin-top: 5px;
                text-align: center;
                font-weight: 500;
            }
            
            .next-button {
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                margin-top: 20px;
                min-width: 120px;
            }
            
            .next-button:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3);
            }
            
            .next-button:disabled {
                background: #9ca3af;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            
            /* Mobile optimizations */
            @media (max-width: 480px) {
                #yonatan-widget-container {
                    width: calc(100vw - 20px);
                    height: calc(100vh - 40px);
                    bottom: 10px;
                    right: 10px;
                }
                
                #yonatan-widget-button {
                    bottom: 15px;
                    right: 15px;
                    width: 56px;
                    height: 56px;
                }
                
                .questionnaire-view {
                    padding: 16px;
                }
                
                .question-container {
                    padding: 20px;
                }
                
                .question-text {
                    font-size: 16px;
                }
                
                .yonatan-input {
                    font-size: 16px; /* Prevent zoom on iOS */
                }
            }
            
            /* Accessibility improvements */
            @media (prefers-reduced-motion: reduce) {
                * {
                    animation-duration: 0.01ms !important;
                    animation-iteration-count: 1 !important;
                    transition-duration: 0.01ms !important;
                }
            }
            
            @media (prefers-contrast: high) {
                .yonatan-message.bot {
                    border: 2px solid #374151;
                }
                
                .yonatan-message.user {
                    border: 2px solid #312e81;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // Enhanced widget creation
    function createWidget() {
        elements.chatButton = document.createElement('button');
        elements.chatButton.id = 'yonatan-widget-button';
        elements.chatButton.setAttribute('aria-label', 'פתח את הצ\'אט עם יונתן הפסיכו-בוט');
        elements.chatButton.setAttribute('title', 'יונתן - הפסיכו-בוט שלך');
        elements.chatButton.innerHTML = `🧠`;
        document.body.appendChild(elements.chatButton);

        elements.widgetContainer = document.createElement('div');
        elements.widgetContainer.id = 'yonatan-widget-container';
        elements.widgetContainer.setAttribute('role', 'dialog');
        elements.widgetContainer.setAttribute('aria-label', 'צ\'אט עם יונתן הפסיכו-בוט');
        elements.widgetContainer.innerHTML = `
            <div class="yonatan-header">
                <div class="connection-status" id="connection-status"></div>
                <div class="flex items-center space-x-2 space-x-reverse">
                    <div class="yonatan-avatar text-base">י</div>
                    <div>
                        <h3 class="font-bold text-lg">יונתן</h3>
                        <div class="text-xs opacity-80" id="status-text">מוכן לעזור</div>
                    </div>
                </div>
                <button id="yonatan-close-btn" class="p-1 hover:bg-white/20 rounded transition-colors" aria-label="סגור צ'אט">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            <div id="yonatan-content-area" class="flex-grow overflow-hidden"></div>
        `;
        document.body.appendChild(elements.widgetContainer);
        
        elements.chatButton.addEventListener('click', toggleWidget);
        document.getElementById('yonatan-close-btn').addEventListener('click', () => toggleWidget(false));
        
        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && elements.widgetContainer.classList.contains('open')) {
                toggleWidget(false);
            }
        });
    }

    // Enhanced view rendering
    function renderView() {
        const contentArea = document.getElementById('yonatan-content-area');
        contentArea.innerHTML = ''; 

        switch (state.uiState) {
            case 'loading':
                renderLoading(contentArea);
                break;
            case 'questionnaire':
                renderQuestionnaire(contentArea);
                break;
            case 'chat':
                renderChat(contentArea);
                break;
            case 'error':
                renderError(contentArea);
                break;
        }
    }

    function renderLoading(container) {
        container.innerHTML = `
            <div class="flex items-center justify-center h-full">
                <div class="text-center">
                    <div class="yonatan-loader mb-4"></div>
                    <p class="text-gray-600">מתחבר ליונתן...</p>
                </div>
            </div>
        `;
    }

    function renderError(container) {
        container.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full p-4 text-center">
                <svg class="w-16 h-16 text-red-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <h3 class="text-xl font-bold mb-2 text-gray-800">אופס, משהו השתבש</h3>
                <p class="mb-4 text-gray-600 leading-relaxed">לא הצלחנו להתחבר למערכת. אנא בדוק את החיבור לאינטרנט ונסה שוב.</p>
                <button id="retry-button" class="retry-button">
                    נסה שוב
                </button>
            </div>
        `;
        
        document.getElementById('retry-button').addEventListener('click', async () => {
            state.uiState = 'loading';
            renderView();
            connectionRetries = 0;
            
            const healthStatus = await checkSystemHealth();
            if (healthStatus.available) {
                if (state.sessionId) {
                    state.uiState = 'questionnaire';
                } else {
                    state.uiState = 'questionnaire';
                }
            } else {
                state.uiState = 'error';
            }
            renderView();
        });
    }

    function renderQuestionnaire(container) {
        const step = state.questionnaireStep;
        const q = questionnaire[step];
        const progress = ((step + 1) / questionnaire.length) * 100;
        
        let inputHtml = '';
        let validationError = '';
        
        switch(q.type) {
            case 'text':
            case 'number':
                inputHtml = `
                    <input type="${q.type}" id="q-input" class="question-input" 
                           placeholder="${q.placeholder}" 
                           ${q.type === 'number' ? 'min="10" max="25"' : ''}
                           autocomplete="off">
                    <div id="validation-error" class="validation-error"></div>
                `;
                break;
            case 'radio':
            case 'choice':
                inputHtml = `
                    <div class="flex flex-wrap justify-center gap-3 mt-4">
                        ${q.options.map(o => `
                            <button class="question-btn" data-value="${o}" type="button">${o}</button>
                        `).join('')}
                    </div>
                `;
                break;
            case 'scale':
                inputHtml = `
                    <div class="question-scale">
                        <span class="scale-labels">1</span>
                        <input type="range" id="q-input" class="scale-input" min="${q.min}" max="${q.max}" value="5">
                        <span class="scale-labels">10</span>
                    </div>
                    <div class="text-center text-lg font-semibold text-primary" id="scale-value">5</div>
                `;
                break;
        }

        container.innerHTML = `
            <div class="questionnaire-view">
                <div class="questionnaire-progress">
                    <div class="questionnaire-progress-bar" style="width: ${progress}%"></div>
                </div>
                
                <div class="question-container">
                    <div class="question-text">${q.question}</div>
                    ${inputHtml}
                    
                    ${(q.type === 'text' || q.type === 'number' || q.type === 'scale') ? `
                        <button id="q-next-btn" class="next-button" disabled>
                            ${step === questionnaire.length - 1 ? 'סיום' : 'המשך'}
                        </button>
                    ` : ''}
                </div>
                
                <div class="text-center text-sm text-gray-500 mt-4">
                    שאלה ${step + 1} מתוך ${questionnaire.length}
                </div>
            </div>
        `;

        // Enhanced event handlers
        if (q.type === 'radio' || q.type === 'choice') {
            container.querySelectorAll('.question-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    // Remove selected class from all buttons
                    container.querySelectorAll('.question-btn').forEach(b => b.classList.remove('selected'));
                    // Add selected class to clicked button
                    btn.classList.add('selected');
                    
                    setTimeout(() => {
                        handleQuestionnaireAnswer(btn.dataset.value);
                    }, 300);
                });
            });
        } else {
            const nextBtn = document.getElementById('q-next-btn');
            const input = document.getElementById('q-input');
            const validationDiv = document.getElementById('validation-error');
            
            function validateInput() {
                const value = input.value.trim();
                if (!value) {
                    nextBtn.disabled = true;
                    return false;
                }
                
                if (q.validation && !q.validation(q.type === 'number' ? parseInt(value) : value)) {
                    validationDiv.textContent = getValidationMessage(q.id);
                    nextBtn.disabled = true;
                    return false;
                }
                
                validationDiv.textContent = '';
                nextBtn.disabled = false;
                return true;
            }
            
            input.addEventListener('input', validateInput);
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !nextBtn.disabled) {
                    handleQuestionnaireAnswer(input.value);
                }
            });
            
            nextBtn.addEventListener('click', () => {
                if (validateInput()) {
                    handleQuestionnaireAnswer(input.value);
                }
            });
            
            // Scale-specific handling
            if (q.type === 'scale') {
                const scaleValue = document.getElementById('scale-value');
                input.addEventListener('input', () => {
                    scaleValue.textContent = input.value;
                    nextBtn.disabled = false;
                });
                nextBtn.disabled = false; // Scale always has a value
            }
            
            // Auto-focus input
            setTimeout(() => input.focus(), 100);
        }
    }

    function getValidationMessage(fieldId) {
        const messages = {
            'parent_name': 'אנא הכנס שם תקין (לפחות 2 תווים)',
            'child_name': 'אנא הכנס שם תקין (לפחות 2 תווים)',
            'child_age': 'אנא הכנס גיל בין 10 ל-25',
            'challenge_context': 'אנא תאר בקצרה מתי הבעיה מופיעה',
            'past_solutions': 'אנא ספר על ניסיונות קודמים'
        };
        return messages[fieldId] || 'אנא מלא שדה זה';
    }
    
    function handleQuestionnaireAnswer(answer) {
        if (!answer && answer !== 0) return;
        
        // Save answer
        state.questionnaireData[questionnaire[state.questionnaireStep].id] = answer;
        
        // Show transition effect
        const container = document.getElementById('yonatan-content-area');
        container.style.opacity = '0.7';
        
        setTimeout(() => {
            if (state.questionnaireStep < questionnaire.length - 1) {
                state.questionnaireStep++;
                renderView();
            } else {
                finishQuestionnaire();
            }
            container.style.opacity = '1';
        }, 200);
    }
    
    async function finishQuestionnaire() {
        state.uiState = 'loading';
        updateStatusText('שומר נתונים...');
        renderView();
        
        try {
            const response = await fetchWithCSRF(`${API_URL}/api/questionnaire`, {
                method: 'POST',
                body: JSON.stringify({ session_id: state.sessionId, ...state.questionnaireData })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `שגיאת שרת: ${response.status}`);
            }

            state.uiState = 'chat';
            updateStatusText('מוכן לשיחה');
            renderView();
            
            // Start conversation
            setTimeout(() => {
                sendMessage("START_CONVERSATION");
            }, 500);
            
        } catch (error) {
            console.error("שגיאה בשמירת שאלון:", error);
            showErrorMessage("אירעה שגיאה בשמירת הנתונים. ננסה להמשיך בכל זאת.");
            
            state.uiState = 'chat';
            renderView();
            addMessageToChat('bot', 'שלום! אני כאן לעזור לך גם בלי הנתונים המלאים. איך אני יכול לעזור?');
        }
    }

    function renderChat(container) {
        container.innerHTML = `
            <div class="yonatan-chat-window" id="chat-window">
                <div id="yonatan-messages" class="flex flex-col"></div>
            </div>
            <div class="yonatan-footer">
                <div class="yonatan-input-area">
                    <input id="yonatan-input" type="text" class="yonatan-input" 
                           placeholder="כתוב/י הודעה..." maxlength="5000"
                           autocomplete="off">
                    <button id="yonatan-send-btn" class="yonatan-send-btn" aria-label="שלח הודעה">
                        <svg class="w-6 h-6 transform -rotate-90" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.428A1 1 0 009.17 15.57l-1.722-7.224a1 1 0 01.224-.97l4.573-5.336z"></path>
                        </svg>
                    </button>
                </div>
                <div class="text-xs text-gray-500 text-center mt-2" id="input-counter"></div>
            </div>
        `;
        
        elements.messagesContainer = document.getElementById('yonatan-messages');
        elements.chatInput = document.getElementById('yonatan-input');
        
        const sendBtn = document.getElementById('yonatan-send-btn');
        const inputCounter = document.getElementById('input-counter');
        
        // Enhanced input handling
        elements.chatInput.addEventListener('input', () => {
            const length = elements.chatInput.value.length;
            inputCounter.textContent = length > 0 ? `${length}/5000` : '';
            
            sendBtn.disabled = state.isTyping || length === 0 || length > 5000;
            
            if (length > 4500) {
                inputCounter.style.color = '#ef4444';
            } else {
                inputCounter.style.color = '#9ca3af';
            }
        });
        
        sendBtn.addEventListener('click', () => sendMessage());
        elements.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Auto-resize textarea behavior
        elements.chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // Restore conversation history
        state.conversationHistory.forEach(msg => addMessageToChat(msg.sender, msg.text, false));
        
        // Focus input
        setTimeout(() => elements.chatInput.focus(), 100);
    }

    // Enhanced message parsing and rendering
    function parseAndRenderContent(text) {
        // Enhanced CARD regex
        const cardRegex = /CARD\[([^|]+)\|([^\]]+)\]/g;
        let processedText = text.replace(cardRegex, (match, title, body) => {
            return `
                <div class="yonatan-card">
                    <div class="yonatan-card-header">${title}</div>
                    <div class="yonatan-card-body">${body.replace(/\n/g, '<br>')}</div>
                </div>
            `;
        });
        
        // Enhanced formatting
        processedText = processedText
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background: #f1f5f9; padding: 2px 4px; border-radius: 4px; font-family: monospace;">$1</code>')
            .replace(/\[(.*?)\]/g, `<button class="suggestion-btn" data-text="$1">$1</button>`)
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');
        
        return processedText;
    }

    function detectFallbackResponse(text) {
        const fallbackIndicators = [
            "המערכת שלי עמוסה כרגע",
            "נסה שוב מאוחר יותר", 
            "CARD[",
            "🤖",
            "💡 מצב חכם",
            "מערכת Fallback",
            "תגובה מהמערכת החכמה"
        ];
        
        return fallbackIndicators.some(indicator => text.includes(indicator));
    }

    function addMessageToChat(sender, text, animate = true) {
        if (!elements.messagesContainer) return;
        
        const wrapper = document.createElement('div');
        wrapper.className = `yonatan-message-wrapper ${sender}`;
        if (!animate) wrapper.style.animation = 'none';

        const contentHTML = parseAndRenderContent(text);
        
        // Enhanced fallback detection
        const isFallback = sender === 'bot' && detectFallbackResponse(text);
        const timestamp = new Date().toLocaleTimeString('he-IL', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        wrapper.innerHTML = `
            ${sender === 'bot' ? '<div class="yonatan-avatar">י</div>' : ''}
            <div class="yonatan-message ${sender} ${isFallback ? 'fallback-mode' : ''}">
                ${isFallback ? '<div class="fallback-indicator">💡 מצב חכם</div>' : ''}
                <div class="message-content">${contentHTML}</div>
                <div class="text-xs opacity-60 mt-2">${timestamp}</div>
            </div>
        `;
        
        elements.messagesContainer.appendChild(wrapper);
        
        // Enhanced suggestion button handling
        wrapper.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.disabled) return;
                
                sendMessage(btn.dataset.text);
                
                // Disable all suggestion buttons in this message
                wrapper.querySelectorAll('.suggestion-btn').forEach(b => { 
                    b.disabled = true;
                    b.style.cssText = 'cursor: not-allowed; opacity: 0.6;'; 
                });
            });
        });
        
        // Enhanced auto-scroll with smooth behavior
        const chatWindow = elements.messagesContainer.parentElement;
        const shouldScroll = chatWindow.scrollTop + chatWindow.clientHeight >= chatWindow.scrollHeight - 100;
        
        if (shouldScroll) {
            setTimeout(() => {
                chatWindow.scrollTo({
                    top: chatWindow.scrollHeight,
                    behavior: 'smooth'
                });
            }, 100);
        }
        
        return wrapper;
    }

    // Enhanced system health checking
    async function checkSystemHealth() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const response = await fetch(`${API_URL}/api/health`, {
                signal: controller.signal,
                cache: 'no-cache'
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`Health check failed: ${response.status}`);
            }
            
            const health = await response.json();
            
            const systemAvailable = health.database_connected && 
                                   (health.ai_model_working || health.fallback_system_available);
            
            const fallbackMode = health.status === "fallback_mode" || 
                               health.quota_exceeded || 
                               !health.ai_model_working;
            
            console.log("בדיקת בריאות המערכת:", health);
            
            state.systemHealth = {
                available: systemAvailable,
                fallbackMode: fallbackMode,
                details: health,
                timestamp: Date.now()
            };
            
            return state.systemHealth;
            
        } catch (error) {
            console.error("שגיאה בבדיקת בריאות המערכת:", error);
            
            state.systemHealth = {
                available: false,
                fallbackMode: false,
                error: error.message,
                timestamp: Date.now()
            };
            
            return state.systemHealth;
        }
    }

    function updateSystemStatusIndicator(systemHealth) {
        let indicator = document.getElementById('yonatan-system-status');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'yonatan-system-status';
            indicator.className = 'system-status-indicator';
            document.body.appendChild(indicator);
        }
        
        indicator.classList.remove('hidden');
        
        if (systemHealth.available) {
            if (systemHealth.fallbackMode) {
                indicator.className = 'system-status-indicator fallback';
                indicator.textContent = '🤖 מצב חכם';
                indicator.title = 'הבוט פועל במצב fallback - תשובות מוכנות מראש';
            } else {
                indicator.className = 'system-status-indicator';
                indicator.textContent = '✅ פעיל';
                indicator.title = 'הבוט פועל במלוא התפקוד';
            }
        } else {
            indicator.className = 'system-status-indicator error';
            indicator.textContent = '❌ שגיאה';
            indicator.title = 'הבוט לא זמין כרגע';
        }
        
        // Auto-hide after 8 seconds
        setTimeout(() => {
            indicator.classList.add('hidden');
            setTimeout(() => {
                if (indicator && indicator.parentNode) {
                    indicator.remove();
                }
            }, 300);
        }, 8000);
    }

    function updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        const statusText = document.getElementById('status-text');
        
        if (statusElement) {
            statusElement.className = `connection-status ${status}`;
        }
        
        if (statusText) {
            const statusMessages = {
                'success': 'מוכן לעזור',
                'warning': 'מצב חכם',
                'error': 'לא זמין'
            };
            statusText.textContent = statusMessages[status] || 'מתחבר...';
        }
    }

    function updateStatusText(text) {
        const statusText = document.getElementById('status-text');
        if (statusText) {
            statusText.textContent = text;
        }
    }

    function showErrorMessage(message) {
        if (elements.messagesContainer) {
            addMessageToChat('bot', `<div class="error-message">${message}</div>`);
        }
    }

    function showSuccessMessage(message) {
        if (elements.messagesContainer) {
            addMessageToChat('bot', `<div class="success-message">${message}</div>`);
        }
    }
    
    // Enhanced message sending with better error handling
    async function sendMessage(messageTextOverride) {
        const messageText = messageTextOverride || elements.chatInput.value.trim();
        if (!messageText || state.isTyping) return;

        // Update UI state
        state.isTyping = true;
        if (elements.chatInput) {
            elements.chatInput.disabled = true;
            elements.chatInput.value = '';
        }
        
        const sendBtn = document.getElementById('yonatan-send-btn');
        if (sendBtn) sendBtn.disabled = true;

        // Add user message to chat (except for START_CONVERSATION)
        if (messageText !== "START_CONVERSATION") {
            addMessageToChat('user', messageText);
            state.conversationHistory.push({ sender: 'user', text: messageText, timestamp: Date.now() });
            saveConversationToStorage();
        }
        
        // Show typing indicator
        toggleTyping(true);
        updateStatusText('כותב תגובה...');
        
        let retryCount = 0;
        const maxRetries = 3;
        
        async function attemptSendMessage() {
            try {
                // Enhanced request with timeout and retry logic
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 45000); // 45 seconds timeout
                
                const response = await fetchWithCSRF(`${API_URL}/api/chat`, {
                    method: 'POST',
                    body: JSON.stringify({ 
                        session_id: state.sessionId, 
                        message: messageText,
                        timestamp: Date.now()
                    }),
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);

                if (!response.ok) {
                    // Handle specific error responses
                    if (response.status === 400) {
                        const errorData = await response.json().catch(() => ({}));
                        if (errorData.error && errorData.error.includes('CSRF')) {
                            console.log('🔄 CSRF token expired, refreshing...');
                            csrfToken = null;
                            await getCSRFToken();
                            
                            if (retryCount < maxRetries) {
                                retryCount++;
                                return attemptSendMessage();
                            }
                        }
                        throw new Error(errorData.error || "בקשה לא תקינה");
                    } else if (response.status === 429) {
                        throw new Error("יותר מדי בקשות. אנא המתן ונסה שוב.");
                    } else if (response.status === 503) {
                        throw new Error("השירות לא זמין כרגע. ננסה שוב...");
                    }
                    
                    throw new Error(`שגיאת שרת: ${response.status}`);
                }
                
                if (!response.body) {
                    throw new Error('התגובה לא מכילה תוכן זורם.');
                }
                
                toggleTyping(false);
                updateStatusText('מקבל תגובה...');
                
                // Enhanced streaming response handling
                const botMessageWrapper = addMessageToChat('bot', '');
                const botMessageContent = botMessageWrapper.querySelector('.message-content');
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullResponseText = '';
                let receivedAnyContent = false;
                let lastUpdate = Date.now();

                try {
                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;
                        
                        const chunk = decoder.decode(value, { stream: true });
                        if (chunk) {
                            receivedAnyContent = true;
                            fullResponseText += chunk;
                            lastUpdate = Date.now();
                            
                            // Enhanced content rendering
                            botMessageContent.innerHTML = parseAndRenderContent(fullResponseText);
                            
                            // Enhanced fallback detection and styling
                            const isFallback = detectFallbackResponse(fullResponseText);
                            const messageDiv = botMessageWrapper.querySelector('.yonatan-message');
                            
                            if (isFallback && !botMessageWrapper.querySelector('.fallback-indicator')) {
                                messageDiv.classList.add('fallback-mode');
                                botMessageContent.insertAdjacentHTML('beforebegin', 
                                    '<div class="fallback-indicator">💡 מצב חכם</div>'
                                );
                            }
                            
                            // Auto-scroll during streaming
                            const chatWindow = elements.messagesContainer.parentElement;
                            if (chatWindow.scrollTop + chatWindow.clientHeight >= chatWindow.scrollHeight - 150) {
                                chatWindow.scrollTop = chatWindow.scrollHeight;
                            }
                        }
                    }
                    
                    // Validate received content
                    if (!receivedAnyContent || !fullResponseText.trim()) {
                        throw new Error('לא התקבל תוכן מהשרת');
                    }
                    
                    // Enhanced suggestion button handling after streaming
                    setTimeout(() => {
                        botMessageWrapper.querySelectorAll('.suggestion-btn').forEach(btn => {
                            btn.addEventListener('click', () => {
                                if (btn.disabled) return;
                                
                                sendMessage(btn.dataset.text);
                                botMessageWrapper.querySelectorAll('.suggestion-btn').forEach(b => { 
                                    b.disabled = true; 
                                    b.style.cssText = 'cursor: not-allowed; opacity: 0.6;'; 
                                });
                            });
                        });
                    }, 500);

                    // Save to conversation history
                    state.conversationHistory.push({ 
                        sender: 'bot', 
                        text: fullResponseText, 
                        timestamp: Date.now() 
                    });
                    saveConversationToStorage();
                    
                    updateStatusText('מוכן לשיחה');
                    connectionRetries = 0; // Reset retry counter on success
                    
                } catch (streamError) {
                    console.error("שגיאת סטרימינג:", streamError);
                    botMessageContent.innerHTML = `
                        <div class="error-message">
                            אירעה שגיאה בקבלת התשובה. 
                            <button class="retry-button" id="retry-stream-btn">נסה שוב</button>
                        </div>
                    `;
                    
                    document.getElementById('retry-stream-btn').addEventListener('click', () => {
                        botMessageWrapper.remove();
                        sendMessage(messageText);
                    });
                    
                    throw streamError;
                }
                
            } catch (error) {
                console.error("שגיאת API:", error);
                
                // Enhanced retry logic with exponential backoff
                if (retryCount < maxRetries && !error.message.includes('aborted')) {
                    retryCount++;
                    console.log(`ניסיון ${retryCount} מתוך ${maxRetries}...`);
                    
                    updateStatusText(`ניסיון ${retryCount}...`);
                    
                    // Exponential backoff
                    const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 5000);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    
                    return attemptSendMessage();
                }
                
                // Final error handling
                toggleTyping(false);
                updateStatusText('שגיאה בתקשורת');
                
                let errorMessage = 'אירעה שגיאה בתקשורת עם השרת.';
                
                if (error.message.includes('aborted') || error.message.includes('timeout')) {
                    errorMessage = 'התגובה ארכה יותר מדי. אנא נסה שוב עם הודעה קצרה יותר.';
                } else if (error.message.includes('quota') || error.message.includes('429')) {
                    errorMessage = 'המערכת עמוסה כרגע. אנא נסה שוב בעוד כמה דקות.';
                } else if (connectionRetries < 2) {
                    errorMessage = 'בעיית חיבור זמנית. אנא נסה שוב.';
                } else {
                    errorMessage = 'נתקלנו בבעיה טכנית. אנא רענן את הדף או נסה מאוחר יותר.';
                }
                
                addMessageToChat('bot', `
                    <div class="error-message">
                        ${errorMessage}
                        <button class="retry-button" id="retry-message-btn">נסה שוב</button>
                    </div>
                `);
                
                document.getElementById('retry-message-btn').addEventListener('click', () => {
                    sendMessage(messageText);
                });
                
                connectionRetries++;
            }
        }
        
        try {
            await attemptSendMessage();
        } finally {
            // Always reset UI state
            state.isTyping = false;
            if (elements.chatInput) {
                elements.chatInput.disabled = false;
                elements.chatInput.focus();
            }
            if (sendBtn) sendBtn.disabled = false;
            
            const inputCounter = document.getElementById('input-counter');
            if (inputCounter) inputCounter.textContent = '';
        }
    }

    function toggleTyping(isTyping) {
        let typingIndicator = elements.messagesContainer?.querySelector('.typing-indicator-wrapper');
        
        if (isTyping && !typingIndicator) {
            const wrapper = document.createElement('div');
            wrapper.className = 'yonatan-message-wrapper bot typing-indicator-wrapper';
            wrapper.innerHTML = `
                <div class="yonatan-avatar">י</div>
                <div class="yonatan-message bot">
                    <div class="yonatan-typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            `;
            elements.messagesContainer.appendChild(wrapper);
            
            const chatWindow = elements.messagesContainer.parentElement;
            chatWindow.scrollTop = chatWindow.scrollHeight;
        } else if (!isTyping && typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Enhanced session management
    function saveConversationToStorage() {
        try {
            // Keep only last 50 messages to prevent storage overflow
            const limitedHistory = state.conversationHistory.slice(-50);
            localStorage.setItem('yonatan_conversation', JSON.stringify(limitedHistory));
            localStorage.setItem('yonatan_last_activity', Date.now().toString());
        } catch (error) {
            console.warn('Could not save conversation to storage:', error);
        }
    }

    function clearStorageData() {
        try {
            localStorage.removeItem('yonatan_session_id');
            localStorage.removeItem('yonatan_conversation');
            localStorage.removeItem('yonatan_last_activity');
        } catch (error) {
            console.warn('Could not clear storage:', error);
        }
    }

    // Enhanced widget toggle with better state management
    async function toggleWidget(forceOpen) {
        const isOpen = elements.widgetContainer.classList.contains('open');
        const shouldOpen = forceOpen !== undefined ? forceOpen : !isOpen;

        if (shouldOpen) {
            elements.chatButton.classList.add('loading');
            
            // Enhanced system health check
            const systemHealth = await checkSystemHealth();
            updateSystemStatusIndicator(systemHealth);
            
            // Update button and connection status
            elements.chatButton.classList.remove('loading', 'api-error', 'fallback-mode');
            if (!systemHealth.available) {
                elements.chatButton.classList.add('api-error');
                updateConnectionStatus('error');
            } else if (systemHealth.fallbackMode) {
                elements.chatButton.classList.add('fallback-mode');
                updateConnectionStatus('warning');
            } else {
                updateConnectionStatus('success');
            }
            
            elements.widgetContainer.classList.add('open');
            elements.chatButton.style.opacity = '0';
            
            // Check session validity
            const lastActivity = localStorage.getItem('yonatan_last_activity');
            const sessionTimeout = 30 * 60 * 1000; // 30 minutes
            
            if (lastActivity && (Date.now() - parseInt(lastActivity)) > sessionTimeout) {
                // Session expired - clear and restart
                clearStorageData();
                state.sessionId = null;
                state.conversationHistory = [];
            }
            
            if (!state.sessionId) {
                state.uiState = 'loading';
                renderView();
                
                if (!systemHealth.available) {
                    state.uiState = 'error';
                    renderView();
                    return;
                }
                
                try {
                    await getCSRFToken();
                    
                    const response = await fetchWithCSRF(`${API_URL}/api/init`, { 
                        method: 'POST',
                        body: JSON.stringify({ timestamp: Date.now() })
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({}));
                        throw new Error(errorData.error || `שגיאת שרת: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    if (data.error) throw new Error(data.error);
                    
                    state.sessionId = data.session_id;
                    localStorage.setItem('yonatan_session_id', state.sessionId);
                    
                    if (data.csrf_token) {
                        csrfToken = data.csrf_token;
                    }
                    
                    state.uiState = 'questionnaire';
                    renderView();
                    
                } catch (error) {
                    console.error("שגיאת אתחול:", error);
                    state.uiState = 'error';
                    renderView();
                }
            } else {
                if (!systemHealth.available) {
                    state.uiState = 'error';
                    renderView();
                    return;
                }
                
                if (state.uiState !== 'chat') {
                    state.uiState = 'chat';
                    renderView();
                    
                    if (state.conversationHistory.length === 0) {
                        const welcomeMessage = systemHealth.fallbackMode ? 
                            'שלום! אני פועל במצב חכם היום - עדיין אוכל לעזור לך בהרבה דרכים! איך המצב?' :
                            'שלום שוב! איך אני יכול לעזור לך היום?';
                        
                        setTimeout(() => {
                            addMessageToChat('bot', welcomeMessage);
                        }, 500);
                    }
                }
            }
        } else {
            elements.widgetContainer.classList.remove('open');
            elements.chatButton.style.opacity = '1';
        }
    }

    // Enhanced initialization
    async function initialize() {
        injectStyles();
        createWidget();
        
        // Initial CSRF token
        await getCSRFToken();
        
        // Enhanced health check with UI updates
        const systemHealth = await checkSystemHealth();
        updateSystemStatusIndicator(systemHealth);
        
        // Update button state based on system health
        if (!systemHealth.available) {
            elements.chatButton.classList.add('api-error');
            elements.chatButton.setAttribute('title', 'יש בעיה בחיבור לשרת - לחץ לפרטים');
        } else if (systemHealth.fallbackMode) {
            elements.chatButton.classList.add('fallback-mode');
            elements.chatButton.setAttribute('title', 'יונתן פועל במצב חכם - לחץ להתחלה');
        } else {
            elements.chatButton.setAttribute('title', 'יונתן מוכן לעזור - לחץ להתחלה');
        }
        
        // Periodic health checks
        setInterval(async () => {
            if (elements.widgetContainer.classList.contains('open')) {
                const health = await checkSystemHealth();
                updateConnectionStatus(health.available ? 
                    (health.fallbackMode ? 'warning' : 'success') : 'error'
                );
            }
        }, 60000); // Every minute
        
        // Enhanced global API
        window.yonatanWidget = { 
            open: () => toggleWidget(true),
            close: () => toggleWidget(false),
            checkHealth: checkSystemHealth,
            getSystemStatus: () => state.systemHealth,
            clearData: () => {
                clearStorageData();
                state.sessionId = null;
                state.conversationHistory = [];
                state.questionnaireData = {};
                state.questionnaireStep = 0;
            },
            resetSession: async () => {
                try {
                    const response = await fetchWithCSRF(`${API_URL}/api/reset_session`, {
                        method: 'POST',
                        body: JSON.stringify({ session_id: state.sessionId })
                    });
                    
                    if (response.ok) {
                        window.yonatanWidget.clearData();
                        csrfToken = null;
                        return true;
                    }
                    return false;
                } catch (error) {
                    console.error("שגיאה באיפוס הסשן:", error);
                    return false;
                }
            },
            // Development helpers
            getState: () => ({ ...state }),
            getConversationHistory: () => [...state.conversationHistory]
        };
        
        console.log('🤖 יונתן הפסיכו-בוט מוכן לפעולה!');
    }

    // Enhanced initialization with proper error handling
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})();