import json
from decimal import Decimal
import time
import logging
import os
import urllib.request
import boto3
from boto3.dynamodb.conditions import Key

# Load environment variables
CHAT_HISTORY_TABLE = os.environ.get('CHAT_HISTORY_TABLE')
WEBSOCKET_API_URL = os.environ.get('WEBSOCKET_API_URL')

# Load OpenAI API key from environment variables
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize resources and clients outside functions for reusability
dynamodb = boto3.resource('dynamodb')
apigateway_client = boto3.client(
    'apigatewaymanagementapi',
    endpoint_url=WEBSOCKET_API_URL
)

def connect(event, context):
    connection_id = event['requestContext']['connectionId']
    table = dynamodb.Table(CHAT_HISTORY_TABLE)

    try:
        # Add connection ID to the table (can be used for future lookups)
        table.put_item(Item={
            'ConnectionId': connection_id,
            'Timestamp': int(time.time())
        })
        return {"statusCode": 200}
    except Exception as e:
        print(f"Error in connect: {e}")
        return {"statusCode": 500, "body": "Failed to connect"}


def disconnect(event, context):
    connection_id = event['requestContext']['connectionId']
    table = dynamodb.Table(CHAT_HISTORY_TABLE)

    try:
        # Remove connection ID
        table.delete_item(Key={
            'ConnectionId': connection_id
        })
        return {"statusCode": 200}
    except Exception as e:
        print(f"Error in disconnect: {e}")
        return {"statusCode": 500, "body": "Failed to disconnect"}


def send_message(event, context):
    # print(f"Web socket: {WEBSOCKET_API_URL}.")
    table = dynamodb.Table(CHAT_HISTORY_TABLE)
    connection_id = event['requestContext']['connectionId']

    try:
        body = json.loads(event['body'])
        user_id = body.get('userId', '').strip()  # Extract UserId from the frontend
        user_message = body.get('message', '').strip()

        if not user_id or not user_message:
            return {"statusCode": 400, "body": "Invalid UserId or message"}

        # Example: Process user message
        ai_response = f"AI response to: {user_message}"

        # Save chat to DynamoDB
        table.put_item(Item={
            'ConnectionId': connection_id,
            'UserId': user_id,  # Store UserId
            'UserMessage': user_message,
            'AIResponse': ai_response,
            'Timestamp': int(time.time())
        })

        # Send AI response back to user
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"response": ai_response})
        )
        return {"statusCode": 200}
    except apigateway_client.exceptions.GoneException:
        print(f"Connection {connection_id} is stale.")
        return {"statusCode": 410, "body": "Connection gone"}
    except Exception as e:
        print(f"Error in send_message: {e}")
        return {"statusCode": 500, "body": "Failed to send message"}

def mercurio_data(event, context):
    # print(f"Web socket: {WEBSOCKET_API_URL}.")
    table = dynamodb.Table(CHAT_HISTORY_TABLE)
    connection_id = event['requestContext']['connectionId']

    try:
        body = json.loads(event['body'])
        user_id = body.get('userId', '').strip()  # Extract UserId from the frontend
        user_message = body.get('message', '').strip()

        if not user_id or not user_message:
            return {"statusCode": 400, "body": "Invalid UserId or message"}

        # Example: Process user message
        ai_response = f"AI response to: {user_message}"

        # Save chat to DynamoDB
        table.put_item(Item={
            'ConnectionId': connection_id,
            'UserId': user_id,  # Store UserId
            'UserMessage': user_message,
            'AIResponse': ai_response,
            'Timestamp': int(time.time())
        })

        # Send AI response back to user
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"response": ai_response})
        )
        return {"statusCode": 200}
    except apigateway_client.exceptions.GoneException:
        print(f"Connection {connection_id} is stale.")
        return {"statusCode": 410, "body": "Connection gone"}
    except Exception as e:
        print(f"Error in send_message: {e}")
        return {"statusCode": 500, "body": "Failed to send message"}

def send_websocket_message(connection_id, message):
    try:
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        print(f"Message sent to WebSocket connection ID {connection_id}.")
    except Exception as e:
        print(f"Failed to send WebSocket message: {e}")

