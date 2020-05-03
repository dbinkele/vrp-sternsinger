import datetime
import smtplib
from email.message import EmailMessage

from main.requests_util import request_dist_matrix
from main.run_algorithm import mainrunner
from main.template import render


def run_job(address_json, constrains_json, config, mail_to, api_key, template_html):
    dist_matrix_json = request_dist_matrix(address_json, api_key)
    json_routes = mainrunner(dist_matrix_json, constrains_json, address_json)
    routes_html = [render(json_route, template_html) for json_route in json_routes]

    msg = EmailMessage()
    msg['From'] = config['MAIL_USERNAME']
    msg['To'] = mail_to
    msg['Subject'] = 'Just Testing..'
    message = """Send at {} \n content {}""".format(datetime.datetime.now(), routes_html)
    msg.set_content(message)
    try:
        with make_server(config) as server:
            if config.get('MAIL_PASSWORD'):
                server.login(config['MAIL_USERNAME'], config.get('MAIL_PASSWORD'))
            send_message = server.send_message(msg)
            server.quit()
            return {'routes': json_routes, 'mail_status': send_message}
    except Exception as e:
        return {'exception': repr(e)}


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
