from unittest.mock import Mock

from main import school_agent_http


def test_cloud_function():
    print("Testing Cloud Function Entry Point...")

    # Mock Flask Request
    request = Mock()
    request.get_json.return_value = {}
    request.args = {}

    # Call the function
    # Note: This will actually run the main logic, so ensure it doesn't do destructive things
    # or rely on cloud-only env vars if they aren't set locally.
    # Since we are running in the same env, it should work if .env is loaded.

    try:
        response = school_agent_http(request)
        print(f"Function returned: {response}")
    except Exception as e:
        print(f"Function failed with error: {e}")


if __name__ == "__main__":
    test_cloud_function()
