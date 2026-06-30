import time

import psycopg2
import redis
from psycopg2.extensions import connection


def run():
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    conn: connection | None = None

    while True:
        try:
            if conn is None or conn.closed:
                conn = psycopg2.connect(dbname="database", user="user", password="password", host="localhost", port=5432)
                conn.autocommit = True

            with conn.cursor() as cur:
                cur.execute("SELECT id, user_id, new_balance FROM outbox ORDER BY id ASC LIMIT 1")
                row = cur.fetchone()

                if row:
                    event_id, user_id, new_balance = row

                    pipe = r.pipeline()
                    pipe.set(f"user:{user_id}:balance", new_balance, ex=600)
                    pipe.execute()

                    cur.execute("DELETE FROM outbox WHERE id = %s", (event_id,))
                    continue

        except Exception as e:
            print(f"Ошибка outbox-воркера: {e.__class__.__name__}")
            if conn:
                try:
                    conn.close()
                except psycopg2.Error:
                    pass
            conn = None
            time.sleep(2)
            continue

        time.sleep(0.1)


if __name__ == "__main__":
    run()