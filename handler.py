import json
from decimal import Decimal
import time
import os
import boto3
from boto3.dynamodb.conditions import Key

# Load environment variables
CHAT_HISTORY_TABLE = os.environ.get('CHAT_HISTORY_TABLE')
WEBSOCKET_API_URL = os.environ.get('WEBSOCKET_API_URL')

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
