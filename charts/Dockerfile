FROM python:3.12-slim
WORKDIR /charts
COPY charts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY charts/streamlit_app.py .
CMD ["python", "-m", "streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
