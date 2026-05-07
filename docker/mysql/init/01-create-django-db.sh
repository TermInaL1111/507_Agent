#!/bin/sh
set -eu

mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS \`${DJANGO_DB_NAME:-django_user_service}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON \`${DJANGO_DB_NAME:-django_user_service}\`.* TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;
SQL
