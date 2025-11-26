import sys
import os
from io import BytesIO

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from werkzeug.serving import WSGIRequestHandler
import base64

def handler(event, context):
    """
    Netlify serverless function handler for Flask app
    """
    try:
        # Parse the incoming request
        path = event.get('path', '/')
        http_method = event.get('httpMethod', 'GET')
        headers = event.get('headers', {})
        query_params = event.get('queryStringParameters') or {}
        body = event.get('body', '')
        is_base64 = event.get('isBase64Encoded', False)
        
        # Decode base64 body if needed
        if is_base64 and body:
            body = base64.b64decode(body)
        elif isinstance(body, str):
            body = body.encode('utf-8')
        
        # Build query string
        query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
        
        # Build WSGI environ
        environ = {
            'REQUEST_METHOD': http_method,
            'SCRIPT_NAME': '',
            'PATH_INFO': path,
            'QUERY_STRING': query_string,
            'CONTENT_TYPE': headers.get('content-type', ''),
            'CONTENT_LENGTH': str(len(body)) if body else '0',
            'SERVER_NAME': headers.get('host', 'localhost').split(':')[0],
            'SERVER_PORT': '443',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': BytesIO(body) if body else BytesIO(b''),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
        }
        
        # Add headers to environ
        for key, value in headers.items():
            key_upper = key.upper().replace('-', '_')
            if key_upper not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                environ[f'HTTP_{key_upper}'] = value
        
        # Create response container
        response_data = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html'
            },
            'body': ''
        }
        
        def start_response(status, response_headers, exc_info=None):
            response_data['statusCode'] = int(status.split()[0])
            for header, value in response_headers:
                response_data['headers'][header] = value
        
        # Call Flask app
        app_iter = app(environ, start_response)
        response_data['body'] = b''.join(app_iter).decode('utf-8')
        
        return response_data
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in serverless function: {error_trace}")
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': f'{{"error": "Internal Server Error", "message": "{str(e)}"}}'
        }
