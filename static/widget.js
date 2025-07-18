// widget.js - קובץ מתוקן ושלם של ווידג'ט הצ'אט

document.addEventListener('DOMContentLoaded', () => {
    // --- Global Elements and State ---
    const elements = {
        chatWindow: document.getElementById('chat-window'),
        chatInput: document.getElementById('chat-input'),
        messagesContainer: document.getElementById('messages-container'),
        widgetButton: document.getElementById('chat-bubble'),
        closeChatBtn: document.getElementById('close-chat-btn'),
        sendBtn: document.getElementById('send-btn'),
        typingIndicator: document.querySelector('.typing-indicator'),
        statusText: document.querySelector('.status-text'),
        inputCounter: document.getElementById('input-counter')
    };

    const state = {
        sessionId: localStorage.getItem('yonatanSessionId') || null,
        isTyping: false,
        conversationHistory: JSON.parse(localStorage.getItem('yonatanConversationHistory')) || [],
        maxMessageLength: 5000, // Matches Flask's MAX_MESSAGE_LENGTH
        currentMessageId: 0 // To uniquely identify messages for updates (optional)
    };

    const API_URL = window.location.origin; // Assumes backend is on the same domain
    let csrfToken = null; // Will be fetched

    // --- Helper Functions ---

    /** Fetches CSRF token from the server. */
    async function getCSRFToken() {
        if (csrfToken) return csrfToken;
        try {
            const response = await fetch(`${API_URL}/api/csrf-token`); // THIS IS THE NEW ENDPOINT
            if (!response.ok) {
                // If it's not OK, it might be an HTML response (e.g., 404 page)
                const errorText = await response.text();
                console.error("Failed to fetch CSRF token. Server response:", errorText);
                throw new Error('Failed to fetch CSRF token');
            }
            const data = await response.json();
            csrfToken = data.csrf_token;
            console.log("CSRF Token fetched successfully.");
            return csrfToken;
        } catch (error) {
            console.error("Error fetching CSRF token:", error);
            // Fallback for development if CSRF is disabled or endpoint not ready
            return 'dummy_csrf_token_for_dev'; // Return a dummy token for testing if fetch fails
        }
    }

    /** Custom fetch wrapper to include CSRF token. */
    async function fetchWithCSRF(url, options = {}) {
        const token = await getCSRFToken();
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': token, // Flask-WTF or Flask-CSRF will look for this header
            ...options.headers
        };
        return fetch(url, { ...options, headers });
    }

    function toggleTyping(show) {
        if (elements.typingIndicator) {
            elements.typingIndicator.classList.toggle('hidden', !show);
        }
    }

    function updateStatusText(text) {
        if (elements.statusText) {
            elements.statusText.textContent = text;
        }
    }

    function addMessageToChat(sender, text) {
        const messageContainer = document.createElement('div');
        messageContainer.classList.add('message-container');
        messageContainer.classList.add(`${sender}-message`);
        messageContainer.setAttribute('data-message-id', state.currentMessageId++);

        const messageBubble = document.createElement('div');
        messageBubble.classList.add('message-bubble');

        messageBubble.innerHTML = text;

        elements.messagesContainer.prepend(messageContainer);

        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;

        return messageContainer;
    }

    function saveConversationToStorage() {
        localStorage.setItem('yonatanConversationHistory', JSON.stringify(state.conversationHistory));
        localStorage.setItem('yonatanSessionId', state.sessionId);
    }

    function parseAndRenderContent(text) {
        let htmlContent = text.replace(/CARD\[(.*?)?\|(.*?)\]/g, (match, title, content) => {
            const cardTitle = title ? `<strong>${title.trim()}</strong>` : '';
            return `<div class="message-card">${cardTitle}${content.trim()}</div>`;
        });

        htmlContent = htmlContent.replace(/\[(.*?)\]/g, (match, buttonText) => {
            return `<button class="suggestion-btn" data-text="${buttonText.trim()}">${buttonText.trim()}</button>`;
        });

        return htmlContent;
    }
    
    function detectFallbackResponse(text) {
        return text.includes('המערכת שלי עמוסה') || text.includes('מערכת חכמה של יונתן הפסיכו-בוט');
    }

    // --- Main Send Message Function ---
    let connectionRetries = 0;

    async function sendMessage(messageTextOverride) {
        const messageText = messageTextOverride || elements.chatInput.value.trim();
        if (!messageText || state.isTyping) return;

        console.log('🔍 DEBUG - שליחת הודעה:', {
            messageText,
            sessionId: state.sessionId,
            messageLength: messageText.length,
            isTyping: state.isTyping
        });

        state.isTyping = true;
        if (elements.chatInput) {
            elements.chatInput.disabled = true;
            elements.chatInput.value = '';
        }
        if (elements.sendBtn) elements.sendBtn.disabled = true;

        if (messageText !== "START_CONVERSATION") {
            addMessageToChat('user', messageText);
            state.conversationHistory.push({ sender: 'user', text: messageText, timestamp: Date.now() });
            saveConversationToStorage();
        }
        
        toggleTyping(true);
        updateStatusText('כותב תגובה...');
        
        let retryCount = 0;
        const maxRetries = 3;
        
        async function attemptSendMessage() {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 45000);
                
                const requestData = { 
                    session_id: state.sessionId, 
                    message: messageText,
                    timestamp: Date.now()
                };
                
                console.log('🔍 DEBUG - נתוני הבקשה:', JSON.stringify(requestData, null, 2));
                
                if (!state.sessionId) {
                    throw new Error('חסר session_id. אנא רענן את הדף.');
                }
                
                if (!messageText || typeof messageText !== 'string' || messageText.length > state.maxMessageLength) {
                    throw new Error(`הודעה לא תקינה או ארוכה מדי (מקסימום ${state.maxMessageLength} תווים).`);
                }
                
                const response = await fetchWithCSRF(`${API_URL}/api/chat`, {
                    method: 'POST',
                    body: JSON.stringify(requestData),
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);

                console.log('🔍 DEBUG - תגובת השרת:', {
                    status: response.status,
                    statusText: response.statusText,
                    headers: Object.fromEntries(response.headers.entries())
                });

                if (!response.ok) {
                    const errorText = await response.text().catch(() => 'לא ניתן לקרוא שגיאה');
                    console.error('🔍 DEBUG - שגיאת שרת:', {
                        status: response.status,
                        statusText: response.statusText,
                        errorText
                    });
                    
                    let errorData = {};
                    try {
                        errorData = JSON.parse(errorText);
                    } catch (e) {
                        errorData = { error: errorText || `שגיאת שרת: ${response.status}` };
                    }
                    
                    if (response.status === 400) {
                        if (errorData.error && errorData.error.includes('CSRF')) {
                            console.log('🔄 CSRF token expired, refreshing...');
                            csrfToken = null;
                            await getCSRFToken();
                            
                            if (retryCount < maxRetries) {
                                retryCount++;
                                return attemptSendMessage();
                            }
                        }
                        throw new Error(errorData.error || "בקשה לא תקינה - בדוק את הנתונים");
                    } else if (response.status === 429) {
                        throw new Error("יותר מדי בקשות. אנא המתן ונסה שוב.");
                    } else if (response.status === 503) {
                        throw new Error("השירות לא זמין כרגע. ננסה שוב...");
                    }
                    
                    throw new Error(errorData.error || `שגיאת שרת: ${response.status}`);
                }
                
                if (!response.body) {
                    throw new Error('התגובה לא מכילה תוכן זורם.');
                }
                
                toggleTyping(false);
                updateStatusText('מקבל תגובה...');
                
                const botMessageWrapper = addMessageToChat('bot', '');
                const botMessageContent = botMessageWrapper.querySelector('.message-bubble');
                
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
                            
                            botMessageContent.innerHTML = parseAndRenderContent(fullResponseText);
                            
                            const isFallback = detectFallbackResponse(fullResponseText);
                            const messageDiv = botMessageWrapper.querySelector('.message-bubble');
                            
                            if (isFallback && !messageDiv.classList.contains('fallback-mode')) {
                                messageDiv.classList.add('fallback-mode');
                                messageDiv.insertAdjacentHTML('beforebegin', 
                                    '<div class="fallback-indicator">💡 מצב חכם</div>'
                                );
                            }
                            
                            elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
                        }
                    }
                    
                    if (!receivedAnyContent || !fullResponseText.trim()) {
                        throw new Error('לא התקבל תוכן מהשרת');
                    }
                    
                    console.log('✅ DEBUG - הודעה התקבלה בהצלחה:', {
                        length: fullResponseText.length,
                        isFallback: detectFallbackResponse(fullResponseText)
                    });
                    
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

                    state.conversationHistory.push({ 
                        sender: 'bot', 
                        text: fullResponseText, 
                        timestamp: Date.now() 
                    });
                    saveConversationToStorage();
                    
                    updateStatusText('מוכן לשיחה');
                    connectionRetries = 0;
                    
                } catch (streamError) {
                    console.error("🔍 DEBUG - שגיאת סטרימינג:", streamError);
                    botMessageContent.innerHTML = `
                        <div class="error-message">
                            אירעה שגיאה בקבלת התשובה. 
                            <button class="retry-button" id="retry-stream-btn-${state.currentMessageId - 1}">נסה שוב</button>
                        </div>
                    `;
                    
                    document.getElementById(`retry-stream-btn-${state.currentMessageId - 1}`).addEventListener('click', () => {
                        botMessageWrapper.remove();
                        sendMessage(messageText);
                    });
                    
                    throw streamError;
                }
                
            } catch (error) {
                console.error("🔍 DEBUG - שגיאת API מפורטת:", {
                    error: error.message,
                    stack: error.stack,
                    retryCount,
                    sessionId: state.sessionId
                });
                
                if (retryCount < maxRetries && !error.message.includes('aborted')) {
                    retryCount++;
                    console.log(`🔄 DEBUG - ניסיון ${retryCount} מתוך ${maxRetries}...`);
                    
                    updateStatusText(`ניסיון ${retryCount}...`);
                    
                    const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 5000);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    
                    return attemptSendMessage();
                }
                
                toggleTyping(false);
                updateStatusText('שגיאה בתקשורת');
                
                let errorMessage = 'אירעה שגיאה בתקשורת עם השרת.';
                
                if (error.message.includes('aborted') || error.message.includes('timeout')) {
                    errorMessage = 'התגובה ארכה יותר מדי. אנא נסה שוב עם הודעה קצרה יותר.';
                } else if (error.message.includes('quota') || error.message.includes('429')) {
                    errorMessage = 'המערכת עמוסה כרגע. אנא נסה שוב בעוד כמה דקות.';
                } else if (error.message.includes('חסר session_id')) {
                    errorMessage = 'בעיה בסשן. אנא רענן את הדף.';
                } else if (error.message.includes('הודעה לא תקינה')) {
                    errorMessage = 'ההודעה לא תקינה. אנא נסה שוב.';
                } else if (connectionRetries < 2) {
                    errorMessage = 'בעיית חיבור זמנית. אנא נסה שוב.';
                } else {
                    errorMessage = 'נתקלנו בבעיה טכנית. אנא רענן את הדף או נסה מאוחר יותר.';
                }
                
                addMessageToChat('bot', `
                    <div class="error-message">
                        ${errorMessage}
                        <button class="retry-button" id="retry-message-btn-${state.currentMessageId - 1}">נסה שוב</button>
                    </div>
                `);
                
                document.getElementById(`retry-message-btn-${state.currentMessageId - 1}`).addEventListener('click', () => {
                    sendMessage(messageText);
                });
                
                connectionRetries++;
            }
        }
        
        try {
            await attemptSendMessage();
        } finally {
            state.isTyping = false;
            if (elements.chatInput) {
                elements.chatInput.disabled = false;
                elements.chatInput.focus();
            }
            if (elements.sendBtn) elements.sendBtn.disabled = false;
            
            if (elements.inputCounter) elements.inputCounter.textContent = '';
        }
    }

    // --- Widget UI Management ---

    async function initializeSession() {
        if (!state.sessionId) {
            try {
                // ADDED: Fetch CSRF token before init
                await getCSRFToken(); 
                const response = await fetchWithCSRF(`${API_URL}/api/init`, { method: 'POST' });
                
                // IMPORTANT: Check if response is JSON, if not, it's likely an HTML error page (like 404)
                const contentType = response.headers.get("content-type");
                if (!contentType || !contentType.includes("application/json")) {
                    const errorBody = await response.text();
                    console.error("API /api/init did not return JSON. Status:", response.status, "Body:", errorBody);
                    throw new Error(`API error: ${response.status} - Not JSON response`);
                }

                const data = await response.json();
                if (data.session_id) {
                    state.sessionId = data.session_id;
                    localStorage.setItem('yonatanSessionId', state.sessionId);
                    console.log("New session initialized:", state.sessionId);
                } else {
                    console.error("Failed to get session ID from /api/init:", data);
                    // Handle error: maybe show a message to the user
                }
            } catch (error) {
                console.error("Error initializing session:", error);
                // Show user a message about initialization failure
                updateStatusText('שגיאה באתחול. אנא רענן.');
            }
        }
    }

    function resetChat() {
        state.conversationHistory = [];
        localStorage.removeItem('yonatanConversationHistory');
        state.sessionId = null;
        localStorage.removeItem('yonatanSessionId');
        elements.messagesContainer.innerHTML = `
            <div class="text-center text-gray-500 text-sm py-2">
                <p class="status-text">מוכן לשיחה!</p>
                <span class="typing-indicator hidden">...יונתן מקליד</span>
            </div>
        `;
        state.currentMessageId = 0;
        initializeSession();
        updateStatusText('התחלה חדשה!');
    }

    function openChat() {
        elements.chatWindow.classList.remove('hidden');
        elements.widgetButton.classList.add('hidden');
        elements.chatInput.focus();
        
        elements.messagesContainer.innerHTML = `
            <div class="text-center text-gray-500 text-sm py-2">
                <p class="status-text">מוכן לשיחה!</p>
                <span class="typing-indicator hidden">...יונתן מקליד</span>
            </div>
        `; // Clear messages before loading history

        state.conversationHistory.forEach(msg => {
            const messageElement = addMessageToChat(msg.sender, parseAndRenderContent(msg.text));
            if (detectFallbackResponse(msg.text)) {
                messageElement.querySelector('.message-bubble').classList.add('fallback-mode');
                messageElement.querySelector('.message-bubble').insertAdjacentHTML('beforebegin', 
                    '<div class="fallback-indicator">💡 מצב חכם</div>'
                );
            }
        });
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
        updateStatusText('מוכן לשיחה');
    }

    function closeChat() {
        elements.chatWindow.classList.add('hidden');
        elements.widgetButton.classList.remove('hidden');
    }

    // --- Event Listeners ---

    elements.widgetButton.addEventListener('click', () => {
        openChat();
        if (state.conversationHistory.length === 0) {
            sendMessage("START_CONVERSATION");
        }
    });
    elements.closeChatBtn.addEventListener('click', closeChat);

    elements.sendBtn.addEventListener('click', () => sendMessage());
    elements.chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    elements.chatInput.addEventListener('input', () => {
        if (elements.inputCounter) {
            const currentLength = elements.chatInput.value.length;
            elements.inputCounter.textContent = `${currentLength}/${state.maxMessageLength}`;
            if (currentLength > state.maxMessageLength) {
                elements.inputCounter.style.color = 'red';
            } else {
                elements.inputCounter.style.color = '';
            }
            elements.inputCounter.classList.remove('hidden');
        }
    });

    // Initialize session on page load
    initializeSession();

    // Expose widget functions globally for buttons in index.html
    window.yonatanWidget = {
        open: openChat,
        close: closeChat,
        sendMessage: sendMessage,
        reset: resetChat
    };
});