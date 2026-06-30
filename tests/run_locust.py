import subprocess

import requests
from requests import RequestException

from utils import API, start_worker, stop_worker


def run_locust_session():
    print(f"\n{'=' * 60}\nНагрузочное тестирование (Locust)\n{'=' * 60}")
    print("Выберите метод для тестирования:")
    print("1 - Dual Write")
    print("2 - Transactional Dual Write")
    print("3 - Transactional Outbox")
    print("4 - Change Data Capture")

    choice = input("\nВведите номер (1-4): ")

    tag_map = {"1": "dual_write", "2": "tx_dual_write", "3": "outbox", "4": "cdc"}
    worker_map = {"3": "outbox_worker.py", "4": "cdc_worker.py"}

    if choice not in tag_map:
        print("Неверный выбор.")
        return

    selected_tag = tag_map[choice]
    worker_file = worker_map.get(choice)
    worker_process = None

    try:
        try:
            requests.post(f"{API}/system/reset", timeout=5)
            print("Система очищена.")
        except RequestException as e:
            print(f"Сервер недоступен: {e.__class__.__name__}")
            return

        worker_process = start_worker(worker_file)

        print(f"Запуск веб-интерфейса Locust для метода {selected_tag}...")
        subprocess.run(["locust", "-f", "tests/locustfile.py", "--tags", selected_tag])

    finally:
        stop_worker(worker_process)


if __name__ == "__main__":
    run_locust_session()