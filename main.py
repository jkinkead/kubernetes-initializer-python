#!/usr/bin/env python3
"""Main script for running the label initializer."""

import argparse
import logging

import kubernetes

from labelizer import LabelController, JobHandler


def main():
    parser = argparse.ArgumentParser(
        description='Requires labels on resources, and propagate labels to child resources.')
    parser.add_argument(
        '--kubeconfig',
        help='If set, use the default kubeconfig file to find '
        'credentials and API information. If unset, cluster environment variables '
        'are used.',
        action='store_true')
    parser.add_argument(
        '--name',
        required=True,
        help='The name of this initializer. This is the name that is '
        'looked for in the "initializers" list for handled resources.')
    parser.add_argument(
        '--verbose', '-v', help='Increase verbosity. May be repeated.', action='count', default=0)
    args = parser.parse_args()

    if args.verbose >= 1:
        base_log_level = logging.DEBUG
    else:
        base_log_level = logging.INFO
    logging.basicConfig(
        level=base_log_level,
        format='%(asctime)s [%(levelname)s] %(name)s:%(lineno)s - %(message)s')

    if args.verbose < 2:
        # Reduce log level for dependency libraries.
        logging.getLogger('kubernetes').setLevel(logging.INFO)

    # Load the Kubernetes configuration, either from the local file, or from the cluster
    # environment.
    if args.kubeconfig:
        kubernetes.config.load_kube_config()
    else:
        kubernetes.config.load_incluster_config()

    api_client = kubernetes.client.api_client.ApiClient()
    # For fetching pods, configmaps, and services. Others, too!
    core_client = kubernetes.client.CoreV1Api(api_client)
    # For fetching jobs.
    batch_client = kubernetes.client.BatchV1Api(api_client)
    # For fetching daemonsets & deployments.
    extensions_client = kubernetes.client.ExtensionsV1beta1Api(api_client)

    # List of resource calls we're monitoring.
    # TODO(jkinkead): Take from flags.
    handled_resource_calls = [
        batch_client.list_job_for_all_namespaces,
        core_client.list_pod_for_all_namespaces,
        extensions_client.list_daemon_set_for_all_namespaces,
        extensions_client.list_deployment_for_all_namespaces,
    ]

    handlers = [LabelController(initializer_name=args.name, handler=JobHandler(api_client))]

    # TODO(jkinkead): Loop and look for new resources frequently.
    for handler in handlers:
        # TODO(jkinkead): Take the labels from a flag.
        handler.handle_update()

    print('Done.')


if __name__ == "__main__":
    main()
