// Simple Signal Web CLI Client Logic

// Configuration & State
let conversationHistory = [];
let isStreaming = false;
let currentAbortController = null;
let activeSessionId = null; // null means unsaved new session
let sessions = []; // list of all saved sessions

// DOM Elements
const terminalContainer = document.querySelector('.terminal-container');
const terminalScreen = document.getElementById('terminal-screen');
const chatInput = document.getElementById('chat-input');
const actionBtn = document.getElementById('action-btn');
const themeSelector = document.getElementById('theme-selector');
const modelSelector = document.getElementById('model-selector');
const modelSelectWrapper = document.getElementById('model-select-wrapper');

// Mac Window Controls
const winCloseBtn = document.getElementById('win-close-btn');
const winMinimizeBtn = document.getElementById('win-minimize-btn');
const winMaximizeBtn = document.getElementById('win-maximize-btn');

// Sidebar Elements
const sidebar = document.getElementById('terminal-sidebar');
const sessionsList = document.getElementById('sessions-list');
const toggleHistoryBtn = document.getElementById('toggle-history-btn');
const closeSidebarBtn = document.getElementById('close-sidebar-btn');
const gpuInfoBtn = document.getElementById('gpu-info-btn');

// Initialize Web UI
document.addEventListener('DOMContentLoaded', async () => {
    await loadConfig();
    await loadModels();
    loadSessionsFromStorage();
    
    // Auto-focus input
    chatInput.focus();
    
    // Setup event listeners
    chatInput.addEventListener('input', autoResizeInput);
    chatInput.addEventListener('keydown', handleKeydown);
    actionBtn.addEventListener('click', handleAction);
    themeSelector.addEventListener('change', handleThemeChange);
    modelSelector.addEventListener('change', handleModelChange);
    
    // Window control buttons listeners
    winCloseBtn.addEventListener('click', handleWindowClose);
    winMinimizeBtn.addEventListener('click', handleWindowMinimize);
    winMaximizeBtn.addEventListener('click', handleWindowMaximize);
    
    // Sidebar toggle buttons
    toggleHistoryBtn.addEventListener('click', toggleSidebar);
    closeSidebarBtn.addEventListener('click', collapseSidebar);
    
    // GPU Info button
    gpuInfoBtn.addEventListener('click', handleGpuQuery);
    
    // Clicking anywhere in the terminal screen focuses the text input (CLI feel)
    terminalScreen.addEventListener('click', (e) => {
        // Do not focus if they clicked a link or selectable elements
        if (e.target.tagName !== 'A' && !window.getSelection().toString()) {
            chatInput.focus();
        }
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

// Formats LaTeX math block in elements using MathJax
function renderLaTeX(element) {
    if (window.MathJax && window.MathJax.typesetPromise) {
        MathJax.typesetPromise([element]).catch(err => console.error('MathJax error:', err));
    }
}

// Check if string contains LaTeX delimiters
function hasLaTeX(text) {
    return text.includes('$') || text.includes('\\(') || text.includes('\\[') || text.includes('\\begin{');
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
        
    // Restore LaTeX backslash-parentheses delimiters from escaping so MathJax matches them
    escaped = escaped.replace(/\\&lt;/g, '\\<').replace(/\\&gt;/g, '\\>');
    
    // Parse bold text: **text**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Parse links: [label](url)
    escaped = escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Parse DuckDuckGo divider lines
    escaped = escaped.replace(/---/g, '<div class="search-divider"></div>');
    
    return escaped;
}

// Format paragraph-separated message body
function formatMessageBody(text) {
    return text.split('\n\n').map(blockText => {
        if (!blockText.trim()) return '';
        return `<p class="msg-block">${parseMarkdown(blockText)}</p>`;
    }).filter(Boolean).join('');
}

// Optimized block-level update helper that scales linearly (O(1) updates)
function updateMessageContent(container, text, isFinal = false, shouldTypeset = true) {
    const rawBlocks = text.split('\n\n');
    let childNodes = container.querySelectorAll('.msg-block');
    
    // Adjust number of child nodes to match rawBlocks length
    while (childNodes.length < rawBlocks.length) {
        const newBlock = document.createElement('p');
        newBlock.className = 'msg-block active';
        container.appendChild(newBlock);
        childNodes = container.querySelectorAll('.msg-block');
    }
    
    // Update each block's content
    for (let i = 0; i < rawBlocks.length; i++) {
        const blockText = rawBlocks[i];
        const blockNode = childNodes[i];
        const isLast = (i === rawBlocks.length - 1);
        
        // If it's not the last block and it's marked active, it means it just completed
        if (!isLast && blockNode.classList.contains('active')) {
            blockNode.classList.remove('active');
            blockNode.innerHTML = parseMarkdown(blockText);
            if (hasLaTeX(blockText)) {
                renderLaTeX(blockNode);
            }
        } else if (isLast) {
            const parsedContent = parseMarkdown(blockText);
            const cursorHtml = isFinal ? '' : '<span class="cursor-block"></span>';
            const targetHtml = `${parsedContent}${cursorHtml}`;
            
            if (blockNode.innerHTML !== targetHtml) {
                blockNode.innerHTML = targetHtml;
                
                if (isFinal) {
                    blockNode.classList.remove('active');
                    if (hasLaTeX(blockText)) {
                        renderLaTeX(blockNode);
                    }
                } else if (shouldTypeset && hasLaTeX(blockText)) {
                    renderLaTeX(blockNode);
                }
            }
        }
    }
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
    
    // If it's the first message of a session, check if we need to initialize active session
    if (conversationHistory.length === 0) {
        createNewSessionOnFirstMsg(text);
    }
    
    // 2. Append User Prompt to terminal logs
    appendMessage('user', text);
    conversationHistory.push({ role: 'user', content: text });
    
    // Save updated history in storage
    saveActiveSessionToStorage();
    
    // 3. Create Placeholder AI Output block
    const aiEntry = createMessageBlock('ai');
    const contentText = aiEntry.querySelector('.message-content-text');
    const statsEl = aiEntry.querySelector('.generation-stats');
    
    // Toggle action button to streaming status
    isStreaming = true;
    actionBtn.classList.add('streaming');
    actionBtn.setAttribute('aria-label', 'Stop generating');
    
    currentAbortController = new AbortController();
    let assistantResponse = '';
    let chunkCount = 0;
    let streamStartTime = null;
    
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
        
        let lastTypesetTime = 0;
        const TYPESET_THROTTLE_MS = 200; // Render at most once every 200ms during streaming
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            
            if (!streamStartTime && chunk.trim()) {
                streamStartTime = Date.now();
            }
            if (chunk.trim()) {
                chunkCount++;
            }
            
            assistantResponse += chunk;
            
            // Throttle MathJax rendering to keep streaming fast and smooth
            const now = Date.now();
            const shouldTypeset = (now - lastTypesetTime > TYPESET_THROTTLE_MS);
            
            updateMessageContent(contentText, assistantResponse, false, shouldTypeset);
            
            if (shouldTypeset) {
                lastTypesetTime = now;
            }
            
            // Show stats in real-time
            if (streamStartTime) {
                const elapsed = (Date.now() - streamStartTime) / 1000;
                const tokPerSec = elapsed > 0 ? (chunkCount / elapsed).toFixed(1) : 0;
                statsEl.style.display = 'flex';
                statsEl.innerHTML = `<span>⏳ Time: ${elapsed.toFixed(1)}s</span><span>⚡ Speed: ${tokPerSec} tok/s</span><span>🪙 Tokens: ${chunkCount}</span>`;
            }
            
            scrollToBottom();
        }
        
        // Final update to clear active class and cursor
        updateMessageContent(contentText, assistantResponse, true);
        
        // Update stats with final metrics
        if (streamStartTime) {
            const elapsed = (Date.now() - streamStartTime) / 1000;
            const tokPerSec = elapsed > 0 ? (chunkCount / elapsed).toFixed(1) : 0;
            statsEl.style.display = 'flex';
            statsEl.innerHTML = `<span>⏳ Time: ${elapsed.toFixed(1)}s</span><span>⚡ Speed: ${tokPerSec} tok/s</span><span>🪙 Tokens: ${chunkCount}</span>`;
        }
        
        // Store full assistant reply
        conversationHistory.push({ role: 'assistant', content: assistantResponse });
        
        // Save again
        saveActiveSessionToStorage();
        
    } catch (e) {
        if (e.name === 'AbortError') {
            // User aborted the request
            assistantResponse += ' [Interrupted by user]';
            updateMessageContent(contentText, assistantResponse, true);
            
            if (streamStartTime) {
                const elapsed = (Date.now() - streamStartTime) / 1000;
                const tokPerSec = elapsed > 0 ? (chunkCount / elapsed).toFixed(1) : 0;
                statsEl.style.display = 'flex';
                statsEl.innerHTML = `<span>⏳ Time: ${elapsed.toFixed(1)}s</span><span>⚡ Speed: ${tokPerSec} tok/s</span><span>🪙 Tokens: ${chunkCount} (Interrupted)</span>`;
            }
            
            // Store partial answer
            conversationHistory.push({ role: 'assistant', content: assistantResponse });
            saveActiveSessionToStorage();
            appendSystemOutput("Inference stopped by user.");
        } else {
            // Real network/server error
            console.error('Fetch error:', e);
            const errorBlock = document.createElement('p');
            errorBlock.className = 'msg-block';
            errorBlock.innerHTML = `<span style="color:#ff5f56;">❌ Connection Error: Failed to generate response (${e.message})</span>`;
            contentText.appendChild(errorBlock);
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
    
    const contentHtml = isUser ? parseMarkdown(text) : formatMessageBody(text);
    
    entry.innerHTML = `
        <div class="message-header ${headerClass}">${prefix}${headerText}</div>
        <div class="message-content">${contentHtml}</div>
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
            <div class="message-content-text"></div>
        </div>
        <div class="generation-stats" style="display: none;"></div>
    `;
    
    terminalScreen.appendChild(entry);
    scrollToBottom();
    return entry;
}

// Clear Terminal logs (soft-clear client-side)
function clearTerminal() {
    // Keep only the first welcome message
    const welcome = terminalScreen.querySelector('.system-message');
    terminalScreen.innerHTML = '';
    if (welcome) {
        terminalScreen.appendChild(welcome);
    }
    conversationHistory = [];
    if (activeSessionId) {
        saveActiveSessionToStorage();
    }
    appendSystemOutput("Terminal logs cleared.");
}

// Auto-scroll screen
function scrollToBottom() {
    terminalScreen.scrollTop = terminalScreen.scrollHeight;
}


/* ==========================================
   SESSION HISTORY / LOCAL STORAGE SYNCING
   ========================================== */

// Load all sessions from localStorage on load
function loadSessionsFromStorage() {
    const saved = localStorage.getItem('simple_signal_sessions');
    if (saved) {
        try {
            sessions = JSON.parse(saved);
        } catch (e) {
            console.error('Failed to parse sessions:', e);
            sessions = [];
        }
    } else {
        sessions = [];
    }
    updateSidebarUI();
}

// Save active sessions list to localStorage
function saveSessionsToStorage() {
    localStorage.setItem('simple_signal_sessions', JSON.stringify(sessions));
    updateSidebarUI();
}

// Create a new session automatically on the first user input message
function createNewSessionOnFirstMsg(firstMsgText) {
    activeSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // Use first 25 characters as title
    let title = firstMsgText;
    if (title.startsWith('/search ')) {
        title = title.substring(8);
    }
    if (title.length > 25) {
        title = title.substring(0, 22) + '...';
    }
    
    const newSession = {
        id: activeSessionId,
        title: title,
        messages: [],
        timestamp: Date.now()
    };
    
    sessions.unshift(newSession); // Add to the top
    saveSessionsToStorage();
}

// Save the active session's conversation history
function saveActiveSessionToStorage() {
    if (!activeSessionId) return;
    
    const idx = sessions.findIndex(s => s.id === activeSessionId);
    if (idx !== -1) {
        sessions[idx].messages = [...conversationHistory];
        sessions[idx].timestamp = Date.now();
        saveSessionsToStorage();
    }
}

// Update the history sidebar interface list
function updateSidebarUI() {
    sessionsList.innerHTML = '';
    
    if (sessions.length === 0) {
        sessionsList.innerHTML = '<div class="empty-history">No saved sessions</div>';
        return;
    }
    
    sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = 'session-item';
        if (session.id === activeSessionId) {
            item.classList.add('active');
        }
        
        // Load click action
        item.addEventListener('click', (e) => {
            // Prevent trigger if they click the delete button
            if (e.target.closest('.delete-session-btn')) return;
            loadSession(session.id);
        });
        
        // Session text title
        const titleEl = document.createElement('span');
        titleEl.className = 'session-title';
        titleEl.textContent = session.title;
        titleEl.title = session.title;
        item.appendChild(titleEl);
        
        // Delete button
        const delBtn = document.createElement('button');
        delBtn.className = 'delete-session-btn';
        delBtn.innerHTML = '&times;';
        delBtn.title = 'Delete Session';
        delBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteSession(session.id);
        });
        item.appendChild(delBtn);
        
        sessionsList.appendChild(item);
    });
}

