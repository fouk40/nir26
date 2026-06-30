import random
import statistics
import time

import redis
import requests
from requests import RequestException

from utils import API, start_worker, stop_worker

ITERATIONS = 100


def measure_lag(endpoint: str, name: str, worker_file: str):
    print(f"\n{'=' * 90}\nИзмерение задержки синхронизации между PostgreSQL и Redis: {name}\n{'=' * 90}")

    worker_process = start_worker(worker_file)
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    lag_results = []

    try:
        requests.post(f"{API}/system/reset", timeout=5)
    except RequestException as e:
        print(f"Сервер недоступен: {e.__class__.__name__}")
        stop_worker(worker_process)
        return

    time.sleep(7)

    print(f"Запуск серии из {ITERATIONS} транзакций...")

    try:
        for i in range(1, ITERATIONS + 1):
            test_user_id = random.randint(1, 1000)
            amount_to_add = random.randint(10, 500)

            current_redis_val = r.get(f"user:{test_user_id}:balance")
            start_balance = int(current_redis_val) if current_redis_val else 0
            expected_balance = start_balance + amount_to_add

            try:
                requests.post(f"{API}{endpoint}?user_id={test_user_id}&amount={amount_to_add}", timeout=2)
            except RequestException as e:
                print(f"Сервер недоступен: {e.__class__.__name__}")
                return

            start_lag_time = time.perf_counter()

            success = False
            while True:
                if r.get(f"user:{test_user_id}:balance") == str(expected_balance):
                    end_lag_time = time.perf_counter()
                    success = True
                    break

                time.sleep(0.001)

            if success:
                pure_lag_ms = (end_lag_time - start_lag_time) * 1000
                lag_results.append(pure_lag_ms)

    finally:
        stop_worker(worker_process)

    print(f"\nСтатистика задержки синхронизации:")
    print(f"Средняя задержка: {statistics.mean(lag_results):.2f} мс")
    print(f"Медианная задержка: {statistics.median(lag_results):.2f} мс")
    print(f"Минимальная задержка: {min(lag_results):.2f} мс")
    print(f"Максиммальная задержка: {max(lag_results):.2f} мс")


if __name__ == "__main__":
    measure_lag("/balance/outbox-write", "Transactional Outbox", "outbox_worker.py")
    measure_lag("/balance/cdc-write", "Change Data Capture", "cdc_worker.py")