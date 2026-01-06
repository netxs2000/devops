import os
# Force env var before importing plugins
os.environ['USE_PYAIRBYTE'] = 'true'

from devops_collector.core.registry import PluginRegistry
# Trigger auto-discovery by importing the package (or reliance on PluginLoader if implemented, 
# but here we explicitly import to be sure, mimicking Loader behavior)
import devops_collector.plugins.jenkins

# client_cls = PluginRegistry.get_client_class('jenkins')
client_cls = PluginRegistry._clients.get('jenkins')
print(f"Jenkins Client Class: {client_cls.__name__}")

if client_cls.__name__ == 'AirbyteJenkinsClient':
    print("SUCCESS: Airbyte client registered.")
    exit(0)
else:
    print("FAILURE: Standard client registered.")
    exit(1)
