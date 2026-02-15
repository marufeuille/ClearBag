import functions_framework
from src.core import main

@functions_framework.http
def school_agent_http(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    print("Triggered via HTTP")
    try:
        main()
        return 'Success', 200
    except Exception as e:
        print(f"Error: {e}")
        return f'Error: {e}', 500
