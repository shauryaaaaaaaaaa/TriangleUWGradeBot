from slackeventsandslashapi import SlackEventAdapter
from slackclient import SlackClient
from TranscriptReader import PDFParser
import os
import requests
from random import randint, shuffle
from time import sleep
from AuthTokenGenerator import BearerAuth
import pandas as pd
from json import loads, dumps
from dotenv import load_dotenv as import_environment_variables

import_environment_variables()

global NAME_SETUP; NAME_SETUP = True
global ignoredUsers; ignoredUsers = ['Slackbot', 'grade_bot']
global quarter; quarter = 'WINTER 2020'

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
            nameSetup()
        
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

@slack_events_adapter.on("slash")
def slash(event_data):
    if(event_data["user_name"] != os.environ["AVP_USERNAME"] or event_data["command"] == "gradeshelp"):
        gradesHelp(event_data)
    elif(event_data["command"] == "updatenames"): updateNames(event_data)
    elif(event_data["command"] == "postrequest"): postRequest(event_data)
    elif(event_data["command"] == "gradereminder"): gradeReminder(event_data)
    elif(event_data["command"] == "academicprobationlist"): academicProbation(event_data)
    elif(event_data["command"] == "gradereport"): gradeReport(event_data)
    
def respondToSlash(event_data, text):
    response = requests.post(event_data["response_url"], json=loads(dumps({"text":text})))
    if(response.status_code != 200):
        print('Something went wrong')

def gradeReport(event_data):
    reportsPath = os.path.join(os.environ["PARENT_PATH"], 'Reports') + '/'
    try:
        os.mkdir(reportsPath)
    except:
        pass
    
    fileName = 'GradesReport' + str(randint(0, 9999999)) + '.csv'
    reportDF = gradeDataFrame[[gradeDataFrame.columns[1], gradeDataFrame.columns[2], gradeDataFrame.columns[3]]]
    reportDF.to_csv(reportsPath + fileName, index=False)
    
    sendFile(reportsPath + fileName)
    
def academicProbation(event_data):
    probation = getProbationList()
    shuffle(probation)
    filePath = saveCSV(probation)
    sendFile(filePath)

def sendFile(filePath):
    reponse = slack_client.api_call("files.upload", channels=getAVPChannel(), content=open(filePath, 'rb'))
    

def getProbationList():
    probationList = list()

    for index, row in gradeDataFrame.iterrows():
        if(row["Cumulative GPA"] is not None):
            if(float(row["Cumulative GPA"]) < 3 or float(row[gradeDataFrame.columns[2]]) < 3):
                probationList.append(row["Name"])

    return probationList

def saveCSV(probation):
    reportsPath = os.path.join(os.environ["PARENT_PATH"], 'Reports') + '/'
    
    try:
        os.mkdir(reportsPath)
    except:
        pass
    
    probationFile = pd.DataFrame({"Brothers on Academic Probation": probation})
    fileName = 'ProbationList' + str(randint(0, 9999999)) + '.csv'
    probationFile.to_csv(reportsPath + fileName, index=False)
    return reportsPath + fileName

def getAVPChannel():
    try:
        index = realNames.index(os.environ['AVP_REALNAME'])
        avpID = ids[index]
        return getIms([avpID], {})[0]
    except:
        return

def gradeReminder(event_data):
    noResponse = getNoneResponses()
    imIDs = getIms(noResponse, event_data)
    sendReminders(imIDs)
    
def getNoneResponses():
    noResponse = list()

    for index, row in gradeDataFrame.iterrows():
        if(row["Cumulative GPA"] is None):
            noResponse.append(row["ID"])

    return noResponse

def getIms(noResponse, event_data):
    imIDs = list()
    
    url = 'https://slack.com/api/conversations.open'
    params = {'token':slack_bot_token,
             'users':''}
    
    for user in noResponse:
        params['users'] = user
        response = requests.get(url, params=params)
        
        if(response.status_code != 200):
            respondToSlash(event_data, '<@%s> IM ID not found' % user)
        
        imInfo = response.json()
        imIDs.append(imInfo.get('channel').get('id'))
    
    return imIDs

