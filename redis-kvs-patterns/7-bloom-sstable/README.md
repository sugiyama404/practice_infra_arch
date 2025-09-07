# 7-bloom-sstable

## 概要
ブルームフィルタ＋SSTableライクな永続化・LSM-Tree圧縮によるパフォーマンス最適化KVS実装例。コミットログ・メモリテーブル・キャッシュ階層・非同期圧縮を備えています。

## 構成
- Python/Flask APIサーバ（app.py/bloom_sstable_server.py）

## 機能
- ブルームフィルタによる高速存在チェック
- コミットログ（WAL: Write Ahead Log）
- メモリテーブル（MemTable）とディスク永続化
- SSTableライクなソート済みファイル構造
- LSM-Tree風の多レベル圧縮
- バックグラウンドでの非同期圧縮処理
- キャッシュ階層化（L1, L2キャッシュ）

## 起動方法
1. Python依存インストール
```bash
pip install -r requirements.txt
```
2. APIサーバ起動
```bash
python app.py
```

## API例
- `/put` 書き込み（WAL, MemTable, Bloom, L2/SSTable反映）
- `/get` 読み込み（Bloom→L1→L2→SSTable階層検索）
- `/compact` LSM-Tree圧縮
- `/stats` キャッシュ・Bloom・SSTable統計

## テスト手順
1. `/put`で複数キー書き込み・Bloom存在チェック
2. `/get`でキャッシュ階層・SSTable検索挙動確認
3. `/compact`で圧縮・ファイル統合
4. `/stats`で各階層統計確認

## LSM-Treeアーキテクチャ解説
- MemTable（メモリ）→SSTable（ディスク）→圧縮統合
- Bloom Filterで高速存在判定
- WALで耐障害性
- L1/L2キャッシュで高速アクセス
