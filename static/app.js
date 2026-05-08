/**
 * HARKA Web Chat - Application Logic
 */

(function () {
    'use strict';

    // --- State ---
    const state = {
        characterName: 'AI',
        characterInitial: 'A',
        userId: generateUserId(),
        isProcessing: false,
    };

    // --- DOM Elements ---
    const $ = (sel) => document.querySelector(sel);
    const chatContainer = $('#chat-container');
    const chatArea = $('#chat-area');
    const messageInput = $('#message-input');
    const sendBtn = $('#send-btn');
    const clearBtn = $('#clear-btn');
    const typingIndicator = $('#typing-indicator');
    const headerName = $('#header-name');
    const headerAvatar = $('#header-avatar');
    const typingAvatar = $('#typing-avatar');
    const userIdDisplay = $('#user-id-display');
    const connectionBanner = $('#connection-banner');

    // --- Init ---
    async function init() {
        userIdDisplay.textContent = state.userId;
        bindEvents();
        await fetchCharacterInfo();
        messageInput.focus();
    }

    // --- Events ---
    function bindEvents() {
        sendBtn.addEventListener('click', handleSend);

        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        });

        // Auto-resize textarea
        messageInput.addEventListener('input', () => {
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 140) + 'px';
        });

        clearBtn.addEventListener('click', handleClear);
    }

    // --- API ---
    async function fetchCharacterInfo() {
        try {
            const res = await fetch('/api/character');
            if (!res.ok) throw new Error('Failed to fetch character info');
            const data = await res.json();
            state.characterName = data.name || 'AI';
            state.characterInitial = state.characterName.charAt(0).toUpperCase();
            headerName.textContent = state.characterName;
            headerAvatar.textContent = state.characterInitial;
            typingAvatar.textContent = state.characterInitial;
            document.title = `${state.characterName} - Web Chat`;

            // Update welcome
            const welcomeTitle = $('#welcome-title');
            const welcomeIcon = $('#welcome-icon');
            if (welcomeTitle) welcomeTitle.textContent = `${state.characterName} へようこそ`;
            if (welcomeIcon) welcomeIcon.textContent = state.characterInitial;

            showConnectionOk();
        } catch (err) {
            console.error('Character info fetch failed:', err);
            showConnectionError();
        }
    }

    async function sendMessage(message) {
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    user_id: state.userId
                })
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const data = await res.json();
            showConnectionOk();
            return data;
        } catch (err) {
            console.error('Chat API error:', err);
            showConnectionError();
            throw err;
        }
    }

    async function clearMemory() {
        try {
            await fetch('/api/clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: state.userId })
            });
        } catch (err) {
            console.error('Clear API error:', err);
        }
    }

    // --- Handlers ---
    async function handleSend() {
        if (state.isProcessing) return;

        const message = messageInput.value.trim();
        if (!message) return;

        // Clear input
        messageInput.value = '';
        messageInput.style.height = 'auto';

        // Remove welcome if present
        removeWelcome();

        // Show user message
        appendMessage('user', message);

        // Show typing
        state.isProcessing = true;
        sendBtn.disabled = true;
        showTyping();

        try {
            const data = await sendMessage(message);
            hideTyping();
            appendMessage('assistant', data.response);
        } catch (err) {
            hideTyping();
            appendMessage('assistant', 'エラーが発生しました。サーバーとの接続を確認してください。');
        } finally {
            state.isProcessing = false;
            sendBtn.disabled = false;
            messageInput.focus();
        }
    }

    async function handleClear() {
        if (state.isProcessing) return;

        await clearMemory();

        // Clear chat display
        chatContainer.innerHTML = '';
        showWelcome();
    }

    // --- UI Helpers ---
    function appendMessage(role, content) {
        const isUser = role === 'user';
        const time = new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });

        const messageEl = document.createElement('div');
        messageEl.className = `message message--${role}`;

        const avatarText = isUser ? '👤' : state.characterInitial;

        messageEl.innerHTML = `
            <div class="message__avatar">${avatarText}</div>
            <div class="message__content">
                <div class="message__bubble">${escapeHtml(content)}</div>
                <span class="message__time">${time}</span>
            </div>
        `;

        chatContainer.appendChild(messageEl);
        scrollToBottom();
    }

    function showTyping() {
        typingIndicator.classList.add('active');
        scrollToBottom();
    }

    function hideTyping() {
        typingIndicator.classList.remove('active');
    }

    function showWelcome() {
        const welcome = document.createElement('div');
        welcome.className = 'welcome';
        welcome.id = 'welcome';
        welcome.innerHTML = `
            <div class="welcome__icon" id="welcome-icon">${state.characterInitial}</div>
            <h2 class="welcome__title" id="welcome-title">${state.characterName} へようこそ</h2>
            <p class="welcome__subtitle">メッセージを送って会話を始めましょう。<br>記憶システムにより、あなたとの会話を覚えています。</p>
        `;
        chatContainer.appendChild(welcome);
    }

    function removeWelcome() {
        const welcome = $('#welcome');
        if (welcome) welcome.remove();
    }

    function showConnectionError() {
        connectionBanner.classList.add('visible');
    }

    function showConnectionOk() {
        connectionBanner.classList.remove('visible');
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatArea.scrollTop = chatArea.scrollHeight;
        });
    }

    // --- Utils ---
    function generateUserId() {
        let id = localStorage.getItem('harka_user_id');
        if (!id) {
            id = 'web_' + Math.random().toString(36).substring(2, 10);
            localStorage.setItem('harka_user_id', id);
        }
        return id;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // --- Start ---
    document.addEventListener('DOMContentLoaded', init);
})();