# def mercurio_chat(event, context):
#     try:
#         # Log the incoming event for debugging
#         print(f"Event: {event}")
#         # Parse the incoming request
#         body = json.loads(event.get("body", "{}"))
#         identifier = body.get("identifier")
#         message = body.get("message")
#         connection_id = event['requestContext']['connectionId']  #body.get("connectionId")

#         if not identifier or not message or not connection_id:
#             return {
#                 "statusCode": 400,
#                 "body": json.dumps({"error": "identifier, message, and connectionId are required."}),
#                 "headers": {
#                     "Access-Control-Allow-Origin": "*",
#                     "Access-Control-Allow-Headers": "Content-Type",
#                     "Access-Control-Allow-Methods": "POST,OPTIONS"
#                 }
#             }

#         # Send a WebSocket message back to the client
#         websocket_message = {
#             "action": "response",
#             "identifier": identifier,
#             "message": message
#         }
#         send_websocket_message(connection_id, websocket_message)

#         # Return a response for the REST API call
#         response = {
#             "status": "success",
#             "details": "WebSocket message sent successfully.",
#             "identifier": identifier
#         }
#         return {
#             "statusCode": 200,
#             "body": json.dumps(response),
#             "headers": {
#                 "Access-Control-Allow-Origin": "*",
#                 "Access-Control-Allow-Headers": "Content-Type",
#                 "Access-Control-Allow-Methods": "POST,OPTIONS"
#             }
#         }

#     except Exception as e:
#         logger.error(f"Error in mercurio_chat: {e}")
#         return {
#             "statusCode": 500,
#             "body": json.dumps({"error": str(e)}),
#             "headers": {
#                 "Access-Control-Allow-Origin": "*",
#                 "Access-Control-Allow-Headers": "Content-Type",
#                 "Access-Control-Allow-Methods": "POST,OPTIONS"
#             }
#         }
    
def mercurio_chat(event, context):
    table = dynamodb.Table(CHAT_HISTORY_TABLE)

    try:
        # Log the incoming event for debugging
        print(f"Event: {event}")
        
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        identifier = body.get('identifier', '').strip()
        message = body.get('message', '').strip()

        if not identifier or not message:
            return {
                "statusCode": 400,
                "body": "Missing identifier or message",
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Methods": "POST,OPTIONS"
                }
            }

        # Generate a GUID for ConnectionId
        # connection_id = str(uuid.uuid4())
        # Query DynamoDB for connection ID
        response = table.query(
            IndexName='UserId-Timestamp-index',  # Replace with your index name
            KeyConditionExpression=Key('UserId').eq(identifier),
            ScanIndexForward=False,  # Sorts in descending order (latest Timestamp first)
            Limit=1  # Only fetch the latest entry
        )
        connections = response.get('Items', [])

        if not connections:
            return {
                "statusCode": 404,
                "body": "No active WebSocket connection found for the user.",
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Methods": "POST,OPTIONS"
                }
            }
        connection_id = connections[0]['ConnectionId']
        # connection_id = identifier
        
        # Log the connection Id for debugging
        print(f"Connection Id: {connection_id}")        
        
        # Add logic to communicate to ChatGPT# Call ChatGPT API to get AI response
        ai_response = call_chatgpt_api(message)
        print(f"ChatGPT Response: {ai_response}")
        
        # Save to DynamoDB
        timestamp = int(time.time())
        table.put_item(Item={
            'ConnectionId': connection_id,
            'UserId': identifier,
            'UserMessage': message,
            'AIResponse': ai_response, 
            'Timestamp': timestamp
        })
                
        # Send a WebSocket message back to the client
        if message == "Initial Message":
            print("Skipping processing for Initial Message.")
        else:
            # Log the connection Id for debugging
            print(f"Sending websocket to Connection Id: {connection_id}")        
            # ai_response = f"AI response to: {message}"
            websocket_message = {
                "action": "response",
                "route": "mercurio_data",
                "identifier": identifier,
                "message": ai_response
            }
            send_websocket_message(connection_id, websocket_message)
            print(f"send_websocket_message sent")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": "Done",
                "connectionId": connection_id,
                "timestamp": timestamp
            }),
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            }
        }
    except Exception as e:
        print(f"Error in mercurio_chat: {e}")
        return {
            "statusCode": 500,
            "body": "Failed to save chat",
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            }
        }
        
