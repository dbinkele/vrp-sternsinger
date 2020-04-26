import smtplib
from email.message import EmailMessage

from main.requests_util import request_dist_matrix
from main.run_algorithm import mainrunner
from main.template import render


def run_job(address_json, constrains_json, config, mail_to):
    dist_matrix_json = request_dist_matrix(address_json)
    json_routes = mainrunner(dist_matrix_json, constrains_json, address_json)
    routes_html = [render(json_route) for json_route in json_routes]
    print(routes_html)

    msg = EmailMessage()
    msg['From'] = config['MAIL_USERNAME']
    msg['To'] = mail_to
    msg['Subject'] = 'Just Testing..'
    message = """{}""".format(routes_html)
    msg.set_content(message)

    with make_server(config) as server:
        if config.get('MAIL_PASSWORD'):
            server.login(config['MAIL_USERNAME'], config.get('MAIL_PASSWORD'))
        server.send_message(msg)
        server.quit()

    return {'message': message}


def make_server(config):
    server = config['MAIL_SERVER']
    port = config['MAIL_PORT']
    if config.get('MAIL_USE_SSL'):
        client = smtplib.SMTP_SSL(server, port)
    else:
        client = smtplib.SMTP(server, port)

    if config.get('MAIL_USE_TLS'):
        client.ehlo()
        client.starttls()
        client.ehlo()

    return client
