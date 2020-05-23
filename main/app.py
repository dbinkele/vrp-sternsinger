import os
import uuid

from flask import request, Flask, jsonify, render_template
from flask_cors import cross_origin
from rq import Queue

from main.dummy_data import make_dummy_result_data
from main.worker.job import run_job
from main.worker.worker import conn
from datetime import datetime

app = Flask(__name__, instance_relative_config=True, static_url_path='',
            static_folder='static',
            template_folder='templates')

config_file = os.environ.get('CONFIG_FILE')
app.config.from_pyfile(config_file)
q = Queue(connection=conn)

MAIL_KEYS = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_USE_SSL',
             'MAIL_USE_TLS']


@app.route("/time", methods=["GET"])
@cross_origin()
def time():
    now = datetime.now()  # current date and time
    return jsonify({'items': [{'price': now.strftime("%m/%d/%Y, %H:%M:%S"), 'name': uuid.uuid4()}]})


@app.route("/data", methods=["GET"])
@cross_origin()
def data():
    result_data = make_dummy_result_data()
    new_routes = [with_id(idx, route) for idx, route in enumerate(result_data['result']['routes'])]
    flattened = [val for sublist in new_routes for val in sublist]
    result_data['result']['routes'] = flattened
    return result_data


def with_id(idx, route):
    idx_dict = {'id': idx}
    return [dict(route_member.items() | idx_dict.items()) for route_member in route]


@app.route("/vrp", methods=["GET"])
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


@app.route("/vrp", methods=["POST"])
def create_job():
    data = request.get_json()
    api_key = os.getenv("MAP_API_KEY")

    job = q.enqueue(run_job, data['data'], data['constraints'], mail_config(), data['recipent'], api_key,
                    './main/templates/template.html')

    return jsonify(get_status(job))


# a route where we will display a welcome message via an HTML template
@app.route("/")
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
