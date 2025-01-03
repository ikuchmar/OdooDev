Если PyCharm не находит файлы или слова при использовании функции "Find in Files", возможно, это связано с проблемами
индексации или кеша. Переиндексирование проекта и очистка кеша может помочь решить эту проблему. Вот как это сделать:

# Переиндексирование проекта:

Закройте все открытые файлы в PyCharm, чтобы проект был чист.
На верхней панели выберите "Файл" (File) -> "Переиндексировать проект" (Invalidate Caches / Restart...).
В появившемся диалоговом окне нажмите на "Переиндексировать" (Invalidate and Restart).
После этого PyCharm начнет переиндексировать проект. Дождитесь завершения процесса, затем попробуйте выполнить поиск
снова.

# Очистка кеша:

Если переиндексирование проекта не помогло, вы можете попробовать очистить кеш PyCharm.
На верхней панели выберите "Файл" (File) -> "Очистить кеш" (Invalidate Caches...).
В появившемся диалоговом окне выберите опции, которые вы хотите очистить, например, "Кеш графа зависимостей", "Кеш
редактора" и т.д. Рекомендуется выбрать все опции.
Нажмите на "ОК".
После очистки кеша PyCharm перезапустится. После перезапуска попробуйте выполнить поиск снова.

Если после выполнения этих действий поиск все равно не находит файлы или слова, проверьте, что вы правильно указали
каталог для поиска, а также обратите внимание на параметры поиска, такие как регистрозависимость, использование
регулярных выражений и т.д.

Если проблема остается нерешенной, возможно, есть другие проблемы с вашим проектом или настройками PyCharm. В таком
случае, может быть полезным обратиться к документации PyCharm или сообществу для получения дополнительной помощи.