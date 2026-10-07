// Visibility and native sizing are independent of recording and generation.
(() => {
  const button = document.getElementById('conversationToggle')
  const panel = document.getElementById('conversationPanel')
  const chat = document.getElementById('chatArea')
  if (!button || !panel) return
  let collapsed = false
  let hadConversation = !!chat?.querySelector('.chat-message')
  let transition = Promise.resolve()
  const settings = document.getElementById('settingsPanel')
  const history = document.getElementById('historyPanel')
  function syncWindowSize() {
    const shrink = collapsed && !settings?.classList.contains('open') && !history?.classList.contains('open')
    const height = Math.ceil(button.getBoundingClientRect().bottom + 32)
    transition = transition.then(() => window.api?.setConversationCollapsed?.(shrink, height)).catch(() => {
      button.title = 'Conversation visibility changed; window resizing is unavailable.'
    })
  }
  if (settings) new MutationObserver(syncWindowSize).observe(settings, {attributes:true, attributeFilter:['class']})
  if (history) new MutationObserver(syncWindowSize).observe(history, {attributes:true, attributeFilter:['class']})
  document.addEventListener('ant:conversation-opened', () => setCollapsed(false))
  function setCollapsed(next) {
    collapsed = next
    panel.hidden = next
    document.body.classList.toggle('conversation-collapsed', next)
    button.textContent = next ? 'Show conversation' : 'Hide conversation'
    button.setAttribute('aria-expanded', String(!next))
    syncWindowSize()
  }
  button.addEventListener('click', () => setCollapsed(!collapsed))
  if (chat) {
    setCollapsed(!hadConversation)
    new MutationObserver(() => {
      const hasConversation = !!chat.querySelector('.chat-message')
      if (hasConversation !== hadConversation) {
        hadConversation = hasConversation
        setCollapsed(!hasConversation)
      }
    }).observe(chat, {childList:true})
  }
})()