// Load a session from the history
function loadSession(sessionId) {
    if (isStreaming) {
        stopStreaming();
    }
    
    const session = sessions.find(s => s.id === sessionId);
    if (!session) return;
    
    activeSessionId = sessionId;
    conversationHistory = [...session.messages];
    
    // Clear terminal screen and restore message history
    const welcome = terminalScreen.querySelector('.system-message');
    terminalScreen.innerHTML = '';
    if (welcome) {
        terminalScreen.appendChild(welcome);
    }
    
    // Re-render each message
    conversationHistory.forEach(msg => {
        appendMessage(msg.role, msg.content);
    });
    
    // Apply LaTeX math formatting to all rendered content
    const contents = terminalScreen.querySelectorAll('.message-content');
    contents.forEach(content => {
        renderLaTeX(content);
    });
    
    updateSidebarUI();
    appendSystemOutput(`Loaded session: "${session.title}"`);
    chatInput.focus();
}

// Delete a session from history
function deleteSession(sessionId) {
    const confirmDelete = confirm("Are you sure you want to delete this session from history?");
    if (!confirmDelete) return;
    
    sessions = sessions.filter(s => s.id !== sessionId);
    saveSessionsToStorage();
    
    // If the active session was deleted, start a new chat
    if (activeSessionId === sessionId) {
        startNewChatSession();
    }
}

