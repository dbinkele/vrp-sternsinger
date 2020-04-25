import os

from flask import request, Flask, jsonify

from main.worker.job import run_job

app = Flask(__name__, instance_relative_config=True)


@app.route("/", methods=["POST"])
def handle_job():
    data = request.get_json()
    result = run_job(data['data'], data['constraints'])
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
