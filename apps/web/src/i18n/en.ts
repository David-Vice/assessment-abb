const en = {
  common: {
    abbAssistant: 'ABB Assistant',
    poweredBy: 'Powered by ABB Bank',
  },
  upload: {
    title: 'Welcome to ABB Assistant',
    subtitle: 'Upload the ABB corpus file to start asking questions about ABB Bank.',
    dropHere: 'Drop corpus.json here',
    orClick: 'or click to browse',
    validating: 'Validating corpus…',
    uploading: 'Saving corpus…',
    startIndexing: 'Start Indexing',
    indexing: 'Indexing documents…',
    ready: 'Corpus indexed and ready!',
    goToChat: 'Open Chat',
    reUpload: 'Upload new corpus',
    invalidFormat: 'Invalid corpus format. Please upload a valid corpus.json file.',
    documents: '{{count}} documents',
    progress: '{{processed}} / {{total}} documents indexed',
    failed: 'Indexing failed. Please try again.',
    tryAgain: 'Try again',
    errorDetail: 'Error: {{message}}',
    alreadyReady: 'Corpus already indexed.',
  },
  chat: {
    placeholder: 'Ask anything about ABB Bank…',
    send: 'Send',
    newChat: 'New chat',
    thinking: 'ABB Assistant is thinking…',
    citations: 'Sources',
    suggestedTitle: 'Try asking:',
    error: 'Something went wrong. Please try again.',
    suggested: [
      "What are ABB Bank's main services?",
      'How do I open an account at ABB Bank?',
      'What loan products does ABB offer?',
      'What cards does ABB Bank offer?',
      'How do I contact ABB Bank?',
    ],
  },
  nav: {
    upload: 'Upload',
    chat: 'Chat',
    dashboard: 'Dashboard',
  },
} as const;

export default en;
