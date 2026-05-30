const { contextBridge } = require('electron');

const BASE_URL = 'http://127.0.0.1:8000';

contextBridge.exposeInMainWorld('SimpleSignal', {
    /**
     * Get real-time system telemetry (CPU, Memory, GPU, Storage)
     * @returns {Promise<Object>} Telemetry data
     */
    getTelemetry: async () => {
        try {
            const res = await fetch(`${BASE_URL}/api/system/status`);
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return await res.json();
        } catch (error) {
            console.error('[SimpleSignal SDK] getTelemetry failed:', error);
            throw error;
        }
    },

    /**
     * Send a chat request to the AI Engine.
     * Note: This returns the full text after completion. For streaming, you'd need a custom fetch.
     * @param {Array<{role: string, content: string}>} messages 
     * @returns {Promise<string>} The AI's response text
     */
    chat: async (messages) => {
        try {
            const res = await fetch(`${BASE_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages })
            });
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            
            // Read the streamed response into a single string for simple SDK usage
            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let fullText = '';
            
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                fullText += decoder.decode(value, { stream: true });
            }
            
            return fullText;
        } catch (error) {
            console.error('[SimpleSignal SDK] chat failed:', error);
            throw error;
        }
    },

    /**
     * Perform a web search using Simple Signal's DuckDuckGo integration
     * @param {string} query 
     * @returns {Promise<string>} The formatted search results
     */
    search: async (query) => {
        try {
            // The /api/chat endpoint accepts "/search <query>" as a special command
            const messages = [{ role: 'user', content: `/search ${query}` }];
            const res = await fetch(`${BASE_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages })
            });
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            
            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let fullText = '';
            
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                fullText += decoder.decode(value, { stream: true });
            }
            
            return fullText;
        } catch (error) {
            console.error('[SimpleSignal SDK] search failed:', error);
            throw error;
        }
    }
});
