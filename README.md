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
            "key": "map",
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
    "mode": "inference"
}
```
