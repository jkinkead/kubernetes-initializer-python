"""
AsyncResourceHandler is responsible for type-specific communication with the Kubernetes API.

This handles items using a "watch" request, rather than polling.

This contains a parent class, as well as instantiations of that class for common types (in
Handlers).
"""

import kubernetes
from kubernetes.watch.watch import iter_resp_lines


class AsyncResourceHandler(object):
    """
    Class for handling API interactions for resources in Kubernetes.

    This is responsible for looking up all unitialized items for a given resource type, and for
    writing changes to those items back to the API.
    """

    def __init__(self, name, list_all_items, update_item):
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
        """
        self.name = name
        self._list_all_items = list_all_items
        self._update_item = update_item

    def async_process_items(self, initializer_controller, resource_controller):
        """Returns the thread handling of all items of the handled type in the Kubernetes server."""

        # Async calls take a callback which handles the response.
        # TODO(jkinkead): Figure out how to handle errors in async procesing -
        # pass error handler into async_process_items?
        def handle_response(response):
            watch = kubernetes.watch.Watch()
            return_type = watch.get_return_type(self._list_all_items)
            try:
                for line in iter_resp_lines(response):
                    event = watch.unmarshal_event(line, return_type)
                    event_type = event['type']
                    item = event['object']
                    print('{} for object name {}'.format(event_type, item.metadata.name))
                    if event_type == 'MODIFIED' or event_type == 'ADDED':
                        initializer_controller.handle_single_item(resource_controller, item)
                        print('doned')
                    else:
                        print('noned')

                print('really doned')
            finally:
                response.close()
                response.release_conn()
            print('handler doned')

        return self._list_all_items(
            include_uninitialized=True,
            watch=True,
            callback=handle_response,
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
        print('yeah')
        return AsyncResourceHandler(
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
        return AsyncResourceHandler(
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
