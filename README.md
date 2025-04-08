# infinitestack-packages
Repository of InfiniteStack public packages

## Descriptor
```json
{
    "type": "Package",
    "package_type": "route-1-dijkistra",
    "input": [
        {
            "key": "map",
            "type": "file",
            "subtype": "geojson"
        },
        {
            "key": "points",
            "type": "file",
            "subtype": "json"
        }
    ],
    "output": [
        {
            "type": "file",
            "subtype": "geojson"
        },
        {
            "type": "file",
            "subtype": "gpx"
        }
    ],
    "mode": "inference",
    "executor_type": "python",
    "executor_version": "3.11",
    "executor": "run_route-1-dijkistra.py",
    "icon": "route-1-dijkistra.png",
    "title": "Routing Algorithm 1 (Dijkstra)",
    "description": "Routing algorithm that takes two input files: one GeoJSON file containing the roads and one JSON file with the array of starting and ending points for each route to be calculated."
}
```
## Workflow Example
```json
{
	"name": "Workflow Route",
	"blocks": [
		{
			"id": "BLOCK-1",
			"type": "File",
			"file_id": "cd65f649-56cf-4968-a438-51f2ae87ab05"
		},
		{
			"id": "BLOCK-2",
			"type": "File",
			"file_id": "cd65f649-56cf-4968-a438-51f2ae87ab05"
		},
		{
			"id": "BLOCK-3",
			"type": "Package",
			"package_type": "route-1-dijkistra",
			"input": {
				       "map": "._BLOCK-1",
				       "points": "._BLOCK-2"
           			 }
		},
		{
			"id": "BLOCK-4",
			"type": "Output",
			"output_type": "Gpx",
			"file_name": "route",
			"input": "._BLOCK-3"
		}
	]
}
```
