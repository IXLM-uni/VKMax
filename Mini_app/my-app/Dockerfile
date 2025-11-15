# Руководство к файлу (Mini_app/my-app/Dockerfile)
# Назначение:
# - Сборка контейнера фронта VKMax (Next.js Mini_app).
# - Подходит для production/dev-запуска вместе с backend через docker-compose.
# - Ожидает переменную NEXT_PUBLIC_API_URL для доступа к API.

FROM node:20-alpine

# Рабочая директория внутри контейнера
WORKDIR /app

# Устанавливаем зависимости по package.json/package-lock.json
COPY package*.json ./
RUN npm ci --legacy-peer-deps && npm cache clean --force

# Копируем остальной исходный код Next.js-приложения
COPY . .

# Собираем production-бандл
RUN npm run build

# Приложение слушает порт 3000
EXPOSE 3000

# Запуск Next.js в режиме production
CMD ["npm", "run", "start"]
