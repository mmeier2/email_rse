import imaplib
import time
import getpass
import email
import socket
from email.parser import HeaderParser
import json
import sys
import re

EMAILS_PER_FILE = 100
FILENAME = ""
IMAP_SERVER = None
PARSER = HeaderParser()
MAIL_SERVERS = {'gmail.com': {'Server': str(socket.gethostbyname('imap.gmail.com'))},
                'yahoo.com': {'Server': str(socket.gethostbyname('imap.mail.yahoo.com'))},
                'aol.com': {'Server': str(socket.gethostbyname('imap.aol.com'))}}

read = set()

def getLogin():
    username = raw_input("Email address: ")
    password = getpass.getpass()
    return username, password

def getMessages(server):
    server.select()
    _, data = server.search(None, 'All')
    return data[0].split()

def add_body(m_from, m_subject, body):
    client_mail = []
    body = body.replace('=\r\n', '')
    urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', body)
    urls.extend(re.findall('<a href="?\'?([^"\'>]*)', body)) 

    set_urls = set(urls)
    if (len(urls)>0):
        message = {}
        message['from']    = m_from
        message['subject'] = m_subject
        message['body']    = body
        message['urls']    = []
        for url in set_urls:
            link = {}
            link['url'] = url
            link['RSE']     = False
            link['pRSE']    = False
            message['urls'].append(link)
            #print url
        client_mail.append(message)

    return client_mail

def get_next_file(fw, emails_read):
    if fw!=None:
        fw.write('{}]')
        fw.close()
    result_file = FILENAME + "_" + str(emails_read)
    fw = open(result_file, 'w+')
    fw.write("[")
    print "Wrote number of emails: " + str(emails_read)
    return fw

def get_email_ids():
    global IMAP_SERVER
    print("Please enter in your email account details.")
    username, password = getLogin()
    username2 = username.split("@")
    while len(username2) != 2:
        print("Please enter a valid email address.")
        username, password = getLogin()
        username2 = username.split("@")

    if username2[1] not in MAIL_SERVERS:
        raise NotImplementedError("Support for your email provider has not been implemented yet")

    IMAP_SERVER = imaplib.IMAP4_SSL(MAIL_SERVERS[username2[1]]["Server"], MAIL_SERVERS[username2[1]].get("Port", 993))
    
    IMAP_SERVER.login(username, password)
    
    ids = getMessages(IMAP_SERVER)
    return ids

def create_key(mail):
    s = ""
    if mail['Message-ID']:
        s += mail['Message-ID']
    if mail['Subject']:
        s += mail['Subject']
    if mail['Date']:
        s += mail['Date']

    if s == "":
        print "BAD ITS BLANK"

    return s

def get_body(email_id):
    resp, data = IMAP_SERVER.fetch(email_id, '(RFC822)')
    mail = email.message_from_string(data[0][1])

    key = create_key(mail)
    print key
    if key not in read:
        read.add(key)
        print 'added message'

        mg = {}
        client_mail = []

        if mail.is_multipart():
            for msg in mail.walk():
                if msg.is_multipart():
                    continue

                content_type =  msg.get_content_type()
                if content_type == 'text/plain' or content_type == 'text/html': 
                    body = msg.as_string()
                    # print body
                    if 'plain' in body and 'printable' in body:
                        client_mail.extend(add_body(mail['From'], mail['Subject'], body))
                        
        else:
            body = mail.get_payload()

            if 'plain' in body and 'printable' in body:
                print_body = add_body(mail['From'], mail['Subject'],body)
                print print_body
                client_mail.extend(print_body)
        return True, client_mail

    print 'DUPLICATE'
    return False, None


def main():
    global FILENAME
    FILENAME = sys.argv[1]
    ids = get_email_ids()
    print "Total number of emails: "+str(len(ids))

    client_mail = []
    wrote_emails = 0
    fw = get_next_file(None, wrote_emails)
    for email_id in ids:
        success, mail_body = get_body(email_id)

        if success and len(mail_body):
            for i in mail_body:
                mail_str = json.dumps(i)
                fw.write(mail_str+",\n")
                wrote_emails += 1

                if wrote_emails % EMAILS_PER_FILE == 0:
                    fw = get_next_file(fw, wrote_emails)

    if wrote_emails % EMAILS_PER_FILE != 0:
        fw.write('{}]')
        fw.close()
                

if __name__ == "__main__":
    main()