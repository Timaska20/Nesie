# Используем базовый образ NGINX
FROM nginx:alpine

EXPOSE 80

COPY ./Frontend /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Запуск NGINX
CMD ["nginx", "-g", "daemon off;"]
