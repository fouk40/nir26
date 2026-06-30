import json
import time
import uuid

import redis
from confluent_kafka import Consumer


def run():
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)

    conf = {
        'bootstrap.servers': "localhost:9092",
        'group.id': f"cache_sync_group_{uuid.uuid4()}",
        'auto.offset.reset': 'latest',
        'enable.auto.commit': False,
        'max.poll.interval.ms': 60000,
    }
    consumer = Consumer(conf)
    consumer.subscribe(["cdc.public.users"])

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                continue

            try:
                value = json.loads(msg.value().decode('utf-8'))
            except Exception:
                consumer.commit()
                continue

            if value and value.get('op') == 'u' and value.get('after'):
                user_id = value['after']['id']
                new_balance = value['after']['balance']
                while True:
                    try:
                        r.set(f"user:{user_id}:balance", new_balance, ex=600)
                        break
                    except redis.RedisError as e:
                        print(f"Ошибка записи в Redis: {e.__class__.__name__}")
                        time.sleep(2)

            consumer.commit()

    finally:
        consumer.close()


if __name__ == "__main__":
    run()