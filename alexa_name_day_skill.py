 # -*- coding: utf-8 -*-

import sys
import json
import boto3
from difflib import SequenceMatcher

sys.path.append('./modules')

import unidecode

s3_url_base = "https://s3-eu-west-1.amazonaws.com/alexa-name-day-skill/"


def lambda_handler(event, context):
    if event["session"]["new"]:
        event["session"]["attributes"] = {}
        on_session_started({"requestId": event["request"]["requestId"]}, event["session"])

    if event["request"]["type"] == "LaunchRequest":
        return launch_message(event["request"], event["session"])
    elif event["request"]["type"] == "IntentRequest":
        return on_intent(event["request"], event["session"])
    elif event["request"]["type"] == "SessionEndedRequest":
        return session_ended_intent(event["request"], event["session"])


def on_session_started(session_started_request, session):
    print("Starting new session.")


def launch_message(launch_request, session):
    speech_output = "<speak> Welcome to the name day skill. " \
                    "Ask me for someone's name day, this can be " \
                    "from any of the name day calendars I know. </speak>"
    reprompt_text = "<speak> Please ask me for someone's name day, for " \
                    "example say.  Name day of Marcela from Slovakia. </speak>"
    should_end_session = False
    return build_response(session['attributes'], build_speechlet_response_no_card(
        speech_output, reprompt_text, should_end_session))


def on_intent(intent_request, session):
    intent = intent_request["intent"]
    intent_name = intent_request["intent"]["name"]

    if intent_name == "NameDayIntent":
        return name_day_intent(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_help_response(session)
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request(session)
    elif intent_name == "Unhandled":
        return handle_unhandled(session)
    else:
        raise ValueError("Invalid intent")


# sessin handlers & help
def get_help_response(session):
    speech_output = "<speak> You can say things like, ask " \
                    "nameday for Marcela in Slovakia or " \
                    "ask nameday for name day of " \
                    "Marcela from Slovakia. </speak>"
    should_end_session = False
    return build_response(session['attributes'], build_speechlet_response_no_card(
        speech_output, None, should_end_session))


def handle_session_end_request(session):
    should_end_session = True
    speech_output = "<speak> Thank you for using the Name Day skill.  Ciao! </speak>"
    return build_response(session['attributes'], build_speechlet_response_no_card(
        speech_output, None, should_end_session))


def session_ended_intent(session_ended_request, session):
    print("Ending session.")
    """ end """


def handle_unhandled(session):
    speech_output = "<speak> Unfortunately something has gone wrong, please try again.  Sorry! </speak>"
    should_end_session = True
    return build_response(session['attributes'], build_speechlet_response_no_card(
        speech_output, None, should_end_session))


# intents
def name_day_intent(intent, session):
    try:
        if session.get('attributes', {}).get('name'):
            name = session['attributes']['name'].replace('.','').replace(' ','').title()
        else:
            name = intent["slots"]["name"]["value"].replace('.','').replace(' ','').title()
        if session.get('attributes', {}).get('country'):
            country = session['attributes']['country']
        else:
            country = intent["slots"]["country"]["value"]
        found = False
        json_data = get_json(country + ".json")
        for month in json_data:
            for dataset in json_data[month]:
                for day in dataset:
                    names = dataset.get(day)
                    names_split = names.split(',')
                    for split in names_split:
                        found, nameday_name = check_name(name, unidecode.unidecode(split))
                        if found:
                            print("Alexa heard: ", name, " & ", country, " | Script created: ", nameday_name, " | Date: ", day, " ", month)
                            card_title = "Found something!"
                            should_end_session = True
                            session['attributes']['country'] = intent["slots"]["country"]["value"]
                            session['attributes']['name'] = intent["slots"]["name"]["value"]
                            card_text = nameday_name + " has a name day on the " + day + " " + month + "."
                            speech_output = "<speak> " + nameday_name + " has a name day on the " + day + " " + month + ". </speak>"
                
                            return build_response(session['attributes'], build_speechlet_response(
                                card_title, card_text, speech_output, None, should_end_session, country))
                    for split in names_split:
                        found, nameday_name = check_similar(name, unidecode.unidecode(split))
                        if found:
                            print("Alexa heard: ", name, " & ", country, " | Script created: ", nameday_name, " | Date: ", day, " ", month)
                            card_title = "Found something!"
                            should_end_session = True
                            session['attributes']['country'] = intent["slots"]["country"]["value"]
                            session['attributes']['name'] = intent["slots"]["name"]["value"]
                            card_text = nameday_name + " has a name day on the " + day + " " + month + "."
                            speech_output = "<speak> " + nameday_name + " has a name day on the " + day + " " + month + ". </speak>"
                
                            return build_response(session['attributes'], build_speechlet_response(
                                card_title, card_text, speech_output, None, should_end_session, country))
    except:
        should_end_session = True
        country = intent["slots"]["country"]["value"]
        speech_output = "<speak>Sorry I'm having trouble recognising that name, " \
                        "I'm learning all the time so please try again later.</speak>"
        return build_response(session['attributes'], build_elicit_dialog_no_card(
            speech_output, None, should_end_session, country))


# utility functions
def check_name(name1, name2):
    if name1 == name2:
        nameday_name = name1.replace("ll", "l")
        found = True
        return found, nameday_name
    else:
        found=False
        nameday_name=""
        return found, nameday_name

def check_similar(name1, name2):
    if similar(name1, name2) > 0.8:
        nameday_name = name1.replace("ll", "l")
        found = True
        return found, nameday_name
    else:
        found=False
        nameday_name=""
        return found, nameday_name
        
    
def get_json(filename):
    try:
        # return json.load(open(filename))
        file = boto3.resource('s3').Object('alexa-name-day-skill', "countries/" + filename)
        return json.loads(file.get()['Body'].read())
    except Exception as e:
        print(e)
        raise e


def phonetic_me(name):
    """ get jiggy with the IPA """
    new_name = []
    for letter in list(name):
        try:
            if letter == unicode("Ž", encoding='utf-8'):
                letter = '<phoneme alphabet="x-sampa" ph="Z">z</phoneme>'
            elif letter == "j":
                letter = '<phoneme alphabet="x-sampa" ph="j">j</phoneme>'
            elif letter == "o":
                letter = '<phoneme alphabet="x-sampa" ph="OI">o</phoneme>'
            # elif letter == "a":
            #     letter = '<phoneme alphabet="x-sampa" ph="@">a</phoneme>'
            else:
                letter = letter
        except Exception as e:
            print(e)
            raise e
        new_name.append(letter)
    ipa_name = "".join(new_name)
    return ipa_name


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


# JSON Responses
def build_speechlet_response(title, text, speech_output, reprompt_text, should_end_session, country):
    return {
        "outputSpeech": {
            "type": "SSML",
            "ssml": speech_output
        },
        "card": {
            "type": "Standard",
            "title": title,
            "text": text,
            "image": {
                "smallImageUrl": s3_url_base + "images/" + str(country) + "_small.png",
                "largeImageUrl": s3_url_base + "images/" + str(country) + "_large.png"
            }
        },
        "reprompt": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }


def build_speechlet_response_no_card(speech_output, reprompt_text, should_end_session):
    return {
        "outputSpeech": {
            "type": "SSML",
            "ssml": speech_output
        },
        "reprompt": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }


def build_elicit_dialog_no_card(speech_output, reprompt_text, should_end_session, country):
    return {
        "outputSpeech": {
            "type": "SSML",
            "ssml": speech_output
        },
        "reprompt": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": reprompt_text
            }
        },
        "shouldEndSession": should_end_session,
        "directives": [
            {
                "type": "Dialog.ElicitSlot",
                "slotToElicit": "name",
                "updatedIntent": {
                    "name": "NameDayIntent",
                    "confirmationStatus": "NONE",
                    "slots": {
                        "name": {
                            "name": "name",
                            "confirmationStatus": "NONE"
                        },
                        "country": {
                            "name": "country",
                            "value": country
                        }
                    }
                }
            }
        ]
        }


