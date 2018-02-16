#!/bin/sh

#curl -u kodi:kodi --data-binary @StartGphotoImport.json -H 'Content-type: application/json;' 'http://127.0.0.1:8080/jsonrpc'

curl -u kodi:kodi \
        --data-binary \
                '{
			"jsonrpc": "2.0", 
			"id": 0, 
			"method": "Addons.ExecuteAddon", 
			"params": { 
				"addonid": "script.gphoto", 
				"params": {}  
				} 
		}' \
        -H 'Content-type: application/json;' \
        'http://127.0.0.1:8080/jsonrpc'
