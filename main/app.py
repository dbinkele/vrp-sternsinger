import os
import uuid
from datetime import datetime

from flask import request, Flask, jsonify
from flask_cors import cross_origin
from rq import Queue

from main.requests_util import request_coordinates_remote
from main.worker.job import run_job
from main.worker.worker import conn

app = Flask(__name__, instance_relative_config=True, static_folder='../build', static_url_path='')

config_file = os.environ.get('CONFIG_FILE')
app.config.from_pyfile(config_file)
q = Queue(connection=conn)

MAIL_KEYS = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_USE_SSL',
             'MAIL_USE_TLS', 'MAIL_TYPE', 'MAP_API_KEY']


@app.route("/coordinates", methods=["GET"])
@cross_origin()
def coordinates():
    data = request.args
    config = make_config()
    api_key = config.get("MAP_API_KEY")

    json = request_coordinates_remote(api_key, data['code'], data['address'], data['country'], data['locality'])
    features_ = json['features']
    if len(features_) <= 0:
        return {}
    coords_result = features_[0]['geometry']['coordinates']
    return {'lat': coords_result[1], 'lon': coords_result[0]}


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
    alive_time = constraints_json['timeout'] * 2
    job = q.enqueue_call(func=run_job,
                         args=(data['data'], constraints_json, config, data['recipent'], api_key,
                               './main/templates/template.html'), result_ttl=5000, ttl=None, timeout=alive_time)

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
    config['SENDGRID_API_KEY'] = os.environ.get('SENDGRID_API_KEY')
    config['SENDGRID_USERNAME'] = os.environ.get('SENDGRID_USERNAME')
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


def flatten_route_lists(result_data):
    for idx, route in enumerate(result_data):
        for route_item in route:
            route_item['idx'] = idx
    return [val for sublist in result_data for val in sublist]


if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=False, port=os.environ.get('PORT', 80))
