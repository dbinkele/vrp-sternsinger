import os

from flask import request, Flask, jsonify, render_template
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


@app.route("/", methods=["GET"])
def check_job():
    query_id = request.args.get('job')
    if query_id:
        found_job = q.fetch_job(query_id)
        if found_job:
            output = get_status(found_job)
        else:
            output = {'id': None, 'error_message': 'No job exists with the id number ' + query_id}
        return output
    else:
        return {'id': None, 'error_message': 'No job id given'}


@app.route("/", methods=["POST"])
def create_job():
    data = request.get_json()
    api_key = os.getenv("MAP_API_KEY")

    job = q.enqueue(run_job, data['data'], data['constraints'], mail_config(), data['recipent'], api_key,
                    './main/templates/template.html')

    return jsonify(get_status(job))


# a route where we will display a welcome message via an HTML template
@app.route("/index")
def hello():
    message = "Hello, World"
    return render_template('index.html', message=message)

def mail_config():
    mail_data = dict((k, app.config[k]) for k in MAIL_KEYS if k in app.config)
    mail_data['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    return mail_data


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
