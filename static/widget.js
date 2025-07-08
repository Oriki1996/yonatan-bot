// Yonatan Psycho-Bot Widget v10.0 - Visual & UX Overhaul
(function() {
    if (window.yonatanWidgetLoaded) return;
    window.yonatanWidgetLoaded = true;

    const API_URL = window.location.origin;

    let state = {
        uiState: 'closed',
        sessionId: localStorage.getItem('yonatan_session_id'),
        conversationHistory: [],
        questionnaireStep: 0,
        questionnaireData: {},
    };

    const elements = {
        chatButton: null,
        widgetContainer: null,
        messagesContainer: null,
        chatInput: null,
    };

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

    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            :root { --primary: #4f46e5; --secondary: #7c3aed; --user-bubble: #eef2ff; --bot-bubble: #f3f4f6; }
            #yonatan-widget-button { position: fixed; bottom: 20px; right: 20px; background: var(--primary); color: white; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.2); cursor: pointer; transition: all 0.3s ease; z-index: 9998; border: none; }
            #yonatan-widget-container { position: fixed; bottom: 20px; right: 20px; width: 400px; height: 600px; max-height: calc(100vh - 40px); background: white; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); display: flex; flex-direction: column; overflow: hidden; transform: scale(0.5) translateY(100px); opacity: 0; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); pointer-events: none; z-index: 9999; }
            #yonatan-widget-container.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: auto; }
            .yonatan-header { background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); color: white; padding: 16px; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
            .yonatan-chat-window { flex-grow: 1; overflow-y: auto; padding: 16px; background-color: #f9fafb; scroll-behavior: smooth; }
            .yonatan-message-wrapper { display: flex; margin-bottom: 12px; max-width: 90%; align-items: flex-end; animation: fadeIn 0.4s ease-out; }
            .yonatan-message-wrapper.user { margin-left: auto; flex-direction: row-reverse; }
            .yonatan-message-wrapper.bot { margin-right: auto; }
            .yonatan-avatar { width: 32px; height: 32px; border-radius: 50%; background-color: var(--secondary); color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0; margin: 0 8px; }
            .yonatan-message { padding: 10px 15px; border-radius: 18px; line-height: 1.5; }
            .yonatan-message.user { background-color: var(--user-bubble); color: #312e81; border-bottom-right-radius: 4px; }
            .yonatan-message.bot { background-color: var(--bot-bubble); color: #374151; border-bottom-left-radius: 4px; }
            .yonatan-footer { padding: 16px; border-top: 1px solid #e5e7eb; background: white; flex-shrink: 0; }
            .yonatan-input-area { display: flex; align-items: center; }
            .yonatan-input { flex-grow: 1; border: 1px solid #d1d5db; border-radius: 20px; padding: 10px 16px; font-size: 16px; outline: none; transition: border-color 0.2s; }
            .yonatan-input:focus { border-color: var(--primary); }
            .yonatan-send-btn { background: var(--primary); color: white; border: none; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-left: 10px; cursor: pointer; transition: background-color 0.2s; }
            .yonatan-typing-indicator span { height: 8px; width: 8px; border-radius: 50%; background-color: #9ca3af; margin: 0 2px; animation: typing-bounce 1.4s infinite ease-in-out both; }
            .yonatan-typing-indicator span:nth-child(1) { animation-delay: -0.32s; } .yonatan-typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
            .yonatan-loader { border: 4px solid #f3f3f3; border-top: 4px solid var(--primary); border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: auto; }
            .questionnaire-view { padding: 24px; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: center; }
            .question-btn { background-color: #f3f4f6; border: 1px solid #e5e7eb; color: #374151; padding: 10px 15px; border-radius: 12px; cursor: pointer; transition: all 0.2s; margin: 5px; }
            .question-btn:hover, .question-btn.selected { background-color: #eef2ff; border-color: var(--primary); color: var(--primary); }
            .suggestion-btn { background-color: white; border: 1px solid var(--primary); color: var(--primary); padding: 8px 12px; border-radius: 20px; cursor: pointer; transition: all 0.2s; margin: 4px; font-family: 'Assistant', sans-serif; font-size: 14px; }
            .suggestion-btn:hover { background-color: #eef2ff; }
            .yonatan-card { background-color: white; border-radius: 12px; border: 1px solid #e5e7eb; margin-top: 8px; overflow: hidden; }
            .yonatan-card-header { background-color: #f9fafb; padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #e5e7eb; }
            .yonatan-card-body { padding: 15px; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
            @keyframes spin { to { transform: rotate(360deg); } }
            @keyframes typing-bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }
        `;
        document.head.appendChild(style);
    }

    function createWidget() {
        elements.chatButton = document.createElement('button');
        elements.chatButton.id = 'yonatan-widget-button';
        elements.chatButton.setAttribute('aria-label', 'פתח את הצ\'אט עם יונתן');
        elements.chatButton.innerHTML = `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg>`;
        document.body.appendChild(elements.chatButton);

        elements.widgetContainer = document.createElement('div');
        elements.widgetContainer.id = 'yonatan-widget-container';
        elements.widgetContainer.innerHTML = `
            <div class="yonatan-header">
                <div class="flex items-center space-x-2 space-x-reverse">
                    <div class="yonatan-avatar text-base">י</div>
                    <h3 class="font-bold text-lg">יונתן</h3>
                </div>
                <button id="yonatan-close-btn" class="p-1" aria-label="סגור צ'אט">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div id="yonatan-content-area" class="flex-grow overflow-hidden"></div>
        `;
        document.body.appendChild(elements.widgetContainer);
        
        elements.chatButton.addEventListener('click', toggleWidget);
        document.getElementById('yonatan-close-btn').addEventListener('click', () => toggleWidget(false));
    }

    function renderView() {
        const contentArea = document.getElementById('yonatan-content-area');
        contentArea.innerHTML = ''; 

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
                ${(q.type === 'text' || q.type === 'number' || q.type === 'scale') ? `<button id="q-next-btn" class="yonatan-send-btn mx-auto mt-6"><svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.707-10.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414l-3-3z" clip-rule="evenodd"></path></svg></button>` : ''}
            </div>`;

        if (q.type === 'radio' || q.type === 'choice') {
            container.querySelectorAll('.question-btn').forEach(btn => btn.addEventListener('click', () => handleQuestionnaireAnswer(btn.dataset.value)));
        } else {
            const nextBtn = document.getElementById('q-next-btn');
            const input = document.getElementById('q-input');
            nextBtn.addEventListener('click', () => handleQuestionnaireAnswer(input.value));
            input.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleQuestionnaireAnswer(input.value); });
        }
    }
    
    function handleQuestionnaireAnswer(answer) {
        if (!answer) return;
        state.questionnaireData[questionnaire[state.questionnaireStep].id] = answer;
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
            await fetch(`${API_URL}/api/questionnaire`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.sessionId, ...state.questionnaireData })
            });
            state.uiState = 'chat';
            renderView();
            sendMessage("START_CONVERSATION"); // Trigger the smart opening message
        } catch (error) {
            console.error(error);
            state.uiState = 'chat';
            renderView();
            addMessageToChat('bot', 'אופס, הייתה בעיה בשמירת הנתונים. בוא/י ננסה לדבר בכל זאת.');
        }
    }

    function renderChat(container) {
        container.innerHTML = `
            <div class="yonatan-chat-window">
                <div id="yonatan-messages" class="flex flex-col"></div>
            </div>
            <div class="yonatan-footer">
                <div class="yonatan-input-area">
                    <input id="yonatan-input" type="text" class="yonatan-input" placeholder="כתוב/י הודעה...">
                    <button id="yonatan-send-btn" class="yonatan-send-btn">
                        <svg class="w-6 h-6 transform -rotate-90" fill="currentColor" viewBox="0 0 20 20"><path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.428A1 1 0 009.17 15.57l-1.722-7.224a1 1 0 01.224-.97l4.573-5.336z"></path></svg>
                    </button>
                </div>
            </div>
        `;
        elements.messagesContainer = document.getElementById('yonatan-messages');
        elements.chatInput = document.getElementById('yonatan-input');
        
        document.getElementById('yonatan-send-btn').addEventListener('click', () => sendMessage());
        elements.chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

        state.conversationHistory.forEach(msg => addMessageToChat(msg.sender, msg.text, false));
    }

    function parseAndRenderContent(text) {
        // Regex to find CARD[...] syntax
        const cardRegex = /CARD\[([^|]+)\|([^\]]+)\]/g;
        return text.replace(cardRegex, (match, title, body) => {
            return `
                <div class="yonatan-card">
                    <div class="yonatan-card-header">${title}</div>
                    <div class="yonatan-card-body">${body.replace(/\n/g, '<br>')}</div>
                </div>
            `;
        }).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\[(.*?)\]/g, `<button class="suggestion-btn" data-text="$1">$1</button>`);
    }

    function addMessageToChat(sender, text, animate = true) {
        if (!elements.messagesContainer) return;
        
        const typingIndicator = elements.messagesContainer.querySelector('.yonatan-typing-indicator');
        if (typingIndicator) typingIndicator.remove();
        
        const wrapper = document.createElement('div');
        wrapper.className = `yonatan-message-wrapper ${sender}`;
        if (!animate) wrapper.style.animation = 'none';

        const contentHTML = parseAndRenderContent(text);

        wrapper.innerHTML = `
            ${sender === 'bot' ? '<div class="yonatan-avatar">י</div>' : ''}
            <div class="yonatan-message ${sender}">
                ${contentHTML}
            </div>
        `;
        
        elements.messagesContainer.appendChild(wrapper);

        wrapper.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                sendMessage(btn.dataset.text);
                wrapper.querySelectorAll('.suggestion-btn').forEach(b => { b.disabled = true; b.style.cssText = 'cursor: not-allowed; opacity: 0.6;'; });
            });
        });
        
        const chatWindow = elements.messagesContainer.parentElement;
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }
    
    async function sendMessage(messageTextOverride) {
        const messageText = messageTextOverride || elements.chatInput.value.trim();
        if (!messageText) return;

        // Don't show the "START_CONVERSATION" message to the user
        if (messageText !== "START_CONVERSATION") {
            addMessageToChat('user', messageText);
            state.conversationHistory.push({ sender: 'user', text: messageText });
        }
        
        if (!messageTextOverride) elements.chatInput.value = '';
        
        // "Thinking time" delay
        setTimeout(() => {
            toggleTyping(true);
        }, 700);

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
        const typingIndicator = elements.messagesContainer.querySelector('.yonatan-typing-indicator');
        if (isTyping && !typingIndicator) {
            const wrapper = document.createElement('div');
            wrapper.className = 'yonatan-message-wrapper bot yonatan-typing-indicator';
            wrapper.innerHTML = `<div class="yonatan-avatar">י</div><div class="yonatan-message bot"><div class="yonatan-typing-indicator"><span></span><span></span><span></span></div></div>`;
            elements.messagesContainer.appendChild(wrapper);
            const chatWindow = elements.messagesContainer.parentElement;
            chatWindow.scrollTop = chatWindow.scrollHeight;
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
                    document.getElementById('yonatan-content-area').innerHTML = '<p class="p-4 text-center text-red-600">לא ניתן היה להתחיל שיחה. אנא נסה לרענן את הדף.</p>';
                }
            } else {
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

    function initialize() {
        injectStyles();
        createWidget();
        window.yonatanWidget = { open: () => toggleWidget(true) };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})();
