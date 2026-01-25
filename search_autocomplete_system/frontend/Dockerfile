FROM node:24-alpine

WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package*.json ./

# アプリケーションコードをコピー
COPY . .

# 依存関係をインストール
RUN npm install

# ポートを公開
EXPOSE 3000

# 開発モードでアプリケーションを実行
CMD ["npm", "run", "dev"]
