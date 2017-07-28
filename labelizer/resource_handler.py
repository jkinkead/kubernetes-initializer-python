import kubernetes

from .rejection import Rejection


class ResourceHandler(object):
    """
    Class for handling unitialized resources in Kubernetes.

    This is responsible for any updates or rejections to the object. Subclasses should override the
    handle_item method as well as provide the appropriate list and patch functions to the
    constructor.
    """

    def __init__(self, name, list_item_for_all_namespaces, patch_namespaced_item):
        """
        Args:
            name: A user-friendly name for logging and error reporting.
            list_item_for_all_namespaces: The Kubernetes API function used to look up all items for
                the handled resource. This should accept the include_uninitialized="true" parameter.
            patch_namespaced_item: The Kubernetes API function used to post updated items to the
                Kubernetes server.
        """
        self.name = name
        self.list_item_for_all_namespaces = list_item_for_all_namespaces
        self.patch_namespaced_item = patch_namespaced_item

    def list_all_items(self):
        """Returns the list of all items of the handled type in the Kubernetes server."""
        return self.list_item_for_all_namespaces(include_uninitialized="true")

    def patch_item(self, item):
        """
        Sends a PATCH request for the given item to the Kubernetes API.

        Args:
            item: The updated item to patch in. This must have valid metadata.

        Returns:
            The response from the API server to the patch request.
        """
        return self.patch_namespaced_item(
            name=item.metadata.name, namespace=item.metadata.namespace, body=item)

    def handle_item(self, item):
        """
        Given a resource item, either return the item for admission, or raise a Rejection.

        The caller is responsible for updating the item's `initializers` object, so it should be
        returned unchanged.

        Args:
            item: The item under consideration by the admission controller.

        Returns:
            The item to post back to the Kubernetes API. This should be the provided item, with any
            modifications made.

        Raises:
            Rejection: The reason for rejecting the item from the Kubernetes cluster. If this is
                raised, the caller will populate `initializers.result` with a `Failed` value holding
                the contents of this exception.
        """
        raise Rejection(
            message='Handler not implemented; rejecting {}.'.format(item.metadtata.name),
            reason='RejectAll')


class PodHandler(ResourceHandler):
    """Class which handles looking up pods. Child classes should override handle_item."""

    def __init__(self, api_client):
        """Constructs a handler for pods using the given ApiClient."""
        core_client = kubernetes.client.CoreV1Api(api_client)
        super().__init__(
            name='pod',
            list_item_for_all_namespaces=core_client.list_pod_for_all_namespaces,
            patch_namespaced_item=core_client.patch_namespaced_pod)


class JobHandler(ResourceHandler):
    """Class which handles looking up jobs. Child classes should override handle_item."""

    def __init__(self, api_client):
        """Constructs a handler for jobs using the given ApiClient."""
        batch_client = kubernetes.client.BatchV1Api(api_client)
        super().__init__(
            name='job',
            list_item_for_all_namespaces=batch_client.list_job_for_all_namespaces,
            patch_namespaced_item=batch_client.patch_namespaced_job)


class DeploymentHandler(ResourceHandler):
    """Class which handles looking up deployments. Child classes should override handle_item."""

    def __init__(self, api_client):
        """Constructs a handler for deployments using the given ApiClient."""
        extensions_client = kubernetes.client.ExtensionsV1beta1Api(api_client)
        super().__init__(
            name='deployment',
            list_item_for_all_namespaces=batch_client.list_deployment_for_all_namespaces,
            patch_namespaced_item=batch_client.patch_namespaced_deployment)


class DaemonSetHandler(ResourceHandler):
    """Class which handles looking up daemonsets. Child classes should override handle_item."""

    def __init__(self, api_client):
        """Constructs a handler for daemonsets using the given ApiClient."""
        batch_client = kubernetes.client.ExtensionsV1beta1Api(api_client)
        super().__init__(
            name='daemonset',
            list_item_for_all_namespaces=batch_client.list_daemon_set_for_all_namespaces,
            patch_namespaced_item=batch_client.patch_namespaced_daemon_set)
