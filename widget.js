// Yonatan Premium Enhanced Widget v4.0 - Questionnaire & Precision Update
(function() {
    if (window.yonatanWidgetLoaded) return;
    window.yonatanWidgetLoaded = true;

    const API_URL = window.location.origin;
    const WIDGET_VERSION = '4.0.0';

    let state = {
        uiState: 'closed', // closed, loading, identity, user_details, select_child, add_child, questionnaire, conversation
        isFullScreen: false,
        sessionId: null,
        userDetails: null,
        children: [],
        selectedChild: null,
        conversationHistory: [],
        currentConversationId: null,
        isTyping: false,
        lastError: null,
        // ... strings remain the same
    };

    const elements = { /* ... */ };

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
        state.sessionId = localStorage.getItem('yonatan_session_id') || `session_${Date.now()}_${Math.random()}`;
        localStorage.setItem('yonatan_session_id', state.sessionId);
        state.userDetails = JSON.parse(localStorage.getItem('yonatan_user_details')) || null;
    }

    function setState(newState) { state = { ...state, ...newState }; render(); }
    function saveState() { if (state.userDetails) localStorage.setItem('yonatan_user_details', JSON.stringify(state.userDetails)); }
    function loadState() { state.userDetails = JSON.parse(localStorage.getItem('yonatan_user_details')) || null; }
    function resetSession() { localStorage.removeItem('yonatan_user_details'); setState({ userDetails: null, children: [], selectedChild: null, uiState: 'user_details' }); }

    function createWidgetShell() {
        elements.chatButton = document.createElement('div');
        elements.chatButton.id = 'yonatan-chat-button';
        elements.chatButton.innerHTML = `🧠<span class="sr-only">פתח צ'אט</span>`;
        document.body.append(elements.chatButton);
        elements.widgetContainer = document.createElement('div');
        elements.widgetContainer.id = 'yonatan-widget-container';
        elements.widgetContainer.innerHTML = `<header id="yonatan-chat-header"></header><div id="yonatan-chat-window"></div><footer id="yonatan-chat-footer"></footer>`;
        document.body.append(elements.widgetContainer);
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
        let title = "יונתן";
        if (state.uiState === 'questionnaire') title = "כמה שאלות להכוונה";
        else if (state.uiState === 'conversation' && state.selectedChild) title = `שיחה על ${state.selectedChild.name}`;
        // ... other title states
        const resizeIcon = state.isFullScreen ? '...': '...'; // SVG icons
        elements.chatHeader.innerHTML = `<div class="header-controls"><button id="resize-widget-btn">${resizeIcon}</button></div><span class="header-title">${title}</span><button id="close-widget-btn">&times;</button>`;
        document.getElementById('close-widget-btn').addEventListener('click', toggleWidget);
        document.getElementById('resize-widget-btn').addEventListener('click', toggleFullScreen);
    }
    
    function renderBody() {
        const uiMap = {
            'identity': getIdentityHTML,
            'user_details': getUserDetailsHTML,
            'select_child': getSelectChildHTML,
            'add_child': getAddChildHTML,
            'questionnaire': getQuestionnaireHTML, // NEW UI STATE
            'conversation': getConversationHTML,
            'loading': getLoadingHTML,
        };
        elements.chatWindow.innerHTML = (uiMap[state.uiState] || getWelcomeHTML)();
        attachBodyEventListeners(state.uiState);
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
    const getLoadingHTML = () => `<div class="loader"></div>`;
    const getWelcomeHTML = () => `...`;
    const getIdentityHTML = () => `...`;
    function getUserDetailsHTML() { return `...`; }
    function getSelectChildHTML() { const c = state.children.map(child => `<button class="child-card" data-child-id="${child.id}">... ${child.name} ... גיל ${child.age} ...</button>`).join(''); return `<div class="grid">${c}<button id="add-child-btn">+ הוסף ילד</button></div>`; }
    
    // MODIFIED: Precise age input
    function getAddChildHTML() {
        return `
            <div class="p-6 space-y-4">
                <div>
                    <label for="child-name-input">שם הילד/ה:</label>
                    <input type="text" id="child-name-input" class="input">
                </div>
                <div>
                    <label for="child-age-input">גיל (בשנים):</label>
                    <input type="number" id="child-age-input" min="0" max="18" class="input">
                </div>
                <div>
                    <span class="font-semibold">מין:</span>
                    <div class="flex gap-2 mt-2">
                        <label><input type="radio" name="child-gender" value="female"> בת</label>
                        <label><input type="radio" name="child-gender" value="male"> בן</label>
                    </div>
                </div>
                <div class="flex gap-2 mt-4">
                    <button id="submit-child-btn" class="btn-primary">הוספה והמשך</button>
                    <button id="back-to-children-btn" class="btn-secondary">חזרה</button>
                </div>
            </div>`;
    }

    // NEW: Questionnaire HTML
    function getQuestionnaireHTML() {
        return `
            <form id="questionnaire-form" class="p-6 space-y-4 text-right">
                <p class="text-center">כדי שאוכל לעזור בצורה הטובה ביותר, אשמח להבין קצת יותר את המצב.</p>
                <div>
                    <label for="q-main-challenge" class="font-semibold">מה האתגר המרכזי שאת/ה מתמודד/ת איתו כרגע עם ${state.selectedChild.name}?</label>
                    <input type="text" id="q-main-challenge" name="mainChallenge" class="input mt-1" required>
                </div>
                <div>
                    <label for="q-parent-feeling" class="font-semibold">איך ההתמודדות עם האתגר הזה גורמת לך להרגיש?</label>
                    <input type="text" id="q-parent-feeling" name="parentFeeling" class="input mt-1" placeholder="לדוגמה: תסכול, חוסר אונים, דאגה..." required>
                </div>
                <div>
                    <label for="q-main-goal" class="font-semibold">מה המטרה המרכזית שהיית רוצה להשיג בשיחה שלנו?</label>
                    <input type="text" id="q-main-goal" name="mainGoal" class="input mt-1" placeholder="לדוגמה: להגיב ברגיעה, להבין למה זה קורה..." required>
                </div>
                <!-- Add 7 more questions here as needed -->
                <button type="submit" class="btn-primary w-full mt-4">התחל שיחה</button>
            </form>
        `;
    }

    const getConversationHTML = () => `...`;
    const getInputBarHTML = () => `...`;

    // --- EVENT HANDLING ---
    function attachBodyEventListeners(uiState) {
        const handlers = {
            'add_child': () => {
                document.getElementById('submit-child-btn')?.addEventListener('click', handleSubmitChildDetails);
                document.getElementById('back-to-children-btn')?.addEventListener('click', () => setState({ uiState: 'select_child' }));
            },
            'questionnaire': () => {
                document.getElementById('questionnaire-form')?.addEventListener('submit', handleQuestionnaireSubmit);
            },
            // ... other handlers
        };
        handlers[uiState]?.();
    }

    // --- LOGIC / API HANDLERS ---
    async function handleSubmitChildDetails() {
        const name = document.getElementById('child-name-input')?.value.trim();
        const age = document.getElementById('child-age-input')?.value;
        const gender = document.querySelector('input[name="child-gender"]:checked')?.value;
        if (!name || !age || !gender) return alert('אנא מלאו את כל הפרטים.');
        
        setState({ uiState: 'loading' });
        try {
            const response = await fetch(`${API_URL}/api/children`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.sessionId, name, age, gender })
            });
            if (!response.ok) throw new Error('Failed to add child');
            const newChild = await response.json();
            // Transition to questionnaire after adding a child
            setState({ selectedChild: newChild, uiState: 'questionnaire' });
        } catch (error) {
            console.error('Error adding child:', error);
            setState({ lastError: error.message, uiState: 'add_child' });
        }
    }

    // NEW: Handle questionnaire submission
    async function handleQuestionnaireSubmit(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);
        const answers = Object.fromEntries(formData.entries());

        setState({ uiState: 'loading' });
        try {
            await fetch(`${API_URL}/api/questionnaire`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    child_id: state.selectedChild.id,
                    answers: answers
                })
            });
            // After submitting, start the conversation
            setState({ uiState: 'conversation', conversationHistory: [] });
        } catch (error) {
            console.error('Error submitting questionnaire:', error);
            // Fallback to conversation even if questionnaire fails
            setState({ uiState: 'conversation', conversationHistory: [] });
        }
    }
    // ... other handlers (handleSendMessage, etc.)
})();
