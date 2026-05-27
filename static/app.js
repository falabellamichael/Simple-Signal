// Simple Signal Web CLI Client Logic

// Configuration & State
let conversationHistory = [];
let isStreaming = false;
let currentAbortController = null;

// DOM Elements
const terminalScreen = document.getElementById('terminal-screen');
const chatInput = document.getElementById('chat-input');
const actionBtn = document.getElementById('action-btn');
const themeSelector = document.getElementById('theme-selector');
const modelSelector = document.getElementById('model-selector');
const modelSelectWrapper = document.getElementById('model-select-wrapper');

// Initialize Web UI
document.addEventListener('DOMContentLoaded', async () => {
    await loadConfig();
    await loadModels();
    
    // Auto-focus input
    chatInput.focus();
    
    // Setup event listeners
    chatInput.addEventListener('input', autoResizeInput);
    chatInput.addEventListener('keydown', handleKeydown);
    actionBtn.addEventListener('click', handleAction);
    themeSelector.addEventListener('change', handleThemeChange);
    modelSelector.addEventListener('change', handleModelChange);
    
    // Clicking anywhere in the terminal screen focuses the text input (CLI feel)
    terminalScreen.addEventListener('click', () => {
        chatInput.focus();
    });
});

// Auto-resize input text area
function autoResizeInput() {
    chatInput.style.height = 'auto';
    chatInput.style.height = (chatInput.scrollHeight) + 'px';
}

// Handle Enter to send, Shift+Enter to newline
function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitMessage();
    }
}

// Fetch active config from FastAPI backend
async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        if (res.ok) {
            const config = await res.json();
            
            // Set theme attribute on body
            document.body.setAttribute('data-theme', config.theme);
            themeSelector.value = config.theme;
        }
    } catch (e) {
        console.error('Failed to load config:', e);
    }
}

// Detect models if API (LM Studio) is connected
async function loadModels() {
    try {
        const res = await fetch('/api/models');
        if (res.ok) {
            const data = await res.json();
            if (data.connected && data.models.length > 0) {
                // Clear existing options except default
                modelSelector.innerHTML = '<option value="">Default API Model</option>';
                
                data.models.forEach(model => {
                    const opt = document.createElement('option');
                    opt.value = model;
                    opt.textContent = model;
                    if (data.selected === model) {
                        opt.selected = true;
                    }
                    modelSelector.appendChild(opt);
                });
                
                modelSelectWrapper.style.display = 'flex';
            } else {
                modelSelectWrapper.style.display = 'none';
            }
        }
    } catch (e) {
        console.error('Failed to load models list:', e);
    }
}

// Send settings changes back to backend
async function handleThemeChange() {
    const selectedTheme = themeSelector.value;
    document.body.setAttribute('data-theme', selectedTheme);
    
    try {
        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ theme: selectedTheme })
        });
        
        appendSystemOutput(`Theme updated to: ${selectedTheme}`);
    } catch (e) {
        console.error('Failed to update theme:', e);
    }
}

// Send selected model changes back to backend
async function handleModelChange() {
    const selectedModel = modelSelector.value;
    
    try {
        const res = await fetch('/api/model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: selectedModel })
        });
        
        if (res.ok) {
            appendSystemOutput(`Active model set to: ${selectedModel || 'Default'}`);
        }
    } catch (e) {
        console.error('Failed to change model:', e);
    }
}

// Action button click (toggles between Send and Stop)
function handleAction() {
    if (isStreaming) {
        stopStreaming();
    } else {
        submitMessage();
    }
}

// Stop current response streaming
function stopStreaming() {
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }
}

// Formats LaTeX math block in elements
function renderLaTeX(element) {
    if (typeof renderMathInElement === 'function') {
        renderMathInElement(element, {
            delimiters: [
                {left: "$$", right: "$$", display: true},
                {left: "$", right: "$", display: false},
                {left: "\\(", right: "\\)", display: false},
                {left: "\\[", right: "\\]", display: true}
            ],
            throwOnError: false
        });
    }
}

// Parse markdown bold and inline links in text
function parseMarkdown(text) {
    // Escape HTML to prevent injection
    let escaped = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
        
    // Restore LaTeX backslash-parentheses delimiters from escaping so KaTeX matches them
    escaped = escaped.replace(/\\&lt;/g, '\\<').replace(/\\&gt;/g, '\\>');
    
    // Parse bold text: **text**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Parse links: [label](url)
    escaped = escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Parse DuckDuckGo divider lines
    escaped = escaped.replace(/---/g, '<div class="search-divider"></div>');
    
    return escaped;
}

