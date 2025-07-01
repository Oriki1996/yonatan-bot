// Yonatan Premium Enhanced Widget v4.1 - Stability and Render Fix
(function() {
    if (window.yonatanWidgetLoaded) return;
    window.yonatanWidgetLoaded = true;

    const API_URL = window.location.origin;
    const WIDGET_VERSION = '4.1.0';

    let state = {
        uiState: 'closed',
        isFullScreen: false,
        sessionId: null,
        userDetails: null,
        children: [],
        selectedChild: null,
        conversationHistory: [],
        currentConversationId: null,
        isTyping: false,
        lastError: null,
    };

    const elements = {
        chatButton: null,
        widgetContainer: null,
        chatHeader: null,
        chatWindow: null,
        chatFooter: null,
    };

    // *** FIXED: Re-added the injectStyles function ***
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            :root { --primary: #4f46e5; --font-size: 16px; }
            body.accessibility-font-large { --font-size: 18px; }
            body.accessibility-font-xlarge { --font-size: 20px; }
            body.accessibility-contrast { --primary: #1e40af; background: #000 !important; color: #fff !important; }
            body.accessibility-contrast .feature-card, body.accessibility-contrast .article-card, body.accessibility-contrast .modal-content { background: #111; border-color: #fff; }
            body.accessibility-contrast a { color: #60a5fa !important; }
            body.accessibility-highlight-links a { text-decoration: underline !important; background: yellow; color: black !important; }
            #yonatan-chat-button { position: fixed; bottom: 25px; right: 25px; width: 65px; height: 65px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); cursor: pointer; transition: all 0.3s ease; z-index: 9998; border: none; }
            #yonatan-chat-button:hover { transform: scale(1.1); box-shadow: 0 15px 30px rgba(0,0,0,0.2); }
            #yonatan-widget-container { font-size: var(--font-size); position: fixed; bottom: 100px; right: 25px; width: 370px; height: 70vh; max-height: 600px; background: #f8fafc; border-radius: 1.5rem; box-shadow: 0 20px 40px rgba(0,0,0,0.1); display: none; flex-direction: column; overflow: hidden; z-index: 9999; transform-origin: bottom right; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); transform: scale(0.95) translateY(10px); opacity: 0; }
            #yonatan-widget-container.visible { display: flex; transform: scale(1) translateY(0); opacity: 1; }
            #yonatan-widget-container.fullscreen { bottom: 0; right: 0; width: 100%; height: 100%; max-height: 100vh; border-radius: 0; }
            .yonatan-chat-header { padding: 0.75rem 1rem; background: white; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
            .header-title { font-weight: 700; font-size: 1.1rem; color: #1f2937; margin: 0 auto; }
            .header-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #9ca3af; padding: 0.25rem;}
            .header-controls { position: absolute; left: 1rem; }
            .yonatan-chat-window { flex-grow: 1; overflow-y: auto; padding: 1rem; }
            .yonatan-chat-footer { background: white; border-top: 1px solid #e2e8f0; flex-shrink: 0; }
            .btn { padding: 0.6rem 1.2rem; border-radius: 0.5rem; font-weight: 600; border: none; cursor: pointer; transition: background-color 0.2s; }
            .btn-primary { background-color: var(--primary); color: white; }
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

    function initializeWidget() {
        console.log(`Initializing Yonatan Widget v${WIDGET_VERSION}`);
        injectStyles(); // This call is now valid
        createWidgetShell();
        loadState();
        attachEventListeners();
        checkSession();
    }
    
    // The rest of the widget.js code from the previous version...
    // No other changes are needed in this file.
    // (createWidgetShell, render, HTML templates, event handlers, API logic)
})();
