import boto3
import cfnresponse
import time
import json
import requests
import os
from os import environ

#Global variables used in composing the URL as in CAPI
accept = "application/json"
content_type = "application/json"

def lambda_handler (event, context):
    
    #The event that is sent from CloudFormation. Displayed in CloudWatch logs.
    print (event)
    
    #Creating the callEvent dictionary that will be identical with a Swagger API call
    callEvent = {}
    if "provider" in event['ResourceProperties']:
        callEvent["provider"] = event['ResourceProperties']["provider"]
    if "region" in event['ResourceProperties']:
        callEvent["region"] = event['ResourceProperties']["region"]
    if "awsAccountId" in event['ResourceProperties']:
        callEvent["awsAccountId"] = event['ResourceProperties']["awsAccountId"]
    if "vpcId" in event['ResourceProperties']:
        callEvent["vpcId"] = event['ResourceProperties']["vpcId"]
    if "vpcCidrs" in event['ResourceProperties']:
        callEvent["vpcCidrs"] = event['ResourceProperties']["vpcCidrs"]
        
    print ("callEvent that is used as the actual API Call is bellow:")
    print (callEvent)
        
    subscription_id = event['ResourceProperties']["subscriptionId"]
    print ("Subscription ID is: " + str(subscription_id))
    
    #Additional global variables used in methods for URL composing or as credentials to login.
    global stack_name
    global base_url
    global x_api_key
    global x_api_secret_key 
    base_url = event['ResourceProperties']['baseURL']
    x_api_key =  RetrieveSecret("redis/x_api_key")["x_api_key"]
    x_api_secret_key =  RetrieveSecret("redis/x_api_secret_key")["x_api_secret_key"]
    stack_name = str(event['StackId'].split("/")[1])
    responseData = {}
    
    #Creating the CloudFormation response block. Presuming the status as SUCCESS. If an error occurs, the status is changed to FAILED.
    responseStatus = 'SUCCESS'
    responseURL = event['ResponseURL']
    responseBody = {'Status': responseStatus,
                    'PhysicalResourceId': context.log_stream_name,
                    'StackId': event['StackId'],
                    'RequestId': event['RequestId'],
                    'LogicalResourceId': event['LogicalResourceId']
                    }
                    
    #If the action of CloudFormation is Create stack                
    if event['RequestType'] == "Create":
        try:
            #The API Call the creates the Peering
            responseValue = PostPeering(callEvent, subscription_id)
            print (responseValue)

            try:
                if "processing-error" in str(responseValue):           
                    peer_error = GetPeeringError (responseValue['links'][0]['href'])
                    responseStatus = 'FAILED'
                    reason = str(peer_error)
                    if responseStatus == 'FAILED':
                        responseBody.update({"Status":responseStatus})
                        if "Reason" in str(responseBody):
                            responseBody.update({"Reason":reason})
                        else:
                            responseBody["Reason"] = reason
                        GetResponse(responseURL, responseBody)

                #Retrieving Peering ID and Peering Description to populate Outputs tab of the stack
                peer_id, peer_description = GetPeeringId (responseValue['links'][0]['href'])
                print ("New peering id is: " + str(peer_id))
                print ("Description for Peering with id " + str(peer_id) + " is: " + str(peer_description))
                
                responseData.update({"SubscriptionId":str(subscription_id), "PeeringId":str(peer_id), "PeeringDescription":str(peer_description), "PostCall":str(callEvent)})
                responseBody.update({"Data":responseData})
                GetResponse(responseURL, responseBody)
            
            except:
                #If any error is encounter in the "try" block, then a function will catch the error and throw it back to CloudFormation as a failure reason.
                peer_error = GetPeeringError (responseValue['links'][0]['href'])
                responseStatus = 'FAILED'
                reason = str(peer_error)
                if responseStatus == 'FAILED':
                    responseBody.update({"Status":responseStatus})
                    if "Reason" in str(responseBody):
                        responseBody.update({"Reason":reason})
                    else:
                        responseBody["Reason"] = reason
                    GetResponse(responseURL, responseBody)

        except:
                #This except block is triggered only for wrong base_url or wrong credentials.
                responseStatus = 'FAILED'
                reason = 'Please check if the base_url or the credentials set in Secrets Manager are wrong.'
                if responseStatus == 'FAILED':
                    responseBody.update({"Status":responseStatus})
                    if "Reason" in str(responseBody):
                        responseBody.update({"Reason":reason})
                    else:
                        responseBody["Reason"] = reason
                    GetResponse(responseURL, responseBody)
    
    #If the action of CloudFormation is Update stack            
    if event['RequestType'] == "Update":
        #Retrieve parameters from Outputs tab of the stack and appending the dictionary with the PhysicalResourceId which is a required parameter for Update actions
        PhysicalResourceId = event['PhysicalResourceId']
        responseBody.update({"PhysicalResourceId":PhysicalResourceId})
        
        cf_sub_id, cf_event, cf_peer_id, cf_peer_description = CurrentOutputs()
        cf_event = cf_event.replace("\'", "\"")
        cf_event = json.loads(cf_event)
        
        #Checking if vpcCidrs suffered any modifications. If it does, make the API call and update the Outputs, else response back to CF
        if callEvent["vpcCidrs"] != cf_event["vpcCidrs"]:
            responseValue = PutPeering(cf_sub_id, cf_peer_id, callEvent)
            cf_event.update(callEvent)
            print (cf_event)
            responseData.update({"SubscriptionId":str(cf_sub_id), "PeeringId":str(cf_peer_id), "PeeringDescription":str(cf_peer_description), "PostCall":str(cf_event)})
            responseBody.update({"Data":responseData})
            GetResponse(responseURL, responseBody)
        
        else:
            responseData.update({"SubscriptionId":str(cf_sub_id), "PeeringId":str(cf_peer_id), "PeeringDescription":str(cf_peer_description), "PostCall":str(cf_event)})
            responseBody.update({"Data":responseData})
            GetResponse(responseURL, responseBody)
    
    #If the action of CloudFormation is Delete stack            
    if event['RequestType'] == "Delete":
        #If the parameters cannot be retrieved, this means the stack was already deleted
        try:
            cf_sub_id, cf_event, cf_peer_id, cf_peer_description = CurrentOutputs()
        except:
            responseStatus = 'SUCCESS'
            responseBody.update({"Status":responseStatus})
            GetResponse(responseURL, responseBody)
        
        #Check if the current peering that is wanted to be deleted is among the other peering that the subscription have. If the Peering exists -> Success and delete, otherwise -> Fail    
        all_peers = GetPeering(cf_sub_id)
        if str(cf_peer_id) in str(all_peers):
            try:
                responseValue = DeletePeering(cf_sub_id, cf_peer_id)
                responseData.update({"SubscriptionId":str(cf_sub_id), "PeeringId":str(cf_peer_id), "PeeringDescription":str(cf_peer_description), "PostCall":str(cf_event)})
                print (responseData)
                responseBody.update({"Data":responseData})
                GetResponse(responseURL, responseBody)
            except:
                responseStatus = 'FAILED'
                reason = "Unable to delete peering"
                if responseStatus == 'FAILED':
                    responseBody.update({"Status":responseStatus})
                    if "Reason" in str(responseBody):
                        responseBody.update({"Reason":reason})
                    else:
                        responseBody["Reason"] = reason
                    GetResponse(responseURL, responseBody)
        else:
            print("Peering does not exists")
            GetResponse(responseURL, responseBody)

