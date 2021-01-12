import os

import redis
from rq import Queue, Connection

from main.worker.heroku_rq_worker import Worker

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, ['default'])))
        worker.work()
