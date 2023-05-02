from __future__ import print_function

import os.path

import re
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from base64 import urlsafe_b64decode, urlsafe_b64encode

from email.mime.text import MIMEText

import email
import base64 #add Base64
import time 
import openai

SCOPES = ['https://mail.google.com/']

messages_read = []

# Read the API key from a text file
with open('openai-api-key.txt', 'r') as file:
    api_key = file.read().strip()

# Configure your OpenAI API credentials
openai.api_key = api_key

role = """
 I want you to respond emails like Bruno Ibanez, being as formal as you can, and I want you to infer the name of the person from the email received. 
Bruno is a bit assertive and tends to escalate things when needed to John Prendergast. Bruno also has deep knowledge of Python, Data Engineering and Deep Learning, as all the Applied Intelligence Party. He is from Spain and is 25 years old.
I do not want you to use [Sender], [Name] or anything similar, for example. Bruno's working experience is the following: 
Data Science Consultant in Accenture
- Managed a team to deliver a project that directly impacted 500k customers and a cumulative of 7.6B€ 
- Migration to cloud and productionizing of a Data Science multiplatform project that produced ETL processes for a D365 front-end
- MVP to Pilot on a Google’s DocumentAI solution
- AWS and GCP
- Terraform, Docker, Azure DevOps Pipelines, Airflow, Snowflake
- SQL, Pyspark, R
Skills: SQL · Data Analysis · Problem Solving · Data Science · Google Cloud Platform (GCP) · Apache Airflow
AI Engineer in Telefónica: 
Telefónica logo
Artificial Intelligence EngineerArtificial Intelligence Engineer
TelefónicaTelefónica
- Deep Learning Natural Language Processing (NLP) and Computer Vision (CV) implementing Proof-of-Concepts or MVPs.
Research on DeepFakes Detection, Action Recognition, Face Recognition, Image Stylization, NLP Language Models (BERT, Transformers and Markov Models), Text Summarisation, Adversarial Attacks on DNNs, Music Generation with Recurrent Neural Networks (RNNs), Audio Recognition (via Spectrogram), Conversational Bots.
"""

def generate_response(sender, subject, body):
    # Compose the prompt for ChatGPT
    prompt = f"Sender: {sender}\nSubject: {subject}\nBody: {body}\n\n"

    # Generate response from ChatGPT using the GPT-3.5-turbo model
    reply = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
            {"role": "system", "content": role},
            {"role": "user", "content": prompt}
        ]
    )

    return reply.choices[0]["message"]["content"].strip()


def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    user_id = "bruno.ibanezlopez@gmail.com"
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)

        while True:
            results = service.users().messages().list(userId=user_id, maxResults=10, q="is:unread to:" + user_id).execute()
            messages = results.get('messages', [])
            
            for message in messages:
                msg = service.users().messages().get(userId=user_id, id=message['id']).execute()
                if message['id'] in messages_read:
                    continue
                else:
                    messages_read.append(message['id'])
                # Print information from the email
                headers = {header['name']: header['value'] for header in msg['payload']['headers']}
                subject = headers.get('Subject', '')
                sender = headers.get('From', '')
                date = headers.get('Date', '')
                snippet = msg['snippet']

                print("Subject:", subject)
                print("From:", sender)
                print("Date:", date)
                print("Snippet:", snippet)
                print("------------------------")

                # Respond to the email
                reply_text = generate_response(sender, subject, snippet)
                send_reply(service, user_id, message['id'], reply_text, sender, subject)

            # Wait for two seconds before checking the inbox again
            time.sleep(2)

    except HttpError as error:
        # TODO(developer) - Handle errors from Gmail API.
        print(f'An error occurred: {error}')

def send_reply(service, user_id, message_id, reply_text, recipient, subject):
    """Sends a reply to the email with the provided text."""
    try:
        message = service.users().messages().get(userId=user_id, id=message_id).execute()

        recipient = extract_email(recipient)
        
        
        if recipient:
            message = MIMEText(reply_text)
            message['to'] = recipient
            message['from'] = user_id
            message['subject'] = "Re: " + subject

            body = {'raw': urlsafe_b64encode(message.as_bytes()).decode()}
            service.users().messages().send(
                userId=user_id,
                body=body
                ).execute()

            service.users().messages().send(userId=user_id, body=body).execute()
            print(f"Replied to message with ID: {message_id}")
        else:
            print("Recipient address not found in the email headers.")

    except HttpError as error:
        # TODO(developer) - Handle errors from Gmail API.
        print(f'An error occurred: {error}')


def extract_email(string):
    # Regular expression pattern to match email addresses
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'

    # Find all matches of the pattern in the string
    matches = re.findall(pattern, string)

    if matches:
        return matches[0]  # Return the first match (valid email address)
    else:
        return None  # No valid email address found



if __name__ == '__main__':
    main()