import datetime
import smtplib
from email.message import EmailMessage

from main.requests_util import request_dist_matrix
from main.run_algorithm import mainrunner
from main.template import render
import sendgrid
import os
from sendgrid.helpers.mail import *


def run_job(address_json, constrains_json, config, mail_to, api_key, template_html):
    try:
        return run(address_json, api_key, config, constrains_json, mail_to, template_html)
    except Exception as e:
        send_mail(config, str(e), mail_to, "")


def run(address_json, api_key, config, constrains_json, mail_to, template_html):
    planning_type = constrains_json['planningType']
    print("----> Job running " + planning_type)
    dist_matrix_json = request_dist_matrix(address_json, api_key, planning_type)
    json_routes = mainrunner(dist_matrix_json, constrains_json, address_json)
    routes_html = [render(json_route, template_html, planning_type) for json_route in json_routes]
    return send_mail(config, json_routes, mail_to, routes_html)


def send_mail(config, json_routes, mail_to, routes_html):
    if config.get('MAIL_TYPE') == 'gmail':
        return send_gmail_email(config, json_routes, mail_to, routes_html)
    return send_sendgrid(config, mail_to, routes_html)


def send_sendgrid(config, mail_to, json_routes):
    apikey = config('SENDGRID_API_KEY')
    sg = sendgrid.SendGridAPIClient(apikey=apikey)
    from_email = config['MAIL_USERNAME']
    email = Email(from_email)
    subject = "Route Planning"
    to_email = Email(mail_to)
    content = Content("text/plain", str(json_routes))
    mail = Mail(email, subject, to_email, content)
    print("Sendgrid..." + str(apikey) + " " + str(mail_to) + " " + str(from_email))
    try:
        response = sg.client.mail.send.post(request_body=mail.get())
        return {'routes': json_routes, 'mail_status': response.status_code}
    except Exception as e:
        raise e


def send_gmail_email(config, json_routes, mail_to, routes_html):
    msg = EmailMessage()
    msg['From'] = config['MAIL_USERNAME']
    msg['To'] = mail_to
    msg['Subject'] = 'Route Planning'
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
        raise e


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
