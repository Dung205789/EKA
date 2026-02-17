FROM python:3.11-slim

WORKDIR /ui

RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir streamlit==1.* httpx==0.* pandas==2.*

COPY ui /ui/ui

EXPOSE 8501

ENV PYTHONPATH=/ui

CMD ["streamlit", "run", "ui/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
