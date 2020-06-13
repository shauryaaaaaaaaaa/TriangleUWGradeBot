#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from slackeventsapi import SlackEventAdapter
from slackclient import SlackClient
from TranscriptReader import PDFParser
import os
import requests
from random import randint
from time import sleep
import pandas as pd
from flash import Flask
from dotenv import load_dotenv

load_dotenv()

NAME_SETUP = False
ignoredUsers = ['Slackbot', 'grade_bot']
quarter = 'WINTER 2020'

# Our app's Slack Event Adapter for receiving actions via the Events API
slack_signing_secret = os.environ['SLACK_SIGNING_SECRET']
slack_events_adapter = SlackEventAdapter(slack_signing_secret)


# Create a SlackClient for your bot to use for Web API requests
slack_bot_token = os.environ['SLACK_BOT_TOKEN']
slack_client = SlackClient(slack_bot_token)

# Example responder to greetings
@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    if message["user"].lower() != os.environ['BOT_USER_NAME'].lower():
        grade = processFile(message)
        if(grade is None): return
        
        text = """I found your quarter gpa to be %s and your cumulative to be %s.
        If this is incorrect please contact the AVP""" % grade
        slack_client.api_call("chat.postMessage", channel=message["channel"], text=text)
        
        if(not NAME_SETUP):
            realNames, ids = getNames()
            global gradeDataFrame
            gradeDataFrame = pd.DataFrame(list(zip(ids, realNames)), columns =['ID', 'Name'])
            gradeDataFrame[quarter + ' GPA'] = None
            gradeDataFrame['Cumulative GPA'] = None
        
        index = -1
        try:
            index = ids.index(message["user"])
        except ValueError:
            slack_client.api_call("chat.postMessage", channel=message["channel"],
                                  text='Contact AVP. Error: Invalid User')
            return
        
        gradeDataFrame.at[index, quarter + ' GPA'] = grade[0]
        gradeDataFrame.at[index, 'Cumulative GPA'] = grade[1]
        
        sleep(1)

def processFile(file):
    url = getFileURL(file)
    
    if url is None: return
    
    response = requests.get(url, auth=BearerAuth(slack_bot_token))
    
    if(response.status_code == 404):
        slack_client.api_call("chat.postMessage", channel=file["channel"], text='File not found')
        return
    elif(response.status_code != 200):
        slack_client.api_call("chat.postMessage", channel=file["channel"], text='Error downloading file')
        return
    
    fileName = 'transcript' + str(randint(0,9999999)) + '.pdf' # to do: repeated name, diff folder
    with open(fileName, 'xb') as f:
        f.write(response.content)
    
    try:
        p = PDFParser(fileName, quarter)
        gpa = p.getGPA()
        p.closeFile()
        return gpa
    except ValueError as err:
        slack_client.api_call("chat.postMessage", channel=file["channel"], text=format(err))
    except:
        slack_client.api_call("chat.postMessage", channel=file["channel"], text='Error parsing file')

def getFileURL(file):
    file_info = file.get('files')
    
    if file_info is None:
        slack_client.api_call("chat.postMessage", channel=file["channel"], text='No file attached')
        return
    
    if(file_info[0].get('name')[-4:].lower() != '.pdf'):
        slack_client.api_call("chat.postMessage", channel=file["channel"], text='Invalid file type')
        return
    
    return file_info[0].get('url_private')

def getNames():
    response = requests.get('https://slack.com/api/users.list', params={'token':slack_bot_token})
    userList = response.json()
    
    if not userList.get('ok'):
        print(userList.get('error') + ' during name set up')
        return
    
    realNames = list()
    ids = list()
    
    members = userList.get('members')
    for member in members:
        if(not member.get('is_bot') and not member.get('deleted') and member.get('real_name') not in ignoredUsers):
            realNames.append(member.get('profile').get('real_name_normalized'))
            ids.append(member.get('id'))
    
    NAME_SETUP = True
    
    return realNames, ids

# Error events
@slack_events_adapter.on("error")
def error_handler(err):
    print("ERROR: " + str(err))

class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r    

# Once we have our event listeners configured, we can start the
# Flask server with the default `/events` endpoint on port 3000
slack_events_adapter.start(port=3000)