def sendReminders(imIDs):
    text = """Hi there,
I see that you have not yet sent in a copy of your unofficial transcript to me yet.

Nationals and our local bylaws require that we collect everyone's GPA information, no matter what the grade is.
If you could please send me your unofficial transcript found: https://sdb.admin.uw.edu/sisstudents/uwnetid/transcriptpdf.aspx

If your grades have yet to be released, please contact the AVP and ignore this and similar messages you may get in the future.

Thanks"""
    for im in imIDs:
        slack_client.api_call("chat.postMessage", channel=im, text=text)

def postRequest(event_data):
    quarter = event_data["text"].strip().upper()
    if(event_data["text"] != quarter):
        respondToSlash(event_data, 'Quarter updated to ' + quarter)
    
    event_data["response_url"] = os.environ["ANNOUNCEMENTS_WEBHOOK"]
    
    text = """Hi everybody, its that time of the quarter again!
Please go to this link: https://sdb.admin.uw.edu/sisstudents/uwnetid/transcriptpdf.aspx, to download your
unofficial transcript and then send it to me in my DMs.

If you do not have all of your grades in yet, please message the AVP (%s).

Thanks!

I am a bot. View my source code here: github.com/shauryaaaaaaaaaa/TriangleUWGradeBot""" % os.environ["AVP_USERNAME"]
    
    respondToSlash(event_data, text)
    

def updateNames(event_data):
    try:
        length = len(realNames)
    except NameError:
        length = 0
    
    nameSetup()
    
    text = str(len(realNames) - length) + ' name(s) added.'
    
    respondToSlash(event_data, text)

def gradesHelp(event_data):
    username = event_data["user_name"]
    
    if(username == os.environ["AVP_USERNAME"]):
        respondToSlash(event_data, AVPHelp())
    else:
        respondToSlash(event_data, userHelp())

def AVPHelp():
    return """Hello Mr. AVP. I am Grade bot. Here are a list of my commands:
/gradeshelp - Shows this dialogue.
/updatenames - Updates the list of members. Warning: deletes existing grade data
/postrequest [quarter] - Send a message to announcements reminding everyone to send their grades to me.
                                    Requires the name of the quarter, must be an exact match to the transcript.
                                        Example: /postrequest SPRING 2020
/gradereminder - Sends a message to those that have not yet sent their grades in
/academicprobationlist - Creates a CSV list of those with a quarterly and/or cumulative GPA below a 3.0 in
                                    random order with no grade information to provide to the academic chair.
/gradereport - Creates an Excel file with everyone's names and gpa

The best way to release the bot is:
/updatenames
/postrequest SPRING 2020"""
    
def userHelp():
    return """Hi there. I am Grade bot. Please go to this link: https://sdb.admin.uw.edu/sisstudents/uwnetid/transcriptpdf.aspx
to download your unofficial transcript and then send it to me.

If you want to see how I work check out my GitHub: github.com/shauryaaaaaaaaaa/TriangleUWGradeBot"""

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
    
    transcriptStorage = os.path.join(os.environ["PARENT_PATH"], quarter) + '/'
    
    try:
        os.mkdir(transcriptStorage)
    except:
        pass
    
    try:
        fileName = 'transcript' + str(randint(0,9999999)) + '.pdf'
        with open(transcriptStorage + fileName, 'xb') as f:
            f.write(response.content)
    except:
        fileName = 'transcript' + str(randint(9999999,99999999)) + '.pdf'
        with open(transcriptStorage + fileName, 'xb') as f:
            f.write(response.content)
    
    try:
        p = PDFParser(transcriptStorage + fileName, quarter)
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
        slack_client.api_call("chat.postMessage", channel=file["channel"],
                              text='No file attached. For help, try /gradeshelp')
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

def nameSetup():
    global realNames
    global ids
    realNames, ids = getNames()
    global gradeDataFrame
    gradeDataFrame = pd.DataFrame(list(zip(ids, realNames)), columns =['ID', 'Name'])
    gradeDataFrame[quarter + ' GPA'] = None
    gradeDataFrame['Cumulative GPA'] = None

# Once we have our event listeners configured, we can start the
# Flask server with the default `/events` endpoint on port 3000
slack_events_adapter.start(port=3000)