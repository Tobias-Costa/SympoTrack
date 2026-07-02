#!/bin/bash

echo "Create migrations"
python manage.py makemigrations
echo "=========================="

echo "Migrate"
python manage.py migrate
echo "=========================="

echo "Start server"
python manage.py runserver 127.0.0.1:8000
echo "=========================="