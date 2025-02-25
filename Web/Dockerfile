# Используем базовый образ NGINX
FROM nginx:alpine

# Копируем все файлы из папки Frontend в папку NGINX
COPY ./Frontend/ /usr/share/nginx/html/

EXPOSE 80

# Запуск NGINX
CMD ["nginx", "-g", "daemon off;"]
