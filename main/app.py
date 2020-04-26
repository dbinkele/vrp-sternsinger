import os

from flask import request, Flask, jsonify
from rq import Queue

from main.worker.job import run_job
from main.worker.worker import conn

app = Flask(__name__, instance_relative_config=True)
config_file = os.environ.get('CONFIG_FILE')
app.config.from_pyfile(config_file)
q = Queue(connection=conn)

# RECIPENT = 'dbinkeleraible@googlemail.com'
RECIPENT = 'dbinkele@itemis.com'

MAIL_KEYS = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_USE_SSL',
             'MAIL_USE_TLS']


@app.route("/", methods=["POST"])
def handle_job():
    data = request.get_json()
    q.enqueue(run_job, data['data'], data['constraints'], mail_config(), "")
    return jsonify("{'success': 1}")


def mail_config():
    return dict((k, app.config[k]) for k in MAIL_KEYS if k in app.config)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
