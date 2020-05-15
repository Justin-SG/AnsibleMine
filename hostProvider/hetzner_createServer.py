from io import BytesIO
from urllib.parse import urlencode
import sys, json, pycurl, certifi, logging, subprocess, shlex

def GetVolumeByName( volumeName ):
    logging.info('Searching existing volumes...')
    url = 'https://api.hetzner.cloud/v1/volumes'
    params = {'name': volumeName}
    serverResponseBytes = BytesIO()
    curl = pycurl.Curl()
    curl.setopt(pycurl.CAINFO, certifi.where())
    curl.setopt(pycurl.HTTPHEADER, ['Authorization: Bearer ' + config['api_key']])
    curl.setopt(curl.URL          , url + '?' + urlencode(params))
    curl.setopt(curl.WRITEDATA, serverResponseBytes)
    curl.perform() 
    curl.close()
    
    body = serverResponseBytes.getvalue()
    serverResponseJson = json.loads(body.decode('utf-8'))
    logging.debug(serverResponseJson)
                
    for volume in serverResponseJson['volumes']:
        volumeData = { 'volume_id': volume['id'],
                       'volume_linux_device': volume['linux_device']
                     }
        return volumeData

    logging.info('No existing volume found')
    return {}

def CreateVolume( config ):
    logging.info('Creating volume...')
    url = 'https://api.hetzner.cloud/v1/volumes'
    serverResponseBytes = BytesIO() 
    curl = pycurl.Curl()
    curl.setopt(pycurl.CAINFO, certifi.where())
    curl.setopt(pycurl.HTTPHEADER, ['Authorization: Bearer ' + config['api_key'], 'Content-Type:application/json'])
    curl.setopt(curl.URL, url)
    curl.setopt(curl.WRITEDATA, serverResponseBytes)
    data = { 'size'              : config['volume_size'],
             'name'              : config['name'],
             'location'          : config['location'],
             'automount'         : False,
             'format'            : 'xfs'
           }

    curl.setopt(curl.POSTFIELDS, json.dumps(data))
    curl.perform()
    curl.close()

    body = serverResponseBytes.getvalue()
    serverResponseJson = json.loads(body.decode('utf-8'))
    logging.debug(serverResponseJson)
    
    volumeData = { 'volume_id': serverResponseJson['volume']['id'],
                   'volume_linux_device': serverResponseJson['volume']['linux_device']
                 }
    return volumeData

def CreateServer( config, volumeId ):
    logging.info('Creating server...')
    url = 'https://api.hetzner.cloud/v1/servers'
    serverResponseBytes = BytesIO() 
    curl = pycurl.Curl()
    curl.setopt(pycurl.CAINFO, certifi.where())
    curl.setopt(pycurl.HTTPHEADER, ['Authorization: Bearer ' + config['api_key'], 'Content-Type:application/json'])
    curl.setopt(curl.URL, url)
    curl.setopt(curl.WRITEDATA, serverResponseBytes)
    data = { 'name'              : config['name'],
             'server_type'       : config['server_type'],
             'location'          : config['location'],
             'start_after_create': True,
             'image'             : config['image'],
             'ssh_keys'          : config['ssh_keys'],
             'volumes'           : [volumeId],
             'automount'         : True
           }

    curl.setopt(curl.POSTFIELDS, json.dumps(data))
    curl.perform()
    curl.close()

    body = serverResponseBytes.getvalue()    
    serverResponseJson = json.loads(body.decode('utf-8'))
    logging.debug(serverResponseJson)
    
    serverData = { 'server_id': serverResponseJson['server']['id'],
                   'server_ip': serverResponseJson['server']['public_net']['ipv4']['ip']
                 }

    logging.info('Created Server:')
    logging.info(serverData)
    return serverData

def CheckServerStatus( config, serverId ):
    while True:   
        logging.info('Checking server status...')
        url = 'https://api.hetzner.cloud/v1/servers/' + serverId
        serverResponseBytes = BytesIO() 
        curl = pycurl.Curl()
        curl.setopt(pycurl.CAINFO, certifi.where())
        curl.setopt(pycurl.HTTPHEADER, ['Authorization: Bearer ' + config['api_key'] ])
        curl.setopt(curl.URL, url)
        curl.setopt(curl.WRITEDATA, serverResponseBytes)

        curl.setopt(curl.POSTFIELDS, json.dumps(data))
        curl.perform()
        curl.close()

        body = serverResponseBytes.getvalue()    
        serverResponseJson = json.loads(body.decode('utf-8'))
        logging.debug(serverResponseJson)

        if serverResponseJson['status'] == 'running':
            logging.info('Server is running...')
            return true

        if serverResponseJson['status'] != 'initializing' and serverResponseJson['status'] != 'starting':
            logging.info('Server is starting...')
            return false

def main( config ):
    volumeData = GetVolumeByName(config['name'])
    if not volumeData:
        volumeData = CreateVolume(config)
    serverData = CreateServer(config, volumeData['volume_id'])
    if not CheckServerStatus(config, serverData['server_ip']):
        logging.info('Server is not running. Aborting...')
        return
    subprocess.call(shlex.split('ansible-playbook -i root@' + serverData['server_ip'] + ', ../playbook.yml --extra-vars "' + json.dumps(volumeData) + '"'))

logging.basicConfig(level=logging.DEBUG)
with open('hetzner_config.json') as config_file:
    config = json.load(config_file)
print(main(config))








