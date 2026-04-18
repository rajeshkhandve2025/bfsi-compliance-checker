/* BFSI Advisory Chatbot — frontend logic */

// Conversation history sent to the backend with every request
let history = [];
let isStreaming = false;

// Configure marked for safe HTML rendering
marked.setOptions({ breaks: true, gfm: true });

// ── Send a message ────────────────────────────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (!text || isStreaming) return;

  input.value = '';
  input.style.height = 'auto';
  setStreaming(true);

  appendMessage('user', text);
  history.push({ role: 'user', content: text });

  // Placeholder for the assistant reply (tool badges + streaming text go here)
  const assistantBubble = appendMessage('assistant', '');
  const bubble = assistantBubble.querySelector('.bubble');
  bubble.innerHTML = typingIndicator();

  let accumulatedText = '';
  let toolBadgesHtml = '';

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history }),
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line for next iteration

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();
        if (!payload) continue;

        let event;
        try { event = JSON.parse(payload); } catch { continue; }

        if (event.type === 'tool_call') {
          toolBadgesHtml += `<div class="tool-badge">${event.display}</div>`;
          bubble.innerHTML = toolBadgesHtml + typingIndicator();
          scrollToBottom();

        } else if (event.type === 'text') {
          accumulatedText += event.text;
          bubble.innerHTML = toolBadgesHtml + marked.parse(accumulatedText);
          scrollToBottom();

        } else if (event.type === 'done') {
          bubble.innerHTML = toolBadgesHtml + marked.parse(accumulatedText);
          history.push({ role: 'assistant', content: accumulatedText });
          scrollToBottom();

        } else if (event.type === 'error') {
          bubble.innerHTML = `<span style="color:#dc2626">⚠️ ${event.message}</span>`;
          scrollToBottom();
        }
      }
    }

  } catch (err) {
    bubble.innerHTML = `<span style="color:#dc2626">⚠️ Connection error: ${err.message}</span>`;
  } finally {
    setStreaming(false);
    input.focus();
  }
}

// ── Ask a quick question from the sidebar ────────────────────────────────────
function ask(text) {
  const input = document.getElementById('user-input');
  input.value = text;
  autoResize(input);
  sendMessage();
}

// ── Start a new chat ──────────────────────────────────────────────────────────
function newChat() {
  history = [];
  const messages = document.getElementById('messages');
  messages.innerHTML = '';
  appendMessage('assistant',
    '**New conversation started.** How can I help you?\n\n' +
    'Ask me about Mutual Funds, Insurance, IPO, Stocks, Tax, or Compliance.'
  );
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function appendMessage(role, text) {
  const messages = document.getElementById('messages');

  const msg = document.createElement('div');
  msg.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? 'You' : 'AI';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = text ? marked.parse(text) : '';

  msg.appendChild(avatar);
  msg.appendChild(bubble);
  messages.appendChild(msg);
  scrollToBottom();
  return msg;
}

function typingIndicator() {
  return '<div class="typing"><span></span><span></span><span></span></div>';
}

function scrollToBottom() {
  const messages = document.getElementById('messages');
  messages.scrollTop = messages.scrollHeight;
}

function setStreaming(active) {
  isStreaming = active;
  const btn = document.getElementById('send-btn');
  const input = document.getElementById('user-input');
  btn.disabled = active;
  input.disabled = active;
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function handleKey(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}
