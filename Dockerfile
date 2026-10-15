FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY app /app
RUN python -m compileall -q /app
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 150 --access-logfile - --error-logfile -"]
