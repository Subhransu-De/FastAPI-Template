from endpoint_test.client import EndpointTestClient
from endpoint_test.config import EndpointTestSettings


def before_all(context):
    context.settings = EndpointTestSettings.from_environment()
    context.endpoint_client = EndpointTestClient(context.settings)
    context.endpoint_client.wait_until_ready()
    context.access_token = context.endpoint_client.create_access_token()


def after_all(context):
    endpoint_client = getattr(context, "endpoint_client", None)
    if endpoint_client is not None:
        endpoint_client.close()