// Initialize a new empty session
function startNewChatSession() {
    if (isStreaming) {
        stopStreaming();
    }
    
    activeSessionId = null;
    conversationHistory = [];
    
    // Clear screen to welcome
    const welcome = terminalScreen.querySelector('.system-message');
    terminalScreen.innerHTML = '';
    if (welcome) {
        terminalScreen.appendChild(welcome);
    }
    
    updateSidebarUI();
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatInput.focus();
}


/* ==========================================
   WINDOW CONTROL BUTTON ACTIONS
   ========================================== */

// 1. Exit Button (Red): Starts a new chat and deletes/clears it from history
function handleWindowClose() {
    if (isStreaming) {
        stopStreaming();
    }
    
    const confirmExit = confirm("Exit session? This will delete the active chat history.");
    if (!confirmExit) return;
    
    if (activeSessionId) {
        sessions = sessions.filter(s => s.id !== activeSessionId);
        saveSessionsToStorage();
        activeSessionId = null;
    }
    
    conversationHistory = [];
    
    // Clear screen to welcome
    const welcome = terminalScreen.querySelector('.system-message');
    terminalScreen.innerHTML = '';
    if (welcome) {
        terminalScreen.appendChild(welcome);
    }
    
    updateSidebarUI();
    appendSystemOutput("Active session deleted. Started a new clean chat.");
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatInput.focus();
}

