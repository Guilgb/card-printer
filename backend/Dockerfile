FROM python:3.12-slim
WORKDIR /srv
COPY engine/requirements.txt engine-requirements.txt
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r engine-requirements.txt -r requirements.txt
COPY engine /srv/engine
COPY backend/app /srv/app
ENV ENGINE_DIR=/srv/engine DATA_DIR=/data
RUN useradd -m app && mkdir /data && chown app /data
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
