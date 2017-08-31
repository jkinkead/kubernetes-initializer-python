"""
ResourceHandler is responsible for type-specific communication with the Kubernetes API.

This contains a parent class, as well as instantiations of that class for common types (in
Handlers).
"""

import logging

import kubernetes
from kubernetes.watch.watch import iter_resp_lines
from urllib3.exceptions import ReadTimeoutError

logger = logging.getLogger(__name__)


class ResourceHandler(object):
    """
    Class for handling API interactions for resources in Kubernetes.

    This is responsible for looking up all unitialized items for a given resource type, and for
    writing changes to those items back to the API.
    """

    def __init__(self, name, list_all_items, update_item, request_timeout_seconds=30):
        """
        Args:
            name: A user-friendly name for logging and error reporting.
            list_all_items: The Kubernetes API function used to look up all items for the handled
                resource. This function should accept one parameter, include_uninitialized="true".
                The list_{type}_for_all_namespaces methods in the python API meets these criteria.
            update_item: The Kubernetes API function used to post updated items to the
                Kubernetes server. This should accept name, namespace, and body parameters. Both the
                patch_namespaced_{type} and replace_namespaced_{type} methods in the python API meet
                these criteria.

                IMPORTANT NOTE: Per issue https://github.com/kubernetes/kubernetes/issues/49814,
                this *must* be a replace_ method, NOT a patch_ method.
            request_timeout_seconds: The amount of time to allow a `watch` request to be idle before
                reconnecting.
        """
        self.name = name
        self._list_all_items = list_all_items
        self._update_item = update_item
        self._request_timeout_seconds = request_timeout_seconds

    def list_all_items(self):
        """Returns the list of all items of the handled type in the Kubernetes server."""
        return self._list_all_items(include_uninitialized="true")

    def async_list_items(self, item_callback, error_callback):
        """
        Starts asynchronous reading of this handler's items using a 'watch' request.

        Args:
            item_callback: The function to call for each item of the handled type returned from the
                Kubernetes server. This will be invoked for each ADDED and MODIFIED event, but not
                for any DELETED event.
            error_callback: The function to invoke with any exception caught. This should log the
                exception, and re-invoke async_list_items if desired.

        Returns:
            The thread handling the watch request.
        """

        def handle_response(response):
            """Handles the response of a watch request."""
            watch = kubernetes.watch.Watch()
            return_type = watch.get_return_type(self._list_all_items)
            try:
                # This will leave a watch connection open indefinitely.
                for line in iter_resp_lines(response):
                    event = watch.unmarshal_event(line, return_type)
                    event_type = event['type']
                    if event_type == 'MODIFIED' or event_type == 'ADDED':
                        item = event['object']
                        item_callback(item)
                    else:
                        logger.debug('Ignored event type {} for item {}:{}'.format(
                            event_type, item.metadata.namespace, item.metadata.name))
            except ReadTimeoutError as timeout:
                # This is expected to occur when we hit _request_timeout below. We need to have a
                # request timeout, else we won't detect dropped network connections or restarted API
                # servers.
                logger.debug('Request timeout; ignoring.')
            except Exception as e:
                error_callback(e)
            finally:
                response.close()
                response.release_conn()
            # TODO(jkinkead): Figure out how to track threads and failures.
            self._list_all_items(
                include_uninitialized=True,
                watch=True,
                callback=handle_response,
                _request_timeout=self._request_timeout_seconds,
                _preload_content=False)

        return self._list_all_items(
            include_uninitialized=True,
            watch=True,
            callback=handle_response,
            _request_timeout=self._request_timeout_seconds,
            _preload_content=False)

    def update_item(self, item):
        """
        Sends an update for the given item to the Kubernetes API.

        Args:
            item: The updated item to send. This must have valid metadata.

        Returns:
            The response from the API server to the request.
        """
        return self._update_item(
            name=item.metadata.name, namespace=item.metadata.namespace, body=item)

    @staticmethod
    def pod_handler(api_client):
        """Constructs a handler for pods using the given kubernetes.client.api_client.ApiClient."""
        core_client = kubernetes.client.CoreV1Api(api_client)
        return ResourceHandler(
            name='pod',
            list_all_items=core_client.list_pod_for_all_namespaces,
            update_item=core_client.replace_namespaced_pod)

    @staticmethod
    def service_handler(api_client):
        """
        Constructs a handler for services using the given kubernetes.client.api_client.ApiClient.
        """
        core_client = kubernetes.client.CoreV1Api(api_client)
        return ResourceHandler(
            name='service',
            list_all_items=core_client.list_service_for_all_namespaces,
            update_item=core_client.replace_namespaced_service)

    @staticmethod
    def config_map_handler(api_client):
        """
        Constructs a handler for config maps using the given kubernetes.client.api_client.ApiClient.
        """
        core_client = kubernetes.client.CoreV1Api(api_client)
        return ResourceHandler(
            name='configmap',
            list_all_items=core_client.list_config_map_for_all_namespaces,
            update_item=core_client.replace_namespaced_config_map)

    @staticmethod
    def job_handler(api_client):
        """Constructs a handler for jobs using the given kubernetes.client.api_client.ApiClient."""
        batch_client = kubernetes.client.BatchV1Api(api_client)
        return ResourceHandler(
            name='job',
            list_all_items=batch_client.list_job_for_all_namespaces,
            update_item=batch_client.replace_namespaced_job)

    @staticmethod
    def deployment_handler(api_client):
        """
        Constructs a handler for deployments using the given kubernetes.client.api_client.ApiClient.
        """
        extensions_client = kubernetes.client.ExtensionsV1beta1Api(api_client)
        return ResourceHandler(
            name='deployment',
            list_all_items=extensions_client.list_deployment_for_all_namespaces,
            update_item=extensions_client.replace_namespaced_deployment)

    @staticmethod
    def daemon_set_handler(api_client):
        """
        Constructs a handler for daemonsets using the given kubernetes.client.api_client.ApiClient.
        """
        extensions_client = kubernetes.client.ExtensionsV1beta1Api(api_client)
        return ResourceHandler(
            name='daemonset',
            list_all_items=extensions_client.list_daemon_set_for_all_namespaces,
            update_item=extensions_client.replace_namespaced_daemon_set)

    @staticmethod
    def cron_job_handler(api_client):
        """
        Constructs a handler for cron jobs using the given kubernetes.client.api_client.ApiClient.
        """
        batch_alpha_client = kubernetes.client.BatchV2alpha1Api(api_client)
        return ResourceHandler(
            name='cronjob',
            list_all_items=batch_alpha_client.list_cron_job_for_all_namespaces,
            update_item=batch_alpha_client.replace_namespaced_cron_job)
