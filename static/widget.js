// תוספת debugging לקובץ widget.js - הוסף בתחילת הפונקציה sendMessage

async function sendMessage(messageTextOverride) {
    const messageText = messageTextOverride || elements.chatInput.value.trim();
    if (!messageText || state.isTyping) return;

    // DEBUG: לוג מפורט של הנתונים שנשלחים
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
            
            // DEBUG: הכנת הנתונים לשליחה
            const requestData = { 
                session_id: state.sessionId, 
                message: messageText,
                timestamp: Date.now()
            };
            
            console.log('🔍 DEBUG - נתוני הבקשה:', JSON.stringify(requestData, null, 2));
            
            // בדיקת תקינות לפני שליחה
            if (!state.sessionId) {
                throw new Error('חסר session_id');
            }
            
            if (!messageText || typeof messageText !== 'string') {
                throw new Error('הודעה לא תקינה');
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
                
                console.log('✅ DEBUG - הודעה התקבלה בהצלחה:', {
                    length: fullResponseText.length,
                    isFallback: detectFallbackResponse(fullResponseText)
                });
                
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
                console.error("🔍 DEBUG - שגיאת סטרימינג:", streamError);
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