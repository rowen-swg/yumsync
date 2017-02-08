import json
import os

metadata_path = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'metadata.json')
with open(metadata_path) as metadata_file:
    metadata = json.load(metadata_file)
if 'version' in metadata:
    __version__ = metadata['version']
else:
    raise RuntimeError("Unable to find version in {0}".format(metadata_path))
