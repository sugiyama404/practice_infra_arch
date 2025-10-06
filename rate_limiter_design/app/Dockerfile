FROM python:3.10-slim

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY main.py .

# ポート8000を公開
EXPOSE 8000

# Flaskアプリケーションの起動
CMD ["python", "main.py"]
