import subprocess
import time

import psycopg2
import redis
import requests
from requests.exceptions import RequestException

from utils import API, start_worker, stop_worker

REDIS_CONTAINER = "redis"


def run_chaos_experiment(endpoint: str, name: str, worker_file: str = None) -> None:
    print(f"\n{'=' * 60}\nТестирование {name}\n{'=' * 60}")

    worker_process = start_worker(worker_file) if worker_file else None

    try:
        try:
            requests.post(f"{API}/system/reset", timeout=5)
            print("Система сброшена.")
        except RequestException as e:
            print(f"Сервер недоступен: {e.__class__.__name__}")
            return

        print(f"Выключение Redis...")
        subprocess.run(["docker", "stop", REDIS_CONTAINER], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(1.5)


        print(f"Отправляется запрос: POST {endpoint} (+5000)...")
        try:
            res = requests.post(f"{API}{endpoint}?user_id=1&amount=5000", timeout=2)
            response_data = res.json()
            if response_data.get("status") == "error":
                print(f"Ответ API: отказ (потеря доступности). Причина: {response_data.get("detail")}")
            else:
                print(f"Ответ API: успех (статус: {response_data.get("status")})")

        except RequestException as e:
            print(f"Ответ API: сервер недоступен ({e.__class__.__name__})")


        print("Включение Redis...")
        subprocess.run(["docker", "start", REDIS_CONTAINER], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

        time.sleep(2)

        db_balance = -1
        redis_balance = -1

        try:
            with psycopg2.connect(dbname="database", user="user", password="password", host="localhost", port=5432) as db_conn:
                db_conn.autocommit = True
                with db_conn.cursor() as db_cur:
                    db_cur.execute("SELECT balance FROM users WHERE id = 1")
                    row = db_cur.fetchone()
                    db_balance = int(row[0]) if row else 0
        except psycopg2.Error as e:
            print(f"Ошибка PostgreSQL: {e.__class__.__name__}")

        try:
            with redis.Redis(host="localhost", port=6379, decode_responses=True) as r:
                val = r.get("user:1:balance")
                redis_balance = int(val) if val else 0
        except redis.RedisError as e:
            print(f"Ошибка Redis: {e.__class__.__name__}")

        print(f"\nРезультаты:\n    в PostgreSQL: {db_balance}\n    в Redis: {redis_balance}")

        if db_balance == 5000 and redis_balance == 5000:
            print("Вывод: согласованность в конечном счете достигнута.")
        elif db_balance == 0 and redis_balance == 0:
            print("Вывод: транзакция отменена. Потеряна доступность.")
        else:
            print("Вывод: данные рассинхронизированы.")

    finally:
        stop_worker(worker_process)


if __name__ == "__main__":
    run_chaos_experiment("/balance/dual-write", "Dual Write")
    run_chaos_experiment("/balance/tx-dual-write", "Transactional Dual Write")
    run_chaos_experiment("/balance/outbox-write", "Transactional Outbox", "outbox_worker.py")
    run_chaos_experiment("/balance/cdc-write", "Change Data Capture", "cdc_worker.py")