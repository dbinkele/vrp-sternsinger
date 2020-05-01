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
    query_id = request.args.get('job')
    if query_id:
        found_job = q.fetch_job(query_id)
        if found_job:
            output = get_status(found_job)
        else:
            output = {'id': None, 'error_message': 'No job exists with the id number ' + query_id}
        return output
    else:
        data = request.get_json()
        api_key = os.getenv("MAP_API_KEY")

        job = q.enqueue(run_job, data['data'], data['constraints'], mail_config(), data['recipent'], api_key,
                        '../templates/template.html')
        # run_job(data['data'], data['constraints'], mail_config(), RECIPENT)
        status = get_status(job)
        return jsonify(status)


def mail_config():
    return dict((k, app.config[k]) for k in MAIL_KEYS if k in app.config)


def get_status(job):
    status = {
        'id': job.id,
        'result': job.result,
        'status': 'failed' if job.is_failed else 'pending' if job.result == None else 'completed'
    }
    status.update(job.meta)
    return status


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
