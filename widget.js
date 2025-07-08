// Yonatan Psycho-Bot Widget v8.0
(function() {
    if (window.yonatanWidgetLoaded) return;
    window.yonatanWidgetLoaded = true;

    const API_URL = window.location.origin;

    // --- State Management ---
    let state = {
        uiState: 'closed', // closed, loading, questionnaire, chat
        isFullScreen: false,
        sessionId: localStorage.getItem('yonatan_session_id'),
        userDetails: null,
        childDetails: null,
        conversationHistory: [],
        isTyping: false,
        questionnaireStep: 0,
        questionnaireData: {},
    };

    // --- DOM Elements ---
    const elements = {
        chatButton: null,
        widgetContainer: null,
        chatWindow: null,
        messagesContainer: null,
        chatInput: null,
        sendButton: null,
    };

    // --- Questionnaire Definition ---
    const questionnaire = [
        { id: 'parent_name', question: "נעים מאוד, אני יונתן. איך קוראים לך?", type: 'text', placeholder: "השם שלך" },
        { id: 'parent_gender', question: "באיזה מגדר לפנות אליך?", type: 'radio', options: ['זכר', 'נקבה', 'אחר'] },
        { id: 'child_name', question: "ומה שם המתבגר/ת שעליו/ה נרצה לדבר?", type: 'text', placeholder: "שם הילד/ה" },
        { id: 'child_age', question: "בן/בת כמה הוא/היא?", type: 'number', placeholder: "לדוגמה: 15" },
        { id: 'child_gender', question: "ומה המגדר שלו/ה?", type: 'radio', options: ['זכר', 'נקבה', 'אחר'] },
        { id: 'main_challenge', question: "מהו האתגר המרכזי שבו את/ה רוצה להתמקד היום?", type: 'choice', options: ['תקשורת וריבים', 'קשיים בלימודים', 'ויסות רגשי והתפרצויות', 'זמן מסך והתמכרויות', 'קשיים חברתיים', 'התנהגות סיכונית', 'אחר'] },
        { id: 'challenge_context', question: "מתי הבעיה הזו מופיעה בדרך כלל?", type: 'text', placeholder: "למשל, בערבים, סביב הכנת שיעורים..." },
        { id: 'past_solutions', question: "איך ניסית להתמודד עם זה עד עכשיו?", type: 'text', placeholder: "למשל, ניסיתי לדבר, לקחת את הטלפון..." },
        { id: 'distress_level', question: "בסקאלה של 1 עד 10, כמה המצב הזה גורם לך למצוקה?", type: 'scale', min: 1, max: 10 },
        { id: 'goal', question: "ומה המטרה העיקרית שלך מהשיחה שלנו?", type: 'choice', options: ['לקבל כלים פרקטיים', 'להבין טוב יותר את הילד/ה', 'להרגיש יותר ביטחון בהורות', 'לפרוק ולשתף'] },
    ];

    // --- Core Functions ---
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            :root { --primary: #4f46e5; --secondary: #7c3aed; }
            #yonatan-widget-button { position: fixed; bottom: 20px; right: 20px; background: var(--primary); color: white; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.2); cursor: pointer; transition: all 0.3s ease; z-index: 9998; border: none; }
            #yonatan-widget-button:hover { transform: scale(1.1); }
            #yonatan-widget-container { position: fixed; bottom: 20px; right: 20px; width: 400px; height: 600px; max-height: calc(100vh - 40px); background: white; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); display: flex; flex-direction: column; overflow: hidden; transform: scale(0.5) translateY(100px); opacity: 0; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); pointer-events: none; z-index: 9999; }
            #yonatan-widget-container.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: auto; }
            #yonatan-widget-container.fullscreen { bottom: 0; right: 0; width: 100%; height: 100%; max-height: 100vh; border-radius: 0; }
            .yonatan-header { background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); color: white; padding: 16px; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
            .yonatan-chat-window { flex-grow: 1; overflow-y: auto; padding: 16px; background-color: #f9fafb; }
            .yonatan-message { max-width: 80%; padding: 10px 15px; border-radius: 18px; margin-bottom: 10px; line-height: 1.5; animation: fadeIn 0.3s ease; }
            .yonatan-message.user { background-color: #eef2ff; color: #312e81; align-self: flex-end; border-bottom-right-radius: 4px; margin-right: auto; }
            .yonatan-message.bot { background-color: #ffffff; color: #374151; align-self: flex-start; border: 1px solid #e5e7eb; border-bottom-left-radius: 4px; margin-left: auto; }
            .yonatan-footer { padding: 16px; border-top: 1px solid #e5e7eb; background: white; flex-shrink: 0; }
            .yonatan-input-area { display: flex; align-items: center; }
            .yonatan-input { flex-grow: 1; border: 1px solid #d1d5db; border-radius: 20px; padding: 10px 16px; font-size: 16px; outline: none; transition: border-color 0.2s; }
            .yonatan-input:focus { border-color: var(--primary); }
            .yonatan-send-btn { background: var(--primary); color: white; border: none; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; cursor: pointer; transition: background-color 0.2s; }
            .yonatan-send-btn:hover { background-color: var(--secondary); }
            .yonatan-typing-indicator { display: flex; align-items: center; padding: 10px 0; }
            .yonatan-typing-indicator span { height: 8px; width: 8px; border-radius: 50%; background-color: #9ca3af; margin: 0 2px; animation: typing-bounce 1.4s infinite ease-in-out both; }
            .yonatan-typing-indicator span:nth-child(1) { animation-delay: -0.32s; } .yonatan-typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
            .yonatan-loader { border: 4px solid #f3f3f3; border-top: 4px solid var(--primary); border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: auto; }
            .questionnaire-view { padding: 24px; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: center; }
            .question-btn { background-color: #f3f4f6; border: 1px solid #e5e7eb; color: #374151; padding: 10px 15px; border-radius: 12px; cursor: pointer; transition: all 0.2s; margin: 5px; }
            .question-btn:hover, .question-btn.selected { background-color: #eef2ff; border-color: var(--primary); color: var(--primary); }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
            @keyframes spin { to { transform: rotate(360deg); } }
            @keyframes typing-bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }
        `;
        document.head.appendChild(style);
    }

    function createWidget() {
        // Chat Button
        elements.chatButton = document.createElement('button');
        elements.chatButton.id = 'yonatan-widget-button';
        elements.chatButton.setAttribute('aria-label', 'פתח את הצ\'אט עם יונתן');
        elements.chatButton.innerHTML = `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg>`;
        document.body.appendChild(elements.chatButton);

        // Widget Container
        elements.widgetContainer = document.createElement('div');
        elements.widgetContainer.id = 'yonatan-widget-container';
        elements.widgetContainer.innerHTML = `
            <div class="yonatan-header">
                <div class="flex items-center">
                    <svg class="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.657 7.343A8 8 0 0117.657 18.657z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.879 16.121A3 3 0 1014.12 11.88l-4.242 4.242z"></path></svg>
                    <h3 class="font-bold text-lg">יונתן</h3>
                </div>
                <div>
                    <button id="yonatan-fullscreen-btn" class="p-1" aria-label="מסך מלא">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1v4m0 0h-4m4 0l-5-5M4 16v4m0 0h4m-4 0l5-5m11 1v-4m0 0h-4m4 0l-5 5"></path></svg>
                    </button>
                    <button id="yonatan-close-btn" class="p-1 mr-2" aria-label="סגור צ'אט">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>
            </div>
            <div id="yonatan-content-area" class="flex-grow overflow-hidden"></div>
        `;
        document.body.appendChild(elements.widgetContainer);
        
        // Add event listeners
        elements.chatButton.addEventListener('click', toggleWidget);
        document.getElementById('yonatan-close-btn').addEventListener('click', () => toggleWidget(false));
        document.getElementById('yonatan-fullscreen-btn').addEventListener('click', toggleFullScreen);
    }

    function renderView() {
        const contentArea = document.getElementById('yonatan-content-area');
        contentArea.innerHTML = ''; // Clear previous view

        switch (state.uiState) {
            case 'loading':
                contentArea.innerHTML = `<div class="flex items-center justify-center h-full"><div class="yonatan-loader"></div></div>`;
                break;
            case 'questionnaire':
                renderQuestionnaire(contentArea);
                break;
            case 'chat':
                renderChat(contentArea);
                break;
        }
    }

    function renderQuestionnaire(container) {
        const step = state.questionnaireStep;
        const q = questionnaire[step];
        
        let inputHtml = '';
        switch(q.type) {
            case 'text':
            case 'number':
                inputHtml = `<input type="${q.type}" id="q-input" class="yonatan-input w-full max-w-sm mx-auto mt-4" placeholder="${q.placeholder}">`;
                break;
            case 'radio':
                inputHtml = `<div class="flex justify-center gap-4 mt-4">${q.options.map(o => `<button class="question-btn" data-value="${o}">${o}</button>`).join('')}</div>`;
                break;
            case 'choice':
                inputHtml = `<div class="flex flex-wrap justify-center gap-3 mt-4">${q.options.map(o => `<button class="question-btn" data-value="${o}">${o}</button>`).join('')}</div>`;
                break;
            case 'scale':
                inputHtml = `<div class="flex justify-center items-center gap-2 mt-4">1 <input type="range" id="q-input" min="${q.min}" max="${q.max}" class="w-full max-w-xs"> 10</div>`;
                break;
        }

        container.innerHTML = `
            <div class="questionnaire-view">
                <p class="text-xl font-semibold text-gray-700">${q.question}</p>
                <div class="mt-6">${inputHtml}</div>
                ${(q.type === 'text' || q.type === 'number' || q.type === 'scale') ? '<button id="q-next-btn" class="yonatan-send-btn mx-auto mt-6">&rarr;</button>' : ''}
            </div>
        `;

        // Add event listeners for the current question
        if (q.type === 'radio' || q.type === 'choice') {
            container.querySelectorAll('.question-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    handleQuestionnaireAnswer(btn.dataset.value);
                });
            });
        } else {
            const nextBtn = document.getElementById('q-next-btn');
            const input = document.getElementById('q-input');
            nextBtn.addEventListener('click', () => handleQuestionnaireAnswer(input.value));
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') handleQuestionnaireAnswer(input.value);
            });
        }
    }
    
    function handleQuestionnaireAnswer(answer) {
        if (!answer) return;
        const q = questionnaire[state.questionnaireStep];
        state.questionnaireData[q.id] = answer;

        if (state.questionnaireStep < questionnaire.length - 1) {
            state.questionnaireStep++;
            renderView();
        } else {
            finishQuestionnaire();
        }
    }
    
    async function finishQuestionnaire() {
        state.uiState = 'loading';
        renderView();

        try {
            const response = await fetch(`${API_URL}/api/questionnaire`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.sessionId, ...state.questionnaireData })
            });
            if (!response.ok) throw new Error('Failed to submit questionnaire');
            
            state.uiState = 'chat';
            renderView();
            addMessageToChat('bot', `תודה שמילאת את השאלון, ${state.questionnaireData.parent_name}. אני מבין שאת/ה מתמודד/ת עם ${state.questionnaireData.main_challenge}. אני כאן כדי לעזור. איך תרצה/י שנתחיל?`);
        } catch (error) {
            console.error(error);
            addMessageToChat('bot', 'אופס, הייתה בעיה בשמירת הנתונים. בוא/י ננסה לדבר בכל זאת.');
            state.uiState = 'chat';
            renderView();
        }
    }

    function renderChat(container) {
        container.innerHTML = `
            <div class="yonatan-chat-window">
                <div id="yonatan-messages" class="flex flex-col"></div>
            </div>
            <div class="yonatan-footer">
                <div class="yonatan-input-area">
                    <button id="yonatan-send-btn" class="yonatan-send-btn">
                        <svg class="w-6 h-6 transform rotate-180" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clip-rule="evenodd"></path></svg>
                    </button>
                    <input id="yonatan-input" type="text" class="yonatan-input" placeholder="כתוב/י הודעה...">
                </div>
            </div>
        `;
        elements.messagesContainer = document.getElementById('yonatan-messages');
        elements.chatInput = document.getElementById('yonatan-input');
        elements.sendButton = document.getElementById('yonatan-send-btn');
        
        elements.sendButton.addEventListener('click', sendMessage);
        elements.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Render existing messages
        state.conversationHistory.forEach(msg => addMessageToChat(msg.sender, msg.text, false));
    }

    function addMessageToChat(sender, text, animate = true) {
        if (!elements.messagesContainer) return;
        
        // Remove typing indicator if it exists
        const typingIndicator = elements.messagesContainer.querySelector('.yonatan-typing-indicator');
        if (typingIndicator) typingIndicator.remove();
        
        const messageEl = document.createElement('div');
        messageEl.classList.add('yonatan-message', sender);
        if (!animate) messageEl.style.animation = 'none';
        
        // Basic markdown support for bold text
        messageEl.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        elements.messagesContainer.appendChild(messageEl);
        elements.messagesContainer.parentElement.scrollTop = elements.messagesContainer.parentElement.scrollHeight;
        
        if (sender === 'user') {
            state.conversationHistory.push({ sender, text });
        }
    }
    
    async function sendMessage() {
        const messageText = elements.chatInput.value.trim();
        if (!messageText) return;

        addMessageToChat('user', messageText);
        elements.chatInput.value = '';
        toggleTyping(true);

        try {
            const response = await fetch(`${API_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.sessionId, message: messageText })
            });
            const data = await response.json();
            
            if (data.error) throw new Error(data.error);

            toggleTyping(false);
            addMessageToChat('bot', data.reply);
            state.conversationHistory.push({ sender: 'bot', text: data.reply });

        } catch (error) {
            console.error("Chat API error:", error);
            toggleTyping(false);
            addMessageToChat('bot', 'אני מתנצל, נתקלתי בבעיה טכנית. נוכל לנסות שוב בעוד כמה רגעים?');
        }
    }

    function toggleTyping(isTyping) {
        state.isTyping = isTyping;
        const typingIndicator = elements.messagesContainer.querySelector('.yonatan-typing-indicator');
        if (isTyping && !typingIndicator) {
            const indicatorEl = document.createElement('div');
            indicatorEl.className = 'yonatan-typing-indicator';
            indicatorEl.innerHTML = `<span></span><span></span><span></span>`;
            elements.messagesContainer.appendChild(indicatorEl);
            elements.messagesContainer.parentElement.scrollTop = elements.messagesContainer.parentElement.scrollHeight;
        } else if (!isTyping && typingIndicator) {
            typingIndicator.remove();
        }
    }

    async function toggleWidget(forceOpen) {
        const isOpen = elements.widgetContainer.classList.contains('open');
        const shouldOpen = forceOpen !== undefined ? forceOpen : !isOpen;

        if (shouldOpen) {
            elements.widgetContainer.classList.add('open');
            elements.chatButton.style.opacity = '0';
            
            if (!state.sessionId) {
                state.uiState = 'loading';
                renderView();
                try {
                    const response = await fetch(`${API_URL}/api/init`, { method: 'POST' });
                    const data = await response.json();
                    if (data.error) throw new Error(data.error);
                    state.sessionId = data.session_id;
                    localStorage.setItem('yonatan_session_id', state.sessionId);
                    state.uiState = 'questionnaire';
                    renderView();
                } catch (error) {
                    console.error("Init error:", error);
                    const contentArea = document.getElementById('yonatan-content-area');
                    contentArea.innerHTML = '<p class="p-4 text-center text-red-600">לא ניתן היה להתחיל שיחה. אנא נסה לרענן את הדף.</p>';
                }
            } else {
                 // If returning user, skip questionnaire and go to chat
                if(state.uiState !== 'chat') {
                    state.uiState = 'chat';
                    renderView();
                    if(state.conversationHistory.length === 0) {
                         addMessageToChat('bot', 'ברוך/ה שובך! אני כאן אם תרצה/י להמשיך את שיחתנו.');
                    }
                }
            }
        } else {
            elements.widgetContainer.classList.remove('open');
            elements.chatButton.style.opacity = '1';
        }
    }
    
    function toggleFullScreen() {
        state.isFullScreen = !state.isFullScreen;
        elements.widgetContainer.classList.toggle('fullscreen');
    }

    // --- Initialization ---
    function initialize() {
        injectStyles();
        createWidget();
        // Expose a public method to open the widget from other scripts
        window.yonatanWidget = { open: () => toggleWidget(true) };
    }

    // Wait for the DOM to be fully loaded before initializing
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})();
