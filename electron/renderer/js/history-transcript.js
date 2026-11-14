// Saved participant speech is independent of AI conversation messages.
(() => {
  const controls = document.getElementById('historyConversationViews')
  const transcript = document.getElementById('historyParticipantTranscript')
  const chat = document.getElementById('chatArea')
  const speechButton = document.getElementById('historyTranscriptButton')
  const answersButton = document.getElementById('historyAnswersButton')
  const select = speech => {
    transcript.hidden = !speech
    chat.hidden = speech
    speechButton.setAttribute('aria-pressed', String(speech))
    answersButton.setAttribute('aria-pressed', String(!speech))
  }
  speechButton.addEventListener('click', () => select(true))
  answersButton.addEventListener('click', () => select(false))
  window.clearHistoryTranscriptView = () => { controls.hidden = true; select(false) }
  window.renderHistoryTranscript = conversation => {
    transcript.replaceChildren()
    const context = new window.UnifiedSessionContext()
    context.restore(conversation.liveContext)
    const append = (label, text) => {
      const entry = document.createElement('article')
      const source = document.createElement('strong')
      source.textContent = label
      const content = document.createElement('p')
      content.textContent = text
      entry.append(source,content); transcript.append(entry)
    }
    for (const episode of context.episodes.filter(e => !context.transcript.length || e.end < context.transcript[0].at)) {
      append('Earlier participant speech excerpt', episode.text)
    }
    for (const turn of context.transcript) {
      append(turn.source === 'remote' ? 'Remote audio' : 'Microphone', turn.text)
    }
    if (!transcript.childElementCount) append('Transcript unavailable', 'No participant speech was saved for this conversation.')
    const note = document.createElement('p')
    note.className = 'history-transcript-note'
    note.textContent = 'Labels show the audio source, not a verified speaker identity. AI responses are excluded.'
    transcript.prepend(note)
    controls.hidden = false
    select(true)
  }
  window.showHistoryAnswers = () => { if (!controls.hidden) select(false) }
})()