// 2. Minimize Button (Yellow): Archives current chat into history list and starts new chat
function handleWindowMinimize() {
    if (isStreaming) {
        stopStreaming();
    }
    
    if (conversationHistory.length > 0) {
        // If it was unsaved, create the active session object
        if (!activeSessionId) {
            createNewSessionOnFirstMsg(conversationHistory[0].content);
        }
        // Save the latest conversation history state
        saveActiveSessionToStorage();
        
        appendSystemOutput(`Session archived in History.`);
    } else {
        appendSystemOutput("No messages to archive. Starting new chat.");
    }
    
    // Start new chat session
    startNewChatSession();
    
    // Expand sidebar so they can see the archived chat in the history list
    expandSidebar();
}

// 3. Widen Button (Green): Toggles Fullscreen window scaling
function handleWindowMaximize() {
    terminalContainer.classList.toggle('fullscreen');
    
    // Adjust layout scroll position slightly after resizing
    setTimeout(scrollToBottom, 150);
}


/* ==========================================
   SIDEBAR DRAWER TOGGLE FUNCTIONS
   ========================================== */

function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
}

function collapseSidebar() {
    sidebar.classList.add('collapsed');
}

function expandSidebar() {
    sidebar.classList.remove('collapsed');
}

// 4. GPU Information Command Trigger
function handleGpuQuery() {
    if (isStreaming) return;
    chatInput.value = '/gpu';
    submitMessage();
}
