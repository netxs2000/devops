import os
# Force env var before importing plugins
os.environ['USE_PYAIRBYTE'] = 'true'

from devops_collector.core.registry import PluginRegistry
import devops_collector.plugins.jira

client_cls = PluginRegistry._clients.get('jira')
print(f"Jira Client Class: {client_cls.__name__}")

if client_cls.__name__ == 'AirbyteJiraClient':
    print("SUCCESS: Airbyte client registered for Jira.")
    exit(0)
else:
    print(f"FAILURE: Unexpected client registered: {client_cls.__name__}")
    exit(1)
