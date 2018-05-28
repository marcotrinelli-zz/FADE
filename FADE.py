#-*- coding: utf-8 -*-
from SPARQLWrapper import SPARQLWrapper, JSON
import json
import requests
import re
import ConfigParser, os, time
import boto3 # SDK for AWS (Amazon Lex)
import string

''' CONFIG '''
config = ConfigParser.ConfigParser()
config.read('config.cfg')
kb = config.get('CATEGORIES','KnowledgeBase')
categories_cfg = config.get('CATEGORIES','Cat').split(',')
df_token = config.get('NLUs','DialogflowDeveloperAccessToken')
wit_token = config.get('NLUs','WitToken')
lex_access_key_id = config.get('NLUs','AWSAccessKeyId')
lex_secret_key = config.get('NLUs','AWSSecretKey')
lex_region = config.get('NLUs','AWSRegion')

''' Amazon Lex SDK '''
lex_client = boto3.client(
    'lex-models',
    aws_access_key_id = lex_access_key_id,
    aws_secret_access_key = lex_secret_key,
    region_name = lex_region
)

''' Menu '''
menu = {}
i = 1;
for category in categories_cfg:
    menu[i] = category
    i = i+1

options=menu.keys()
options.sort()
for entry in options: 
    print str(entry) + ") " + menu[entry]
selection=raw_input("Please select: ") 
category = menu[int(selection)]

print "Which NLU engine would you use?"
print "1) Dialogflow"
print "2) Wit.ai"
print "3) Amazon Lex"
nlu_app=raw_input("Please select: "); 

print "Retrieving results from Knowledge Base ..."
''' Send SPARQL request '''
sparql = SPARQLWrapper(kb)
sparql.setQuery("""SELECT distinct(?label)
    WHERE {{
        GRAPH <http://3cixty.com/cotedazur/places> {{ ?uri a dul:Place }}
        ?uri rdfs:label ?label .
        ?uri locationOnt:businessType ?category .
        ?category skos:prefLabel ?label_category
        FILTER(?label_category = \"{0}\"@en)
    }}
    LIMIT 10000
""".format(category))
sparql.setReturnFormat(JSON)
results = sparql.query().convert()
list_entries = []

print "%d entities retrieved." % len(results["results"]["bindings"])

''' Build JSON '''
for result in results["results"]["bindings"]:
    entry = result["label"]["value"]#.encode('ascii', errors='ignore').decode('ascii')
	# removes special characters and ( ) that give errors in DF
    # entry = re.sub(r'[^\x00-\x7F]+','',F entry)
    entry = entry.replace("\"", "").replace("(", "").replace(")", "").replace("|", "").replace("<", "")
    list_entries.append({"value": entry})

print "%d entities selected" % len(list_entries)

if nlu_app == '1':
    ''' Send PUT request to Dialogflow'''
    print "Training Dialogflow ..."
    data = [{
        "name": category.lower(),
        "entries": list_entries
    }]

    json_data = json.dumps(data)
    headers = {
        "Authorization": "Bearer 47e9916631d644f49c6f381ea9b68e45",
        "Content-Type": "application/json"
    }
    r = requests.put("https://api.dialogflow.com/v1/entities?v=20150910", data=json_data, headers=headers)
    print "Status code: %s" % str(r.status_code)
    print "Description: \n %s" % str(r.content)

elif nlu_app == '2':
    ''' Send POST request to Wit.ai'''
    print "Training Wit.ai"
    # Create new entity
    print "- Creating new entity %s" % category.lower()
    data = {
        "id": category.lower(),
        "doc": "Entity about {0}. Generated automatically by FADE.".format(category.lower())
    }
    json_data = json.dumps(data)
    headers = {
        "Authorization": "Bearer " + wit_token,
        "Content-Type": "application/json"
    }
    r = requests.post("https://api.wit.ai/entities?v=20170307", data=json_data, headers=headers)
    print "Status code: %s" % str(r.status_code)
    print "Description: \n %s" % str(r.content)

    # Fill the entity with the values
    print "- Filling entity %s" % category.lower()
    headers = {
        "Authorization": "Bearer " + wit_token,
        "Content-Type": "application/json"
    }
    for entry in list_entries:
        json_entry = json.dumps(entry)
        r = requests.post("https://api.wit.ai/entities/" + category.lower() + "/values?v=20170307", data=json_entry, headers=headers)
        if r.status_code != 200:
            print "Entry: {0} | Status code: {1}".format(entry, str(r.status_code))
            print "Description: \n %s" % str(r.content)


elif nlu_app == '3':
    ''' Send PUT request to Amazon Lex'''
    print "Training Amazon Lex"
    response = lex_client.put_slot_type(
        name = category.lower(),
        description = "Slot about {0}. Generated automatically by FADE.".format(category.lower()),
        enumerationValues = list_entries,
        createVersion = True
    )
    print response
 
#    l = len(list_entries)
#    for i in xrange(0, 10000, l):
#        last = i+10000 if (i + 10000) < l else l
#        print last
#  */    data = list_entries[i:last]