def mercurio_analyzer(event, context):
    table = dynamodb.Table(CHAT_HISTORY_TABLE)

    try:
        # Log the incoming event for debugging
        print(f"Event: {event}")
        
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        identifier = body.get('identifier', '').strip()
        message = body.get('message', '').strip()

        if not identifier or not message:
            return {
                "statusCode": 400,
                "body": "Missing identifier or message",
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Methods": "POST,OPTIONS"
                }
            }

        # Generate a GUID for ConnectionId
        # connection_id = str(uuid.uuid4())
        # Query DynamoDB for connection ID
        response = table.query(
            IndexName='UserId-Timestamp-index',  # Replace with your index name
            KeyConditionExpression=Key('UserId').eq(identifier),
            ScanIndexForward=False,  # Sorts in descending order (latest Timestamp first)
            Limit=1  # Only fetch the latest entry
        )
        connections = response.get('Items', [])

        if not connections:
            return {
                "statusCode": 404,
                "body": "No active WebSocket connection found for the user.",
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Methods": "POST,OPTIONS"
                }
            }
        connection_id = connections[0]['ConnectionId']
        # connection_id = identifier
        
        # Log the connection Id for debugging
        print(f"Connection Id: {connection_id}")        
        
        # Add logic to communicate to ChatGPT# Call ChatGPT API to get AI response
        ai_response = call_chatgpt_api(message)
        print(f"ChatGPT Response: {ai_response}")
        
        # Save to DynamoDB
        timestamp = int(time.time())
        table.put_item(Item={
            'ConnectionId': connection_id,
            'UserId': identifier,
            'UserMessage': message,
            'AIResponse': ai_response, 
            'Timestamp': timestamp
        })
                
        # Send a WebSocket message back to the client
        if message == "Initial Message":
            print("Skipping processing for Initial Message.")
        else:
            # Log the connection Id for debugging
            print(f"Sending websocket to Connection Id: {connection_id}")        
            # ai_response = f"AI response to: {message}"
            websocket_message = {
                "action": "response",
                "route": "mercurio_anali",
                "identifier": identifier,
                "message": ai_response
            }
            send_websocket_message(connection_id, websocket_message)
            print(f"send_websocket_message sent")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": "Done",
                "connectionId": connection_id,
                "timestamp": timestamp
            }),
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            }
        }
    except Exception as e:
        print(f"Error in mercurio_chat: {e}")
        return {
            "statusCode": 500,
            "body": "Failed to save chat",
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            }
        }
        
def call_chatgpt_api(user_message):
    """Call the OpenAI API using urllib to avoid external libraries."""
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4-1106-preview",
            "messages": [{"role": "user", "content": user_message}],
            "temperature": 0.7
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(OPENAI_API_URL, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req) as response:
            result = response.read()
            result_json = json.loads(result)
            return result_json['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling ChatGPT API: {e}")
        return "I'm sorry, but I'm unable to process your request at the moment."

def decimal_to_float(obj):
    """Helper function to convert Decimal to float."""
    if isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj

def query_chat_history(event, context):
    user_id = event.get('queryStringParameters', {}).get('userId', '').strip()
    print(f"User Id: {user_id}")
    table = dynamodb.Table(CHAT_HISTORY_TABLE)

    if not user_id:
        return {
            "statusCode": 400,
            "body": "Missing userId parameter",
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET,OPTIONS"
            }
        }

    try:
        # Query chat history by UserId
        response = table.query(
            IndexName='UserId-Timestamp-index',
            KeyConditionExpression=Key("UserId").eq(user_id)
        )

        items = response.get('Items', [])
        # Convert items to JSON serializable
        serializable_items = decimal_to_float(items)

        return {
            "statusCode": 200,
            "body": json.dumps(serializable_items),
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET,OPTIONS"
            }
        }
    except Exception as e:
        print(f"Error in query_chat_history: {e}")
        return {"statusCode": 500, "body": "Failed to query chat history"}