def build_response(session_attributes, speechlet_response):
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": speechlet_response
    }


if __name__ == "__main__":
    event = {
      "session": {
        "sessionId": "SessionId.ddb8a361-cf0a-4d9e-a0b0-aee6e71ca245",
        "application": {
          "applicationId": "amzn1.ask.skill.80edc7f5-85ab-4021-96dc-f94cca32fb42"
        },
        "attributes": {},
        "user": {
          "userId": "amzn1.ask.account.AHWWNY2BGCPOLVU6QSOXHKZMDYHF5YQX54I4HCT3FNCNH5WJAFNPGCQSXUMJ3ZUYRJE7CL22GXIIBLVV3XJ4YNNZAU5NR544F5QUJTZOJEX7Y3QA3IFU7OFEKOJ2HUODYMR4V3X5ZCACEX2GGXCYF67XJ7BISSPZUQTROTUE54Q3X24EPVL2BEF42BQAAAI2O2MBZRNPGGPNN4Q"
        },
        "new": False
      },
      "request": {
        "type": "IntentRequest",
        "requestId": "EdwRequestId.6c4b8cde-0327-4eea-8eb3-e7eb33ba4061",
        "locale": "en-GB",
        "timestamp": "2017-07-25T17:06:32Z",
        "intent": {
          "name": "NameDayIntent",
          "slots": {
            "country": {
              "name": "country",
              "value": "Slovakia"
            },
            "name": {
              "name": "name",
              "value": "z. a. r. k. o."
            },
            "name_spelt_out": True
          }
        }
      },
      "version": "1.0"
    }
    on_intent(event['request'], event['session'])
