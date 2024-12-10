import sqlite3


class SQLiteClient:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_urls (
                url_hash TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


    def fetch_seen_urls_hash(self):
        self.cursor.execute("SELECT url_hash FROM seen_urls")
        return [self.row[0] for self.row in self.cursor.fetchall()]


    def bulk_insert_seen_urls(self, url_hashes):
        self.cursor.executemany("INSERT INTO seen_urls (url_hash) VALUES (?)", [(url_hash,) for url_hash in url_hashes])
        self.conn.commit()

    def bulk_delete_seen_urls(self):
        self.cursor.execute("""
            DELETE FROM seen_urls
            WHERE created_at < DATETIME('now', '-7 days');
        """)
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()