#This function retrieves x_api_key and x_api_secret_key from Secrets Manager service and returns them in the function as variables                    
def RetrieveSecret(secret_name):
    headers = {"X-Aws-Parameters-Secrets-Token": os.environ.get('AWS_SESSION_TOKEN')}

    secrets_extension_endpoint = "http://localhost:2773/secretsmanager/get?secretId=" + str(secret_name)
    r = requests.get(secrets_extension_endpoint, headers=headers)
    secret = json.loads(r.text)["SecretString"]
    secret = json.loads(secret)

    return secret

#This function retrieves the parameters from Outputs tab of the stack to be used later    
def CurrentOutputs():
    cloudformation = boto3.client('cloudformation')
    cf_response = cloudformation.describe_stacks(StackName=stack_name)
    for output in cf_response["Stacks"][0]["Outputs"]:
        if "SubscriptionId" in str(output): 
            cf_sub_id = output["OutputValue"]

        if "PostCall" in str(output): 
            cf_event = output["OutputValue"]

        if "PeeringId" in str(output): 
            cf_peer_id = output["OutputValue"]

        if "PeeringDescription" in str(output): 
            cf_peer_description = output["OutputValue"]
            
    print ("cf_sub_id is: " + str(cf_sub_id))
    print ("cf_event is: " + str(cf_event))
    print ("cf_peer_id is: " + str(cf_peer_id))
    print ("cf_peer_description is: " + str(cf_peer_description))
    return cf_sub_id, cf_event, cf_peer_id, cf_peer_description

