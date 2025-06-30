// Yonatan Premium Enhanced Widget v2.2 - Bug Fixes & Stability
(function() {
    // --- SETUP ---
    if (window.yonatanWidgetLoaded) {
        return;
    }
    window.yonatanWidgetLoaded = true;

    // --- CONFIGURATION ---
    const API_URL = window.location.origin;
    const WIDGET_VERSION = '2.2.0';

    // --- STATE MANAGEMENT ---
    let state = {
        uiState: 'closed', // closed, loading, identity, user_details, select_child, add_child, conversation
        sessionId: null,
        userDetails: null,
        children: [],
        selectedChild: null,
        conversationHistory: [],
        currentConversationId: null,
        isTyping: false,
        lastError: null,
        strings: {
            welcomeTitle: 'ברוכים הבאים ליונתן',
            welcomeSubtitle: 'עוזר וירטואלי מבוסס CBT להורים',
            identityTitle: (name) => `שלום ${name}!`,
            identitySubtitle: 'נעים לראות אותך שוב.',
            identityConfirm: 'כן, זה אני ✨',
            identityDeny: 'לא, זה לא אני',
            detailsTitle: 'בואו נכיר',
            detailsSubtitle: 'איך תרצו שנפנה אליכם?',
            yourName: 'השם שלך:',
            yourNamePlaceholder: 'לדוגמה: שרה',
            genderPrompt: 'איך תרצו שנפנה אליכם?',
            genderFemale: 'בלשון נקבה (את)',
            genderMale: 'בלשון זכר (אתה)',
            selectChildTitle: 'על איזה ילד נדבר היום?',
            addChildBtn: '+ הוסף ילד חדש',
            addChildTitle: 'הוספת ילד חדש',
            addChildSubtitle: 'ספרו לנו על הילד/ה.',
            childNameLabel: 'שם הילד/ה:',
            childGenderLabel: 'מין:',
            childAgeLabel: 'קבוצת גיל:',
            startChatBtn: 'התחל שיחה 💬',
            endChatBtn: 'סיים שיחה וקבל סיכום',
            inputPlaceholder: 'כתבו כאן את הודעתכם...',
            sendMessage: 'שלח',
            errorGeneral: 'אופס, משהו השתבש. נסו שוב בעוד רגע.',
            errorConnection: 'בעיית חיבור. אנא בדקו את הרשת.',
        }
    };

    // --- DOM ELEMENTS CACHE ---
    const elements = {
        chatButton: null,
        widgetContainer: null,
        chatHeader: null,
        chatWindow: null,
        chatFooter: null,
    };

    // --- CORE INITIALIZATION ---
    document.addEventListener('DOMContentLoaded', initializeWidget);

    function initializeWidget() {
        console.log(`Initializing Yonatan Widget v${WIDGET_VERSION}`);
        injectStyles();
        createWidgetShell();
        loadState();
        attachEventListeners();
        checkSession();
    }

    function checkSession() {
        const sessionId = localStorage.getItem('yonatan_session_id');
        const userDetails = JSON.parse(localStorage.getItem('yonatan_user_details'));

        if (sessionId) {
            state.sessionId = sessionId;
        } else {
            state.sessionId = `session_${Date.now()}_${Math.random()}`;
            localStorage.setItem('yonatan_session_id', state.sessionId);
        }
        
        if (userDetails) {
            state.userDetails = userDetails;
        }
    }

    // --- STATE & LOCAL STORAGE ---
    function setState(newState) {
        state = { ...state, ...newState };
        render();
    }

    function saveState() {
        try {
            if (state.userDetails) {
                localStorage.setItem('yonatan_user_details', JSON.stringify(state.userDetails));
            }
        } catch (error) {
            console.error('Error saving state to localStorage:', error);
        }
    }

    function loadState() {
        try {
            const userDetails = JSON.parse(localStorage.getItem('yonatan_user_details'));
            if (userDetails) {
                state.userDetails = userDetails;
            }
        } catch (error) {
            console.error('Error loading state from localStorage:', error);
            localStorage.removeItem('yonatan_user_details');
        }
    }

    function resetSession() {
        localStorage.removeItem('yonatan_user_details');
        state.userDetails = null;
        state.children = [];
        state.selectedChild = null;
        setState({ uiState: 'user_details' });
    }

    // --- UI & RENDERING ---
    function createWidgetShell() {
        elements.chatButton = document.createElement('div');
        elements.chatButton.id = 'yonatan-chat-button';
        elements.chatButton.innerHTML = `🧠<span class="sr-only">פתח צ'אט</span>`;
        elements.chatButton.setAttribute('role', 'button');
        elements.chatButton.setAttribute('aria-label', 'פתח צ\'אט עם יונתן');
        
        elements.widgetContainer = document.createElement('div');
        elements.widgetContainer.id = 'yonatan-widget-container';
        elements.widgetContainer.innerHTML = `
            <header id="yonatan-chat-header" class="yonatan-chat-header"></header>
            <div id="yonatan-chat-window" class="yonatan-chat-window" role="log" aria-live="polite"></div>
            <footer id="yonatan-chat-footer" class="yonatan-chat-footer"></footer>
        `;

        document.body.append(elements.chatButton, elements.widgetContainer);

        elements.chatHeader = document.getElementById('yonatan-chat-header');
        elements.chatWindow = document.getElementById('yonatan-chat-window');
        elements.chatFooter = document.getElementById('yonatan-chat-footer');
    }

    function render() {
        renderHeader();
        renderBody();
        renderFooter();
    }
    
    function renderHeader() {
        const { uiState, selectedChild, strings } = state;
        let title = strings.welcomeTitle;

        if (uiState === 'select_child') title = strings.selectChildTitle;
        else if (uiState === 'conversation' && selectedChild) title = `שיחה על ${selectedChild.name}`;
        else if (uiState === 'add_child') title = strings.addChildTitle;
        else if (state.userDetails) title = strings.identityTitle(state.userDetails.name);
        
        elements.chatHeader.innerHTML = `
            <span class="header-title">${title}</span>
            <button id="close-widget-btn" class="header-btn" aria-label="סגור חלון">&times;</button>
        `;
        document.getElementById('close-widget-btn').addEventListener('click', toggleWidget);
    }
    
    function renderBody() {
        const { uiState } = state;
        let content = '';
        switch (uiState) {
            case 'identity': content = getIdentityHTML(); break;
            case 'user_details': content = getUserDetailsHTML(); break;
            case 'select_child': content = getSelectChildHTML(); break;
            case 'add_child': content = getAddChildHTML(); break;
            case 'conversation': content = getConversationHTML(); break;
            case 'loading': content = getLoadingHTML(); break;
            default: content = getWelcomeHTML();
        }
        elements.chatWindow.innerHTML = content;
        attachBodyEventListeners(uiState);
        scrollToBottom(false);
    }
    
    function renderFooter() {
         if (state.uiState === 'conversation') {
             elements.chatFooter.innerHTML = getInputBarHTML();
             attachFooterEventListeners();
         } else {
             elements.chatFooter.innerHTML = '';
         }
    }

    // --- HTML TEMPLATES ---
    const getLoadingHTML = () => `<div class="flex justify-center items-center h-full"><div class="loader"></div></div>`;
    const getWelcomeHTML = () => `<div class="p-8 text-center"><h2 class="text-2xl font-bold mb-2">${state.strings.welcomeTitle}</h2><p class="text-gray-600">${state.strings.welcomeSubtitle}</p></div>`;
    
    function getIdentityHTML() {
        return `
            <div class="p-8 text-center">
                <h2 class="text-2xl font-bold mb-2">${state.strings.identityTitle(state.userDetails.name)}</h2>
                <p class="text-gray-600 mb-6">${state.strings.identitySubtitle}</p>
                <div class="flex justify-center gap-4">
                    <button id="confirm-identity-btn" class="btn btn-primary">${state.strings.identityConfirm}</button>
                    <button id="deny-identity-btn" class="btn btn-secondary">${state.strings.identityDeny}</button>
                </div>
            </div>`;
    }

    function getUserDetailsHTML() {
        return `
            <div class="p-6">
                <h3 class="text-xl font-bold text-center mb-1">${state.strings.detailsTitle}</h3>
                <p class="text-center text-gray-500 mb-6">${state.strings.detailsSubtitle}</p>
                <div class="space-y-4">
                    <div>
                        <label for="name-input" class="font-semibold text-gray-700">${state.strings.yourName}</label>
                        <input type="text" id="name-input" class="w-full mt-1 p-2 border border-gray-300 rounded-lg" placeholder="${state.strings.yourNamePlaceholder}">
                    </div>
                    <div>
                        <span class="font-semibold text-gray-700">${state.strings.genderPrompt}</span>
                        <div class="mt-2 flex gap-2"><label class="flex-1 text-center p-3 border rounded-lg hover:bg-gray-100 cursor-pointer"><input type="radio" name="gender" value="female" class="mr-2"><span>${state.strings.genderFemale}</span></label><label class="flex-1 text-center p-3 border rounded-lg hover:bg-gray-100 cursor-pointer"><input type="radio" name="gender" value="male" class="mr-2"><span>${state.strings.genderMale}</span></label></div>
                    </div>
                    <button id="submit-details-btn" class="w-full btn btn-primary mt-4">המשך</button>
                </div>
            </div>`;
    }

    function getSelectChildHTML() {
        const childrenCards = state.children.map(child => `
            <button class="child-card" data-child-id="${child.id}">
                <div class="text-3xl">${child.gender === 'male' ? '👦' : '👧'}</div>
                <div class="font-bold text-lg">${child.name}</div>
                <div class="text-sm text-gray-500">גיל ${child.age_range}</div>
            </button>
        `).join('');

        return `<div class="p-4"><div class="grid grid-cols-2 gap-4">${childrenCards}<button id="add-child-btn" class="child-card items-center justify-center"><div class="text-3xl">+</div><div class="font-bold text-lg">${state.strings.addChildBtn}</div></button></div></div>`;
    }
    
    function getAddChildHTML() {
        return `
            <div class="p-6">
                <div class="space-y-4">
                    <div>
                        <label for="child-name-input" class="font-semibold text-gray-700">${state.strings.childNameLabel}</label>
                        <input type="text" id="child-name-input" class="w-full mt-1 p-2 border border-gray-300 rounded-lg">
                    </div>
                    <div>
                        <span class="font-semibold text-gray-700">${state.strings.childGenderLabel}</span>
                        <div class="mt-2 flex gap-2"><label class="flex-1 text-center p-3 border rounded-lg hover:bg-gray-100 cursor-pointer"><input type="radio" name="child-gender" value="female" class="mr-2"><span>בת</span></label><label class="flex-1 text-center p-3 border rounded-lg hover:bg-gray-100 cursor-pointer"><input type="radio" name="child-gender" value="male" class="mr-2"><span>בן</span></label></div>
                    </div>
                    <div>
                        <span class="font-semibold text-gray-700">${state.strings.childAgeLabel}</span>
                        <div class="mt-2 grid grid-cols-2 gap-2">
                            <label class="flex items-center p-2 border rounded-lg hover:bg-gray-100 cursor-pointer text-sm"><input type="radio" name="child-age" value="3-5" class="mr-2"><span>3-5</span></label>
                            <label class="flex items-center p-2 border rounded-lg hover:bg-gray-100 cursor-pointer text-sm"><input type="radio" name="child-age" value="6-8" class="mr-2"><span>6-8</span></label>
                            <label class="flex items-center p-2 border rounded-lg hover:bg-gray-100 cursor-pointer text-sm"><input type="radio" name="child-age" value="9-12" class="mr-2"><span>9-12</span></label>
                            <label class="flex items-center p-2 border rounded-lg hover:bg-gray-100 cursor-pointer text-sm"><input type="radio" name="child-age" value="13-18" class="mr-2"><span>13-18</span></label>
                        </div>
                    </div>
                    <div class="flex gap-2 mt-4">
                        <button id="submit-child-btn" class="w-full btn btn-primary">הוספה</button>
                        <button id="back-to-children-btn" class="w-full btn btn-secondary">ביטול</button>
                    </div>
                </div>
            </div>`;
    }

    function getConversationHTML() {
        return state.conversationHistory.map(msg => {
            const isUser = msg.role === 'user';
            return `<div class="message-wrapper ${isUser ? 'user' : 'bot'}"><div class="message-bubble">${msg.parts[0].text}</div></div>`;
        }).join('') + (state.isTyping ? `<div class="message-wrapper bot"><div class="message-bubble typing-indicator"><span></span><span></span><span></span></div></div>` : '');
    }

    const getInputBarHTML = () => `<div class="flex items-center p-2"><textarea id="message-input" class="flex-grow p-2 border rounded-lg resize-none" placeholder="${state.strings.inputPlaceholder}" rows="1"></textarea><button id="send-btn" class="mr-2 btn btn-primary">${state.strings.sendMessage}</button></div>`;

    // --- EVENT HANDLING ---
    function attachEventListeners() {
        elements.chatButton.addEventListener('click', toggleWidget);
    }
    
    function attachBodyEventListeners(uiState) {
        const handlers = {
            'identity': () => {
                document.getElementById('confirm-identity-btn')?.addEventListener('click', handleGetChildren);
                document.getElementById('deny-identity-btn')?.addEventListener('click', resetSession);
            },
            'user_details': () => {
                document.getElementById('submit-details-btn')?.addEventListener('click', handleSubmitUserDetails);
            },
            'select_child': () => {
                document.getElementById('add-child-btn')?.addEventListener('click', () => setState({uiState: 'add_child'}));
                document.querySelectorAll('.child-card:not(#add-child-btn)').forEach(card => card.addEventListener('click', handleSelectChild));
            },
            'add_child': () => {
                document.getElementById('submit-child-btn')?.addEventListener('click', handleSubmitChildDetails);
                document.getElementById('back-to-children-btn')?.addEventListener('click', handleGetChildren);
            }
        };
        handlers[uiState]?.();
    }
    
    function attachFooterEventListeners() {
        const sendBtn = document.getElementById('send-btn');
        const messageInput = document.getElementById('message-input');
        if (!sendBtn || !messageInput) return;
        
        sendBtn.addEventListener('click', handleSendMessage);
        messageInput.addEventListener('keydown', e => (e.key === 'Enter' && !e.shiftKey) && (e.preventDefault(), handleSendMessage()));
        messageInput.addEventListener('input', () => {
            messageInput.style.height = 'auto';
            messageInput.style.height = `${messageInput.scrollHeight}px`;
        });
    }

    function toggleWidget() {
        const isOpening = !elements.widgetContainer.classList.contains('visible');
        elements.widgetContainer.classList.toggle('visible');
        elements.chatButton.classList.toggle('open');
        
        if (isOpening) {
            setState({ uiState: state.userDetails ? 'identity' : 'user_details' });
        } else {
            setState({ uiState: 'closed' });
        }
    }

    // --- LOGIC / API HANDLERS ---
    async function handleGetChildren() {
        setState({uiState: 'loading'});
        try {
            const response = await fetch(`${API_URL}/api/children?session_id=${state.sessionId}`);
            if (!response.ok) throw new Error('Network response was not ok');
            const children = await response.json();
            setState({ children, uiState: 'select_child' });
        } catch (error) {
            console.error('Error fetching children:', error);
            setState({ lastError: state.strings.errorConnection, uiState: 'identity' });
        }
    }

    async function handleSubmitUserDetails() {
        const name = document.getElementById('name-input')?.value.trim();
        const gender = document.querySelector('input[name="gender"]:checked')?.value;
        if (!name || !gender) return alert('אנא מלאו את כל השדות.');
        
        setState({uiState: 'loading'});
        try {
            const response = await fetch(`${API_URL}/api/session`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.sessionId, name, gender })
            });
            if (!response.ok) throw new Error('Failed to save details');
            state.userDetails = await response.json();
            saveState();
            await handleGetChildren();
        } catch(error) {
            console.error('Error submitting user details:', error);
            setState({ lastError: state.strings.errorGeneral, uiState: 'user_details' });
        }
    }
    
    async function handleSubmitChildDetails() {
        const name = document.getElementById('child-name-input')?.value.trim();
        const gender = document.querySelector('input[name="child-gender"]:checked')?.value;
        const age_range = document.querySelector('input[name="child-age"]:checked')?.value;
        if (!name || !gender || !age_range) return alert('אנא מלאו את כל הפרטים.');

        setState({ uiState: 'loading' });
        try {
            const response = await fetch(`${API_URL}/api/children`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.sessionId, name, gender, age_range })
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Failed to add child');
            }
            await handleGetChildren();
        } catch (error) {
            console.error('Error adding child:', error);
            setState({ lastError: error.message, uiState: 'add_child' });
        }
    }

    function handleSelectChild(event) {
        const childId = parseInt(event.currentTarget.dataset.childId);
        const child = state.children.find(c => c.id === childId);
        setState({ selectedChild: child, uiState: 'conversation', conversationHistory: [] });
    }
    
    async function handleSendMessage() {
        const input = document.getElementById('message-input');
        const messageText = input.value.trim();
        if (!messageText) return;

        const userMessage = { role: 'user', parts: [{ text: messageText }] };
        const newHistory = [...state.conversationHistory, userMessage];
        setState({ conversationHistory: newHistory, isTyping: true });
        
        input.value = '';
        input.style.height = 'auto';

        try {
            const response = await fetch(`${API_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    child_id: state.selectedChild.id,
                    conversation_id: state.currentConversationId,
                    history: newHistory,
                }),
            });
            if (!response.ok) throw new Error('Chat API error');
            const data = await response.json();
            const botMessage = { role: 'model', parts: [{ text: data.response }] };
            setState({
                conversationHistory: [...newHistory, botMessage],
                currentConversationId: data.conversation_id,
                isTyping: false
            });
        } catch(error) {
            console.error('Chat error:', error);
            const errorMessage = { role: 'model', parts: [{ text: state.strings.errorGeneral }] };
            setState({ conversationHistory: [...newHistory, errorMessage], isTyping: false });
        }
    }

    // --- STYLES ---
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            :root { --primary: #4f46e5; }
            #yonatan-chat-button { position: fixed; bottom: 25px; right: 25px; width: 65px; height: 65px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); cursor: pointer; transition: all 0.3s ease; z-index: 9998; border: none; }
            #yonatan-chat-button:hover { transform: scale(1.1); box-shadow: 0 15px 30px rgba(0,0,0,0.2); }
            #yonatan-chat-button.open { transform: scale(0.9); }
            #yonatan-widget-container { position: fixed; bottom: 100px; right: 25px; width: 370px; height: 70vh; max-height: 600px; background: #f8fafc; border-radius: 1.5rem; box-shadow: 0 20px 40px rgba(0,0,0,0.1); display: none; flex-direction: column; overflow: hidden; z-index: 9999; transform-origin: bottom right; transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.2s ease; transform: scale(0.95) translateY(10px); opacity: 0; }
            #yonatan-widget-container.visible { display: flex; transform: scale(1) translateY(0); opacity: 1; }
            .yonatan-chat-header { padding: 1rem 1.5rem; background: white; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
            .header-title { font-weight: 700; font-size: 1.1rem; color: #1f2937; }
            .header-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #9ca3af; padding: 0.25rem;}
            .yonatan-chat-window { flex-grow: 1; overflow-y: auto; padding: 1rem; }
            .yonatan-chat-footer { background: white; border-top: 1px solid #e2e8f0; flex-shrink: 0; }
            .btn { padding: 0.6rem 1.2rem; border-radius: 0.5rem; font-weight: 600; border: none; cursor: pointer; transition: background-color 0.2s; }
            .btn-primary { background-color: var(--primary); color: white; }
            .btn-primary:hover { background-color: #4338ca; }
            .btn-secondary { background-color: #e5e7eb; color: #374151; }
            .btn-secondary:hover { background-color: #d1d5db; }
            .child-card { display: flex; flex-direction: column; align-items: center; justify-content: center; background-color: white; border: 1px solid #e2e8f0; border-radius: 0.75rem; padding: 1rem; text-align: center; cursor: pointer; transition: all 0.2s ease-in-out; height: 120px; }
            .child-card:hover { transform: translateY(-4px); box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-color: var(--primary); }
            .message-wrapper { display: flex; margin-bottom: 0.75rem; animation: msg-fade-in 0.3s ease; }
            .message-wrapper.user { justify-content: flex-end; }
            .message-wrapper.bot { justify-content: flex-start; }
            .message-bubble { padding: 0.75rem 1rem; border-radius: 1rem; max-width: 80%; line-height: 1.5; }
            .message-wrapper.user .message-bubble { background-color: var(--primary); color: white; border-bottom-right-radius: 0.25rem; }
            .message-wrapper.bot .message-bubble { background-color: #e5e7eb; color: #1f2937; border-bottom-left-radius: 0.25rem; }
            .typing-indicator span { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: #9ca3af; margin: 0 2px; animation: typing-bounce 1.4s infinite ease-in-out both; }
            .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
            .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
            .loader { border: 4px solid #f3f3f3; border-top: 4px solid var(--primary); border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; }
            .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border-width: 0; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            @keyframes msg-fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
            @keyframes typing-bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }
        `;
        document.head.appendChild(style);
    }
    
    function scrollToBottom(smooth = true) {
        if (!elements.chatWindow) return;
        elements.chatWindow.scrollTo({ top: elements.chatWindow.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
    }
})();
