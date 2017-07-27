import logging

from .rejection import Rejection

logger = logging.getLogger(__name__)


class LabelController(object):
    """
    LabelController is responsible for delegating validation logic to a type-specific handler.

    This handles the core admission controller logic, matching the initializer list against the
    initializer name, while delegating lookup, update, and label logic to the sub-controller.

    The entry method is handle_update, which runs a single lookup-update loop on all items returned
    by the handler.
    """

    def __init__(self, initializer_name, handler):
        """
        Builds a LabelController handling the given initializer name with the given handler.

        Args:
            initializer_name: The name of the initializer in the InitializerConfiguration. Only
                resources returned by the handler that have this name in their pending initializers
                will be modified (per the dynamic admission controller contract).
            handler: A ResourceHandler to delegate update logic to.
        """
        self.initializer_name = initializer_name
        self.handler = handler

    def handle_update(self):
        """Finds and updates all items in need of update, using the wrapped handler."""
        result = self.handler.list_all_items()
        logger.debug('Got %s results from %s lookup.', len(result.items), self.handler.name)
        # TODO: Validate `result`.
        for item in result.items:
            initializers = item.metadata.initializers
            if (initializers and initializers.pending
                    and initializers.pending[0].name == self.initializer_name):
                logger.debug('Processing %s %s:%s.', self.handler.name, item.metadata.namespace,
                             item.metadata.name)
                try:
                    updated_item = self.handler.handle_item(item)
                    logger.debug('Handler returned a value.')
                except Rejection as rejection:
                    logger.debug('Handler rejected.')
                    # Update the unmodified item, using the provided rejection reason.
                    updated_item = item
                    updated_item.metadata.initializers.result = rejection.status
                # Copy in the old initializer pending list, minus the first item.
                updated_item.metadata.initializers.pending = initializers.pending[1:]
                self.handler.patch_item(updated_item)