// Append system information output directly in terminal
function appendSystemOutput(text) {
    const entry = document.createElement('div');
    entry.className = 'message-entry system-message';
    entry.innerHTML = `<p class="separator">--------------------------------------------------</p><p>ℹ️ ${text}</p><p class="separator">--------------------------------------------------</p>`;
    terminalScreen.appendChild(entry);
    scrollToBottom();
}

// Submit prompt to backend
async function submitMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    
    // Reset textbox height
    chatInput.value = '';
    chatInput.style.height = 'auto';
    
    // 1. Handle client-side commands
    if (text === '/clear') {
        clearTerminal();
        return;
    }
    
    // 2. Append User Prompt to terminal logs
    appendMessage('user', text);
    conversationHistory.push({ role: 'user', content: text });
    
    // 3. Create Placeholder AI Output block
    const aiEntry = createMessageBlock('ai');
    const contentText = aiEntry.querySelector('.message-content-text');
    const cursor = aiEntry.querySelector('.cursor-block');
    
    // Toggle action button to streaming status
    isStreaming = true;
    actionBtn.classList.add('streaming');
    actionBtn.setAttribute('aria-label', 'Stop generating');
    
    currentAbortController = new AbortController();
    let assistantResponse = '';
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: conversationHistory }),
            signal: currentAbortController.signal
        });
        
        if (!response.ok) {
            throw new Error(`Server returned code: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            assistantResponse += chunk;
            
            // Set HTML content to parse Markdown while preserving LaTeX tokens
            contentText.innerHTML = parseMarkdown(assistantResponse);
            scrollToBottom();
        }
        
        // Remove active cursor
        cursor.remove();
        
        // Final LaTeX render triggers on the completed message
        renderLaTeX(contentText);
        
        // Store full assistant reply
        conversationHistory.push({ role: 'assistant', content: assistantResponse });
        
    } catch (e) {
        if (e.name === 'AbortError') {
            // User aborted the request
            assistantResponse += ' [Interrupted by user]';
            contentText.innerHTML = parseMarkdown(assistantResponse);
            cursor.remove();
            
            // Store partial answer
            conversationHistory.push({ role: 'assistant', content: assistantResponse });
            appendSystemOutput("Inference stopped by user.");
        } else {
            // Real network/server error
            console.error('Fetch error:', e);
            contentText.innerHTML = `<span style="color:#ff5f56;">❌ Connection Error: Failed to generate response (${e.message})</span>`;
            cursor.remove();
        }
    } finally {
        isStreaming = false;
        currentAbortController = null;
        actionBtn.classList.remove('streaming');
        actionBtn.setAttribute('aria-label', 'Send message');
        scrollToBottom();
        chatInput.focus();
    }
}

// Create UI block elements
function appendMessage(role, text) {
    const entry = document.createElement('div');
    entry.className = 'message-entry';
    
    const isUser = role === 'user';
    const headerText = isUser ? 'user@signal:~$' : 'signal-ai:~$';
    const headerClass = isUser ? 'user' : 'ai';
    const prefix = isUser ? '👤 ' : '🤖 ';
    
    entry.innerHTML = `
        <div class="message-header ${headerClass}">${prefix}${headerText}</div>
        <div class="message-content">${parseMarkdown(text)}</div>
    `;
    
    terminalScreen.appendChild(entry);
    scrollToBottom();
}

function createMessageBlock(role) {
    const entry = document.createElement('div');
    entry.className = 'message-entry';
    
    const headerText = role === 'user' ? 'user@signal:~$' : 'signal-ai:~$';
    const headerClass = role === 'user' ? 'user' : 'ai';
    const prefix = role === 'user' ? '👤 ' : '🤖 ';
    
    entry.innerHTML = `
        <div class="message-header ${headerClass}">${prefix}${headerText}</div>
        <div class="message-content">
            <span class="message-content-text"></span><span class="cursor-block"></span>
        </div>
    `;
    
    terminalScreen.appendChild(entry);
    scrollToBottom();
    return entry;
}

// Clear Terminal logs
function clearTerminal() {
    // Keep only the first welcome message
    const welcome = terminalScreen.querySelector('.system-message');
    terminalScreen.innerHTML = '';
    if (welcome) {
        terminalScreen.appendChild(welcome);
    }
    conversationHistory = [];
    appendSystemOutput("Terminal logs cleared.");
}

// Auto-scroll screen
function scrollToBottom() {
    terminalScreen.scrollTop = terminalScreen.scrollHeight;
}
