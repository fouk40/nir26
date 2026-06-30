import subprocess
import time
import sys

API = "http://127.0.0.1:8000"


def start_worker(worker_file: str | None) -> subprocess.Popen | None:
    if worker_file:
        print(f"Запуск воркера {worker_file}...")

        process = subprocess.Popen(
            [sys.executable, f"workers/{worker_file}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        time.sleep(2)
        return process
    return None


def stop_worker(process: subprocess.Popen | None) -> None:
    if process:
        print("Остановка воркера...")
        process.terminate()
        process.wait()