#Makes the POST API call for Peering    
def PostPeering (event, subscription_id):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings"
    
    response = requests.post(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key, "Content-Type":content_type}, json = event)
    response_json = response.json()
    print ("This is the response after POST call: " + str(response_json))

    time.sleep(5)
    response = requests.get(response_json['links'][0]['href'], headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    response_json = response.json()
    print ("This is the response 5 seconds after POST call: " + str(response_json))

    return response_json
    Logs(response_json)

#Returns all the information about Peerings under the specified Subscription
def GetPeering (subscription_id):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings"
    response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    response = response.json()
    
    while "vpcPeeringId" not in str(response):
        time.sleep(1)
        response = requests.get(response['links'][0]['href'], headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
        response = response.json()
    print (str(response))
        
    return response
    Logs(response)

#Returns the Peering ID used for other API calls
def GetPeeringId (url):
    response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    response = response.json()
    print (str(response))
    
    while "resourceId" not in str(response):
        time.sleep(1)
        response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
        response = response.json()
    print (str(response))

    peer_id = response["response"]["resourceId"]
    peer_description = response["description"]
    return peer_id, peer_description

#Makes the PUT API call on Update stack    
def PutPeering (subscription_id, peering_id, callEvent):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings/" + str(peering_id)
    
    response = requests.put(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key, "Content-Type":content_type}, json = callEvent)
    response_json = response.json()
    return response_json
    Logs(response_json)

#Deletes Peering
def DeletePeering (subscription_id, peering_id):
    url = base_url + "/v1/subscriptions/" + str(subscription_id) + "/peerings/" + str(peering_id)
    
    response_peer = requests.delete(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    Logs(response_peer.json())

#Returns the error message of a wrong peering    
def GetPeeringError (url):
    response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    response = response.json()

    while "processing-error" not in str(response):
        time.sleep(1)
        response = requests.get(url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
        response = response.json()

    peer_error_description = response["response"]["error"]["description"]
    return peer_error_description
 
#Send response back to CloudFormation      
def GetResponse(responseURL, responseBody): 
    responseBody = json.dumps(responseBody)
    req = requests.put(responseURL, data = responseBody)
    print ('RESPONSE BODY:n' + responseBody)

#Checks if there is an error in the description    
def Logs(response_json):
    error_url = response_json['links'][0]['href']
    error_message = requests.get(error_url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
    error_message_json = error_message.json()
    if 'description' in error_message_json:
        while response_json['description'] == error_message_json['description']:
            error_message = requests.get(error_url, headers={"accept":accept, "x-api-key":x_api_key, "x-api-secret-key":x_api_secret_key})
            error_message_json = error_message.json()
        print(error_message_json)
    else:
        print ("No errors")
