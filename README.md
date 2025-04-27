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
            "type": "geojson",
            "required": "false",
            "format": "file"
        },
        {
            "type": "gpx",
            "required": "false",
            "format": "file"
        }
    ],
    "quality_metrics": {},
    "mode": "inference",
    "executor_type": "python",
    "executor_version": "3.11",
    "executor": "package.py",
    "icon": "route-1-dijkistra.png",
    "title": "Routing Algorithm 1 (Dijkstra)",
    "description": "Routing algorithm that takes two input files: one GeoJSON file containing the roads and one JSON file with the array of starting and ending points for each route to be calculated.",
    "uuid": "e11f8feb-51cb-4fb8-8300-312bfa666fd4"
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
			"output_type": "gpx",
			"file_name": "route",
			"input": "._BLOCK-3"
		}
	]
}
```
## Packages example
The file packages.json must be inside `commons` folder.
```json
{"e11f8feb-51cb-4fb8-8300-312bfa666fd4":{"package_type": "route-1-dijkistra"}}
```

## Run parameters example

```json
{
  "port": 90000,
  "input":  {
              "map": "", 
              "points": ""
  },
  "output": {
              "output_type": "gpx", 
              "file_name": "route"
  }
}
```
Local test, without InfiniteStack
```bash
python3 package.py 90000 &
curl -X POST http://localhost:9000/input \
     -H "Content-Type: application/json" \
     -d '{
       "input": {
         "map": "",
         "points": ""
       },
       "output": {
         "output_type": "gpx",
         "file_name": "route"
       }
     }'
```