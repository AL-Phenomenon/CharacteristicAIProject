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
        isCreator: false,
        creatorName: '',
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

    const authBtn = $('#auth-btn');
    const authModal = $('#auth-modal');
    const authClose = $('#auth-modal-close');
    const authCancel = $('#auth-cancel');
    const authSubmit = $('#auth-submit');
    const authPassword = $('#auth-password');
    const authMessage = $('#auth-message');

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

        // Auth Events
        if (authBtn) {
            authBtn.addEventListener('click', showAuthModal);
            authClose.addEventListener('click', hideAuthModal);
            authCancel.addEventListener('click', hideAuthModal);
            authSubmit.addEventListener('click', handleAuth);
            authPassword.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') handleAuth();
            });
        }
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

            // Check if creator auth is enabled
            if (data.has_creator_auth && authBtn) {
                authBtn.style.display = 'inline-flex';
            }

            showConnectionOk();
        } catch (err) {
            console.error('Character info fetch failed:', err);
            showConnectionError();
        }
    }

    async function sendMessage(message) {
        try {
            // 1. タスクを送信してIDを取得
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    user_id: state.userId,
                    is_creator: state.isCreator
                })
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const submitData = await res.json();
            const taskId = submitData.task_id;
            
            // 2. 結果が出るまで数秒おきにポーリング
            while (true) {
                // 3秒待つ
                await new Promise(resolve => setTimeout(resolve, 3000));
                
                try {
                    const statusRes = await fetch(`/api/chat/status/${taskId}`);
                    if (!statusRes.ok) continue; // エラーでもリトライ
                    
                    const statusData = await statusRes.json();
                    
                    if (statusData.status === 'completed' || statusData.status === 'error') {
                        showConnectionOk();
                        return statusData; // responseが含まれている
                    }
                    // processingの場合はループ継続
                } catch (e) {
                    // ネットワーク切れなどのエラーでも無視してリトライし続ける
                    console.warn("Polling network error, retrying...", e);
                }
            }
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

    async function authenticateCreator(password) {
        try {
            const res = await fetch('/api/auth', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });
            return await res.json();
        } catch (err) {
            console.error('Auth API error:', err);
            throw err;
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

    function showAuthModal() {
        if (state.isCreator) {
            alert(`すでに制作者「${state.creatorName}」としてログインしています。`);
            return;
        }
        authPassword.value = '';
        authMessage.textContent = '';
        authMessage.className = 'modal__message';
        authModal.style.display = 'flex';
        setTimeout(() => authPassword.focus(), 100);
    }

    function hideAuthModal() {
        authModal.style.display = 'none';
    }

    async function handleAuth() {
        const password = authPassword.value;
        if (!password) return;

        authSubmit.disabled = true;
        authMessage.textContent = '認証中...';
        authMessage.className = 'modal__message';

        try {
            const data = await authenticateCreator(password);
            if (data.success) {
                authMessage.textContent = data.message;
                authMessage.className = 'modal__message success';
                state.isCreator = true;
                state.creatorName = data.creator_name;
                
                // Update UI
                authBtn.innerHTML = '👑 <span>制作者</span>';
                authBtn.classList.add('active');
                authBtn.style.color = '#00b894';
                authBtn.style.borderColor = '#00b894';

                setTimeout(hideAuthModal, 1500);
            } else {
                authMessage.textContent = data.message;
                authMessage.className = 'modal__message error';
                authSubmit.disabled = false;
            }
        } catch (err) {
            authMessage.textContent = 'エラーが発生しました';
            authMessage.className = 'modal__message error';
            authSubmit.disabled = false;
        }
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
