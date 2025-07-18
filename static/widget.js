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
            const response = await fetch(`${API_URL}/api/csrf-token`); // Assuming you have such an endpoint
            if (!response.ok) throw new Error('Failed to fetch CSRF token');
            const data = await response.json();
            csrfToken = data.csrf_token;
            console.log("CSRF Token fetched:", csrfToken);
            return csrfToken;
        } catch (error) {
            console.error("Error fetching CSRF token:", error);
            // Fallback for development if CSRF is disabled or endpoint not ready
            return 'dummy_csrf_token_for_dev';
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
        messageContainer.setAttribute('data-message-id', state.currentMessageId++); // Unique ID for each message

        const messageBubble = document.createElement('div');
        messageBubble.classList.add('message-bubble');

        // Initial content will be empty for streaming messages
        messageBubble.innerHTML = text; // Content is updated during streaming

        messageContainer.appendChild(messageBubble);
        elements.messagesContainer.prepend(messageContainer); // Prepend to show latest message at bottom

        // Scroll to bottom (since we prepend, the container needs to scroll up)
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;

        return messageContainer; // Return container to update streaming content
    }

    function saveConversationToStorage() {
        localStorage.setItem('yonatanConversationHistory', JSON.stringify(state.conversationHistory));
        localStorage.setItem('yonatanSessionId', state.sessionId);
    }

    function parseAndRenderContent(text) {
        // Handle CARD[Title|Content] format
        let htmlContent = text.replace(/CARD\[(.*?)?\|(.*?)\]/g, (match, title, content) => {
            const cardTitle = title ? `<strong>${title.trim()}</strong>` : '';
            return `<div class="message-card">${cardTitle}${content.trim()}</div>`;
        });

        // Handle [Button Text] format for suggestions
        htmlContent = htmlContent.replace(/\[(.*?)\]/g, (match, buttonText) => {
            // Check if it's a known placeholder button for existing functionality (e.g., [בעיות תקשורת])
            // Or if it's a dynamically generated suggestion button
            // For now, treat all as suggestion buttons
            return `<button class="suggestion-btn" data-text="${buttonText.trim()}">${buttonText.trim()}</button>`;
        });

        return htmlContent;
    }
    
    function detectFallbackResponse(text) {
        // Check for specific phrases that indicate a fallback response
        return text.includes('המערכת שלי עמוסה') || text.includes('מערכת חכמה של יונתן הפסיכו-בוט');
    }

    // --- Main Send Message Function ---
    let connectionRetries = 0; // Tracks consecutive connection failures

    async function sendMessage(messageTextOverride) {
        const messageText = messageTextOverride || elements.chatInput.value.trim();
        if (!messageText || state.isTyping) return;

        // DEBUG: Detailed log of sent data
        console.log('🔍 DEBUG - שליחת הודעה:', {
            messageText,
            sessionId: state.sessionId,
            messageLength: messageText.length,
            isTyping: state.isTyping
        });

        // Update UI state
        state.isTyping = true;
        if (elements.chatInput) {
            elements.chatInput.disabled = true;
            elements.chatInput.value = '';
        }
        if (elements.sendBtn) elements.sendBtn.disabled = true;

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
                
                // DEBUG: Preparing data to send
                const requestData = { 
                    session_id: state.sessionId, 
                    message: messageText,
                    timestamp: Date.now() // Add timestamp for server-side logging
                };
                
                console.log('🔍 DEBUG - נתוני הבקשה:', JSON.stringify(requestData, null, 2));
                
                // Input validation before sending
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
                    // Enhanced error handling with detailed logging
                    const errorText = await response.text().catch(() => 'לא ניתן לקרוא שגיאה');
                    console.error('🔍 DEBUG - שגיאת שרת:', {
                        status: response.status,
                        statusText: response.statusText,
                        errorText
                    });
                    
                    // Try to parse error as JSON
                    let errorData = {};
                    try {
                        errorData = JSON.parse(errorText);
                    } catch (e) {
                        errorData = { error: errorText || `שגיאת שרת: ${response.status}` };
                    }
                    
                    // Handle specific error responses
                    if (response.status === 400) {
                        if (errorData.error && errorData.error.includes('CSRF')) {
                            console.log('🔄 CSRF token expired, refreshing...');
                            csrfToken = null; // Clear token to force refetch
                            await getCSRFToken(); // Attempt to get new token
                            
                            // Retry sending message with new token
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
                
                // Enhanced streaming response handling
                const botMessageWrapper = addMessageToChat('bot', '');
                const botMessageContent = botMessageWrapper.querySelector('.message-bubble'); // Get the bubble element
                
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
                            const messageDiv = botMessageWrapper.querySelector('.message-bubble'); // The bubble itself
                            
                            if (isFallback && !messageDiv.classList.contains('fallback-mode')) {
                                messageDiv.classList.add('fallback-mode');
                                messageDiv.insertAdjacentHTML('beforebegin', 
                                    '<div class="fallback-indicator">💡 מצב חכם</div>'
                                );
                            }
                            
                            // Auto-scroll during streaming
                            // This logic needs to scroll the messages container, not its parent
                            elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
                        }
                    }
                    
                    // Validate received content
                    if (!receivedAnyContent || !fullResponseText.trim()) {
                        throw new Error('לא התקבל תוכן מהשרת');
                    }
                    
                    console.log('✅ DEBUG - הודעה התקבלה בהצלחה:', {
                        length: fullResponseText.length,
                        isFallback: detectFallbackResponse(fullResponseText)
                    });
                    
                    // Enhanced suggestion button handling after streaming
                    // Buttons are now parsed dynamically from the fullResponseText
                    setTimeout(() => {
                        botMessageWrapper.querySelectorAll('.suggestion-btn').forEach(btn => {
                            btn.addEventListener('click', () => {
                                if (btn.disabled) return;
                                
                                sendMessage(btn.dataset.text);
                                // Disable all suggestion buttons after one is clicked
                                botMessageWrapper.querySelectorAll('.suggestion-btn').forEach(b => { 
                                    b.disabled = true; 
                                    b.style.cssText = 'cursor: not-allowed; opacity: 0.6;'; 
                                });
                            });
                        });
                    }, 500); // Small delay to ensure DOM is updated

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
                    console.error("🔍 DEBUG - שגיאת סטרימינג:", streamError);
                    botMessageContent.innerHTML = `
                        <div class="error-message">
                            אירעה שגיאה בקבלת התשובה. 
                            <button class="retry-button" id="retry-stream-btn-${state.currentMessageId - 1}">נסה שוב</button>
                        </div>
                    `;
                    // Unique ID for retry button
                    document.getElementById(`retry-stream-btn-${state.currentMessageId - 1}`).addEventListener('click', () => {
                        botMessageWrapper.remove(); // Remove incomplete message
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
                
                // Enhanced retry logic with exponential backoff
                if (retryCount < maxRetries && !error.message.includes('aborted')) {
                    retryCount++;
                    console.log(`🔄 DEBUG - ניסיון ${retryCount} מתוך ${maxRetries}...`);
                    
                    updateStatusText(`ניסיון ${retryCount}...`);
                    
                    // Exponential backoff
                    const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 5000);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    
                    return attemptSendMessage(); // Recursive call for retry
                }
                
                // Final error handling after retries exhausted
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
                } else if (connectionRetries < 2) { // Allow a couple of general connection retries
                    errorMessage = 'בעיית חיבור זמנית. אנא נסה שוב.';
                } else {
                    errorMessage = 'נתקלנו בבעיה טכנית. אנא רענן את הדף או נסה מאוחר יותר.';
                }
                
                // Add error message to chat with retry button
                addMessageToChat('bot', `
                    <div class="error-message">
                        ${errorMessage}
                        <button class="retry-button" id="retry-message-btn-${state.currentMessageId - 1}">נסה שוב</button>
                    </div>
                `);
                // Unique ID for retry button
                document.getElementById(`retry-message-btn-${state.currentMessageId - 1}`).addEventListener('click', () => {
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
            if (elements.sendBtn) elements.sendBtn.disabled = false;
            
            if (elements.inputCounter) elements.inputCounter.textContent = '';
        }
    }

    // --- Widget UI Management ---

    /** Initializes a new chat session. */
    async function initializeSession() {
        if (!state.sessionId) {
            try {
                const response = await fetchWithCSRF(`${API_URL}/api/init`, { method: 'POST' }); // Assuming an /api/init endpoint
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
                // Handle error
            }
        }
    }

    /** Clears chat history and re-initializes session. */
    function resetChat() {
        state.conversationHistory = [];
        localStorage.removeItem('yonatanConversationHistory');
        state.sessionId = null; // Clear old session ID
        localStorage.removeItem('yonatanSessionId');
        elements.messagesContainer.innerHTML = `
            <div class="text-center text-gray-500 text-sm py-2">
                <p class="status-text">מוכן לשיחה!</p>
                <span class="typing-indicator hidden">...יונתן מקליד</span>
            </div>
        `;
        state.currentMessageId = 0;
        initializeSession(); // Get a new session ID
        updateStatusText('התחלה חדשה!');
    }

    /** Opens the chat window. */
    function openChat() {
        elements.chatWindow.classList.remove('hidden');
        elements.chatBubble.classList.add('hidden');
        elements.chatInput.focus();
        // Load history when opening
        state.conversationHistory.forEach(msg => {
            const messageElement = addMessageToChat(msg.sender, parseAndRenderContent(msg.text));
            // Apply fallback class if it was a fallback message in history
            if (detectFallbackResponse(msg.text)) {
                messageElement.querySelector('.message-bubble').classList.add('fallback-mode');
                messageElement.querySelector('.message-bubble').insertAdjacentHTML('beforebegin', 
                    '<div class="fallback-indicator">💡 מצב חכם</div>'
                );
            }
        });
        // Scroll to the bottom after loading history
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
        updateStatusText('מוכן לשיחה'); // Reset status text
    }

    /** Closes the chat window. */
    function closeChat() {
        elements.chatWindow.classList.add('hidden');
        elements.chatBubble.classList.remove('hidden');
    }

    // --- Event Listeners ---

    elements.widgetButton.addEventListener('click', () => {
        openChat();
        if (state.conversationHistory.length === 0) {
            sendMessage("START_CONVERSATION"); // Send initial greeting only on first open
        }
    });
    elements.closeChatBtn.addEventListener('click', closeChat);

    elements.sendBtn.addEventListener('click', () => sendMessage());
    elements.chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Character counter for input
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