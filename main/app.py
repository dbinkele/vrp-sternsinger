import os
import uuid

from flask import request, Flask, jsonify, render_template
from flask_cors import cross_origin
from rq import Queue

from main.dummy_data import make_dummy_result_data
from main.worker.job import run_job
from main.worker.worker import conn
from datetime import datetime

app = Flask(__name__, instance_relative_config=True, static_folder='../build', static_url_path='')

config_file = os.environ.get('CONFIG_FILE')
app.config.from_pyfile(config_file)
q = Queue(connection=conn)

MAIL_KEYS = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_USE_SSL',
             'MAIL_USE_TLS', 'MAIL_TYPE', 'MAP_API_KEY']


@app.route("/time", methods=["GET"])
@cross_origin()
def time():
    now = datetime.now()  # current date and time
    return jsonify({'items': [{'price': now.strftime("%m/%d/%Y, %H:%M:%S"), 'name': uuid.uuid4()}]})


@app.route("/data", methods=["GET"])
@cross_origin()
def data():
    result_data = make_dummy_result_data()
    result_data['result']['routes'] = flatten_route_lists(result_data['result']['routes'])
    return result_data


def flatten_route_lists(result_data):
    for idx, route in enumerate(result_data):
        for route_item in route:
            route_item['idx'] = idx;
    return [val for sublist in result_data for val in sublist]


@app.route("/vrp", methods=["GET"])
@cross_origin()
def check_job():
    query_id = request.args.get('job')
    if query_id:
        found_job = q.fetch_job(query_id)
        if found_job:
            output = get_status(found_job)
            if 'result' in output:
                output['result']['routes'] = flatten_route_lists(output['result']['routes'])
        else:
            output = {'id': None, 'error_message': 'No job exists with the id number ' + query_id}
        return output
    else:
        return {'id': None, 'error_message': 'No job id given'}


@app.route("/vrp", methods=["POST"])
@cross_origin()
def create_job():
    data = request.get_json()
    config = make_config()
    api_key = config.get("MAP_API_KEY")
    print("-----> Create Job " + api_key)
    constraints_json = data['constraints']
    transform_to_index_value_format(constraints_json, 'dwell_duration')
    transform_to_index_value_format(constraints_json, 'time_windows')
    job = q.enqueue_call(func=run_job,
                         args=(data['data'], constraints_json, config, data['recipent'], api_key,
                               '../templates/template.html'), result_ttl=5000, ttl=120)
    return jsonify(get_status(job))


@app.route('/', methods=["GET"])
@cross_origin()
def index():
    return app.send_static_file('index.html')


@app.route('/favicon.ico', methods=["GET"])
@cross_origin()
def favicon():
    return app.send_static_file('favicon.ico')


def make_config():
    config = dict((k, app.config[k]) for k in MAIL_KEYS if k in app.config)
    config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    for key in MAIL_KEYS:
        if not config.get(key):
            config[key] = os.getenv(key)

    return config


def get_status(job):
    status = {
        'id': job.id,
        'result': job.result,
        'status': 'failed' if job.is_failed else 'pending' if job.result == None else 'completed'
    }
    status.update(job.meta)
    return status


def transform_to_index_value_format(constrains_json, tag):
    dwell_duration = constrains_json[tag]
    constrains_json[tag] = dict([item.values() for item in dwell_duration])


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=False, port=os.environ.get('PORT', 80))
