const ru = {
  common: {
    abbAssistant: 'ABB Ассистент',
    poweredBy: 'Разработано банком ABB',
  },
  upload: {
    title: 'Добро пожаловать в ABB Ассистент',
    subtitle: 'Загрузите файл корпуса ABB, чтобы задавать вопросы о банке ABB.',
    dropHere: 'Перетащите corpus.json сюда',
    orClick: 'или нажмите для выбора файла',
    validating: 'Проверка корпуса…',
    uploading: 'Сохранение корпуса…',
    startIndexing: 'Начать индексацию',
    indexing: 'Индексация документов…',
    ready: 'Корпус проиндексирован и готов!',
    goToChat: 'Открыть чат',
    reUpload: 'Загрузить новый корпус',
    invalidFormat: 'Неверный формат корпуса. Пожалуйста, загрузите корректный файл corpus.json.',
    documents: '{{count}} документов',
    progress: '{{processed}} / {{total}} документов проиндексировано',
    failed: 'Индексация не удалась. Пожалуйста, попробуйте ещё раз.',
    tryAgain: 'Попробовать снова',
    errorDetail: 'Ошибка: {{message}}',
    alreadyReady: 'Корпус уже проиндексирован.',
  },
  chat: {
    placeholder: 'Задайте любой вопрос о банке ABB…',
    send: 'Отправить',
    newChat: 'Новый чат',
    thinking: 'ABB Ассистент думает…',
    citations: 'Источники',
    suggestedTitle: 'Попробуйте спросить:',
    error: 'Что-то пошло не так. Пожалуйста, попробуйте ещё раз.',
    suggested: [
      'Каковы основные услуги банка ABB?',
      'Как открыть счёт в банке ABB?',
      'Какие кредитные продукты предлагает ABB?',
      'Какие карты предлагает банк ABB?',
      'Как связаться с банком ABB?',
    ],
  },
  nav: {
    upload: 'Загрузить',
    chat: 'Чат',
    dashboard: 'Панель',
  },
} as const;

export default ru;
