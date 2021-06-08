"""
Lennox iComfort Wifi API.

Support added for AirEase MyComfortSync thermostats.

By Pete Sage

Notes:
  This API currently only supports manual mode (no programs) on the thermostat.

Cloud API Response Notes:

Issues:

Ideas/Future:

Change log:
v0.2.0 - Initial Release

"""

import logging
import json
import uuid
import aiohttp

from urllib.parse import quote

_LOGGER = logging.getLogger(__name__)
#_LOGGER.setLevel(logging.DEBUG)


AUTHENTICATE_URL = "https://ic3messaging.myicomfort.com/v1/mobile/authenticate"
LOGIN_URL = "https://ic3messaging.myicomfort.com/v2/user/login"
NEGOTIATE_URL = "https://icnotificationservice.myicomfort.com/LennoxNotificationServer/negotiate"
RETRIEVE_URL = 'https://icretrieveapi.myicomfort.com/v1/messages/retrieve?LongPollingTimeout=0&StartTime=1&Direction=Oldest-to-Newest&MessageCount=10'
IC3_MESSAGING_REQUEST_URL = "https://ic3messaging.myicomfort.com/v1/messages/requestData"
REQUESTDATA_URL = "https://icrequestdataapi.myicomfort.com/v1/Messages/RequestData"
PUBLISH_URL = "https://icpublishapi.myicomfort.com/v1/messages/publish"

HVAC_MODES = {'off', 'cool', 'heat'}
FAN_MODES = {'on', 'auto', 'circulate'}
HVAC_MODE_TARGETS = {'fanMode', 'systemMode'}

# NOTE:  This application id is super important and a point of brittleness.  You can find this in the burp logs between the mobile app and the Lennox server.  
# If we start getting reports of missesd message, this is the place to look....
# Here is what I do know
#
#  The application id is unique to the mobile app install, so if you install the app on your iphone and ipad you will have two different ids.  
#  Uninstalling app on ipad and re-installing created the same app_id; which is also referenced as the device_id in some api calls
#
# If you use the same application_id in both the app and here, then messages will be lost - as there appears to be a SINGLE QUEUE based on <application_id>_<email> - 
# so whichever app consumes the message first gets it. The simple test for this - is with the App open and this program running - go to the thermostat and change the mode it will only show up in one place
#
# Arbitrary application_ids do not work, so for example creating a unique id each time this program runs does not seem to work, changing the prefix from MAPP to HA also did not work.
#
# So what I did is made a single change to one of the digits and i am getting data AND i get updates to both phone and this application
# Because the topic also contains e-mail this has a chance to work, but running this program more the once using the same account and email will result in missed messages
#
# So, we do need a mechanism to generate a unique APPLICATION_ID that does work reliably.
APPLICATION_ID = "mapp079372367644467046827099"

# This appears to be a certificate that is installed as part of the App.  The same cert was presented from both Android and IOS apps.  Fortunately it is being passed; rather than used by the app to encrypt a request.
CERTIFICATE = "MIIKXAIBAzCCChgGCSqGSIb3DQEHAaCCCgkEggoFMIIKATCCBfoGCSqGSIb3DQEHAaCCBesEggXnMIIF4zCCBd8GCyqGSIb3DQEMCgECoIIE/jCCBPowHAYKKoZIhvcNAQwBAzAOBAhvt2dVYDpuhgICB9AEggTYM43UVALue2O5a2GqZ6xPFv1ZOGby+M3I/TOYyVwHDBR+UAYNontMWLvUf6xE/3+GUj/3lBcXk/0erw7iQXa/t9q9b8Xk2r7FFuf+XcWvbXcvcPG0uP74Zx7Fj8HcMmD0/8NNcH23JnoHiWLaa1walfjZG6fZtrOjx4OmV6oYMdkRZm9tP5FuJenPIwdDFx5dEKiWdjdJW0lRl7jWpvbU63gragLBHFqtkCSRCQVlUALtO9Uc2W+MYwh658HrbWGsauLKXABuHjWCK8fiLm1Tc6cuNP/hUF+j3kxt2tkXIYlMhWxEAOUicC0m8wBtJJVCDQQLzwN5PebGGXiq04F40IUOccl9RhaZ2PdWLChaqq+CNQdUZ1mDYcdfg5SVMmiMJayRAA7MWY/t4W53yTU0WXCPu3mg0WPhuRUuphaKdyBgOlmBNrXq/uXjcXgTPqKAKHsph3o6K2TWcPdRBswwc6YJ88J21bLD83fT+LkEmCSldPz+nvLIuQIDZcFnTdUJ8MZRh+QMQgRibyjQwBg02XoEVFg9TJenXVtYHN0Jpvr5Bvd8FDMHGW/4kPM4mODo0PfvHj9wgqMMgTqiih8LfmuJQm30BtqRNm3wHCW1wZ0bbVqefvRSUy82LOxQ9443zjzSrBf7/cFk+03iNn6t3s65ubzuW7syo4lnXwm3DYVR32wo/WmpZVJ3NLeWgypGjNA7MaSwZqUas5lY1EbxLXM5WLSXVUyCqGCdKYFUUKDMahZ6xqqlHUuFj6T49HNWXE7lAdSAOq7yoThMYUVvjkibKkji1p1TIAtXPDPVgSMSsWG1aJilrpZsRuipFRLDmOmbeanS+TvX5ctTa1px/wSeHuAYD/t+yeIlZriajAk62p2ZGENRPIBCbLxx1kViXJBOSgEQc8ItnBisti5N9gjOYoZT3hoONd/IalOxcVU9eBTuvMoVCPMTxYvSz6EUaJRoINS6yWfzriEummAuH6mqENWatudlqKzNAH4RujRetKdvToTddIAGYDJdptzzPIu8OlsmZWTv9HxxUEGYXdyqVYDJkY8dfwB1fsa9vlV3H7IBMjx+nG4ESMwi7UYdhFNoBa7bLD4P1yMQdXPGUs1atFHmPrXYGf2kIdvtHiZ149E9ltxHjRsEaXdhcoyiDVdraxM2H46Y8EZNhdCFUTr2vMau3K/GcU5QMyzY0Z1qD7lajQaBIMGJRZQ6xBnQAxkd4xU1RxXOIRkPPiajExENuE9v9sDujKAddJxvNgBp0e8jljt7ztSZ+QoMbleJx7m9s3sqGvPK0eREzsn/2aQBA+W3FVe953f0Bk09nC6CKi7QwM4uTY9x2IWh/nsKPFSD0ElXlJzJ3jWtLpkpwNL4a8CaBAFPBB2QhRf5bi52KxaAD0TXvQPHsaTPhmUN827smTLoW3lbOmshk4ve1dPAyKPl4/tHvto/EGlYnQf0zjs6BATu/4pJFJz+n0duyF1y/F/elBDXPclJvfyZhEFT99txYsSm2GUijXKOHW/sjMalQctiAyg8Y5CzrOJUhKkB/FhaN5wjJLFz7ZCEJBV7Plm3aNPegariTkLCgkFZrFvrIppvRKjR41suXKP/WhdWhu0Ltb+QgC+8OQTC8INq3v1fdDxT2HKNShVTSubmrUniBuF5MDGBzTATBgkqhkiG9w0BCRUxBgQEAQAAADBXBgkqhkiG9w0BCRQxSh5IADAANgAyAGQANQA5ADMANQAtADYAMAA5AGUALQA0ADYAMgA2AC0AOQA2ADUAZAAtADcAMwBlAGQAMQAwAGUAYwAzAGYAYgA4MF0GCSsGAQQBgjcRATFQHk4ATQBpAGMAcgBvAHMAbwBmAHQAIABTAHQAcgBvAG4AZwAgAEMAcgB5AHAAdABvAGcAcgBhAHAAaABpAGMAIABQAHIAbwB2AGkAZABlAHIwggP/BgkqhkiG9w0BBwagggPwMIID7AIBADCCA+UGCSqGSIb3DQEHATAcBgoqhkiG9w0BDAEGMA4ECFK0DO//E1DsAgIH0ICCA7genbD4j1Y4WYXkuFXxnvvlNmFsw3qPiHn99RVfc+QFjaMvTEqk7BlEBMduOopxUAozoDAv0o+no/LNIgKRXdHZW3i0GPbmoj2WjZJW5T6Z0QVlS5YlQgvbSKVee51grg6nyjXymWgEmrzVldDxy/MfhsxNQUfaLm3awnziFb0l6/m9SHj2eZfdB4HOr2r9BXA6oSQ+8tbGHT3dPnCVAUMjht1MNo6u7wTRXIUYMVn+Aj/xyF9uzDRe404yyenNDPqWrVLoP+Nzssocoi+U+WUFCKMBdVXbM/3GYAuxXV+EHAgvVWcP4deC9ukNPJIdA8gtfTH0Bjezwrw+s+nUy72ROBzfQl9t/FHzVfIZput5GcgeiVppQzaXZMBu/LIIQ9u/1Q7xMHd+WsmNsMlV6eekdO4wcCIo/mM+k6Yukf2o8OGjf1TRwbpt3OH8ID5YRIy848GT49JYRbhNiUetYf5s8cPglk/Q4E2oyNN0LuhTAJtXOH2Gt7LsDVxCDwCA+mUJz1SPAVMVY8hz/h8l4B6sXkwOz3YNe/ILAFncS2o+vD3bxZrYec6TqN+fdkLf1PeKH62YjbFweGR1HLq7R1nD76jinE3+lRZZrfOFWaPMBcGroWOVS0ix0h5r8+lM6n+/hfOS8YTF5Uy++AngQR18IJqT7+SmnLuENgyG/9V53Z7q7BwDo7JArx7tosmxmztcubNCbLFFfzx7KBCIjU1PjFTAtdNYDho0CG8QDfvSQHz9SzLYnQXXWLKRseEGQCW59JnJVXW911FRt4Mnrh5PmLMoaxbf43tBR2xdmaCIcZgAVSjV3sOCfJgja6mKFsb7puzYRBLqYkfQQdOlrnHHrLSkjaqyQFBbpfROkRYo9sRejPMFMbw/Orreo+7YELa+ZoOpS/yZAONgQZ6tlZ4VR9TI5LeLH5JnnkpzpRvHoNkWUtKA+YHqY5Fva3e3iV82O4BwwmJdFXP2RiRQDJYVDzUe5KuurMgduHjqnh8r8238pi5iRZOKlrR7YSBdRXEU9R5dx+i4kv0xqoXKcQdMflE+X4YMd7+BpCFS3ilgbb6q1DuVIN5Bnayyeeuij7sR7jk0z6hV8lt8FZ/Eb+Sp0VB4NeXgLbvlWVuq6k+0ghZkaC1YMzXrfM7N+jy2k1L4FqpO/PdvPRXiA7uiH7JsagI0Uf1xbjA3wbCj3nEi3H/xoyWXgWh2P57m1rxjW1earoyc1CWkRgZLnNc1lNTWVA6ghCSMbCh7T79Fr5GEY2zNcOiqLHS3MDswHzAHBgUrDgMCGgQU0GYHy2BCdSQK01QDvBRI797NPvkEFBwzcxzJdqixLTllqxfI9EJ3KSBwAgIH0A=="

class s30api_async(object):

    _username: str = None
    _password: str = None
    _applicationid: str = APPLICATION_ID
    _systemList = []
    _publishMessageId: int = 1

    """Representation of the Lennox S30/E30 thermostat."""
    def __init__(self, username: str, password : str):
        """Initialize the API interface."""
        _LOGGER.info('__init__ S30TStat  applicationId [' + APPLICATION_ID + ']')

        self._username = username
        self._password = password
        self._applicationid = APPLICATION_ID
        self._systemList = []
        self._publishMessageId = 1
        self.session = aiohttp.ClientSession()

    def getClientId(self) -> str:
        return self._applicationid + "_" + self._username

    async def serverConnect(self) -> bool:
        _LOGGER.info("serverLogin - Entering")
        result = await self.authenticate()
        if result == False:
            _LOGGER.info("serverLogin:authenticate - failed")
            return False
        result = await self.login()
        if result == False:
            _LOGGER.info("serverLogin:login - failed")
            return False
        result = await self.negotiate()
        if result == False:
            _LOGGER.info("serverLogin:negotiate - failed")
            return False
        _LOGGER.info("serverLogin - Complete")
        return True

    async def authenticate(self) -> bool:
        # The only reason this function would fail is if the certificate is no longer valid or the URL is not longer valid.
        _LOGGER.info("Authenticate - Enter")
        url = AUTHENTICATE_URL
        body = CERTIFICATE
        try:
            # I did see this fail due to an active directory error on Lennox side.  I saw the same failure in the Burp log for the App and saw that it repeatedly retried
            # until success, so this must be a known / re-occuring issue that they have solved via retries.  When this occured the call hung for a while, hence there
            # appears to be no reason to sleep between retries.
            for x in range(1, 5):
                resp = await self.session.post(url, data=body)
                if resp.status == 200:
                    resp_json = await resp.json()
                    _LOGGER.debug(json.dumps(resp_json, indent=4))
                    self.authBearerToken = resp_json['serverAssigned']['security']['certificateToken']['encoded']
                    _LOGGER.info("authenticate success")
                    return True
                else:
                    # There is often useful diag information in the txt, so grab it and log it                    
                    txt = await resp.text()
                    _LOGGER.error('authenticate failed response code [' + str(resp.status) + '] text [' + str(txt) + ']')
                _LOGGER.info("authenticate retry [" + str(x) + "]")
            return False
        except Exception as e:
            _LOGGER.error("authenticate exception " + str(e))
            return False

    async def login(self) -> bool:
        _LOGGER.info("login - Enter")
        url:str = LOGIN_URL
        try:
            payload:str = "username=" + self._username + "&password=" + self._password + "&grant_type=password" + "&applicationid=" + self._applicationid
            headers = {
                'Authorization': self.authBearerToken,
                'Content-Type': 'text/plain',
                'User-Agent': 'lx_ic3_mobile_appstore/3.75.218 (iPad; iOS 14.4.1; Scale/2.00)'
            }
            resp = await self.session.post(url,headers=headers, data=payload)
            if resp.status != 200:
                txt = await resp.text()
                _LOGGER.error('Login failed response code [' + str(resp.status) + '] text [' + str(resp.text)+ ']')
                return False
            resp_json = await resp.json()
            _LOGGER.debug(json.dumps(resp_json, indent=4))
            # Grab the bearer token
            self.loginBearerToken = resp_json['ServerAssignedRoot']['serverAssigned']['security']['userToken']['encoded']
            # Split off the "bearer" part of the token, as we need to use just the token part later in the URL.  Format is "Bearer <token>"
            split = self.loginBearerToken.split(' ')
            self.loginToken = split[1]
            # This is the ID of the target thermostat
            homeList = resp_json['readyHomes']['homes']
            # not sure if this is the best way to reinitialize.
            self._homeList = []
            self._systemList = []

            for home in homeList:
                lhome = lennox_home(home['id'], home['homeId'], home['name'], home)
                self._homeList.append(lhome)
                for system in resp_json['readyHomes']['homes'][lhome.idx]['systems']:
                    lsystem = lennox_system(self, lhome, system['id'],system['sysId'])
                    self._systemList.append(lsystem)                
        except Exception as e:
            _LOGGER.error("Exception " + str(e))
            return False
        _LOGGER.info("login Success homes [" + str(len(self._homeList)) + "] systems [" + str(len(self._systemList)) + "]")
        return True


    async def negotiate(self) -> bool:
        _LOGGER.info("Negotiate - Enter")
        try:
            url = NEGOTIATE_URL
            # This sets the version of the client protocol, at some point Lenox could obsolete this version
            url += "?clientProtocol=1.3.0.0"
            # Since these may have special characters, they need to be URI encoded
            url += "&clientId=" + quote(self.getClientId())
            url += "&Authorization=" + quote(self.loginToken)
            resp = await self.session.get(url)            
            if resp.status != 200:
                _LOGGER.error('Negotiate failed response code [' + str(resp.status) + '] text [' + await resp.text() + ']')
                return False
            resp_json = await resp.json()
            _LOGGER.debug(json.dumps(resp_json, indent=4))
            # So we get these two pieces of information, but they are never used, perhaps these are used by the websockets interface?
            self._connectionId = resp_json['ConnectionId']
            self._connectionToken = resp_json['ConnectionToken']
            # The apps do not try to use websockets, instead they periodically poll the data using the retrieve endpoint, would be better
            # to use websockets, so we will stash the info for future use.
            self._tryWebsockets = resp_json['TryWebSockets']
            self._streamURL = resp_json['Url']
            _LOGGER.info("Negotiate Success connectionId [" + self._connectionId + "] tryWebSockets [" + str(self._tryWebsockets) + "] streamUrl [" + self._streamURL + "]")
            return True
        except Exception as e:
            _LOGGER.error("Exception " + e)
            _LOGGER.info("Negotiate - Failed")
            return False

    # The topics subscribed to here are based on the topics that the WebApp subscribes to.  We likely don't need to subscribe to all of them
    # These appear to be JSON topics that correspond to the returned JSON.  For now we will do what the web app does.
    async def subscribe(self, lennoxSystem: 'lennox_system') -> bool:
        result =  await self.requestDataHelper("ic3server", '"AdditionalParameters":{"publisherpresence":"true"},"Data":{"presence":[{"id":0,"endpointId":"' + lennoxSystem.sysId + '"}]}')
        if result == False:
            _LOGGER.error("subscribe - subscription 1 failed")
            return False
        result =  await self.requestDataHelper(lennoxSystem.sysId, '"AdditionalParameters":{"JSONPath":"1;\/system;\/zones;\/occupancy;\/schedules;"}')
        if result == False:
            _LOGGER.error("subscribe - subscription 2 failed")
            return False
        result = await self.requestDataHelper(lennoxSystem.sysId, '"AdditionalParameters":{"JSONPath":"1;\/reminderSensors;\/reminders;\/alerts\/active;\/alerts\/meta;\/dealers;\/devices;\/equipments;\/fwm;\/ocst;"}')
        if result == False:        
            _LOGGER.error("subscribe - subscription 3 failed")
            return False
        return True

    async def retrieve(self) -> bool:
        # This method reads off the queue.
        # Observations:  the clientId is not passed in, they must be mapping the token to the clientId as part of negotiate
        # TODO: The long polling is not working, I have tried adjusting the long polling delay.  Long polling seems to work from the IOS App, not sure
        # what the difference is.   https://gist.github.com/rcarmo/3f0772f2cbe0612b699dcbb839edabeb
        _LOGGER.info("Request Data - Enter")
        try:
            url = RETRIEVE_URL
            headers = {
                'Authorization': self.loginBearerToken,
                'User-Agent' : 'lx_ic3_mobile_appstore/3.75.218 (iPad; iOS 14.4.1; Scale/2.00)',
                'Accept' : '*.*',
                'Accept-Language' : 'en-US;q=1',
                'Accept-Encoding' : 'gzip, deflate'                
            }
            resp = await self.session.get(url,  headers=headers)                      
            if resp.status != 200:
                _LOGGER.error('Negotiate failed response code [' + str(resp.status) + '] text [' + await resp.text() + ']')            
                return False
            resp_json = await resp.json()               
            _LOGGER.debug(json.dumps(resp_json, indent=4))
            for message in resp_json["messages"]:
                sysId = message["SenderId"]
                system = self.getSystem(sysId)
                if (system == None):
                    _LOGGER.error("Retrieve unknown SenderId/SystemId [" + str(sysId) + "]")
                    continue
                system.processMessage(message)

            return True
        except Exception as e:
            _LOGGER.error("Retrieve Failed - Exception " + str(e))
            return False

    # Messages seem to use unique GUIDS, here we create one
    def getNewMessageID(self):
        return str(uuid.uuid4())


    async def requestDataHelper(self, sysId: str, additionalParameters: str) -> bool:
        _LOGGER.info("requestDataHelper - Enter")
        try:
            url = REQUESTDATA_URL
            headers = {
                'Authorization': self.loginBearerToken,
                'Content-Type': 'application/json; charset=utf-8',
                'User-Agent' : 'lx_ic3_mobile_appstore/3.75.218 (iPad; iOS 14.4.1; Scale/2.00)',
                'Accept' : '*.*',
                'Accept-Language' : 'en-US;q=1',
                'Accept-Encoding' : 'gzip, deflate'
            }

            payload = '{'
            payload += '"MessageType":"RequestData",'
            payload += '"SenderID":"' + self.getClientId() + '",'
            payload += '"MessageID":"' + self.getNewMessageID() + '",'
            payload += '"TargetID":"' + sysId + '",'
            payload += additionalParameters
            payload += '}'
            _LOGGER.debug("Payload  [" + payload + "]")           
            resp = await self.session.post(url, headers=headers, data=payload)            

            if resp.status != 200:
                _LOGGER.error('requestDataHelper failed response code [' + str(resp.status) + '] text [' + await resp.text() + ']')
                return False
            _LOGGER.debug(json.dumps(await resp.json(), indent=4))
            return True
        except Exception as e:
            _LOGGER.error("requestDataHelper - Exception " + str(e))
            return False

    def getSystems(self):
        return self._systemList

    def getSystem(self, sysId) -> 'lennox_system':
        for system in self._systemList:
            if (system.sysId == sysId):
                return system
        return None

    def getHomes(self):
        return self._homeList

    # When publishing data, app uses a GUID that counts up from 1.
    def getNextMessageId(self):
        self._publishMessageId += 1
        messageUUID = uuid.UUID(int = self._publishMessageId)
        return str(messageUUID)

    async def setModeHelper(self, sysId, modeTarget, mode, scheduleId):
        _LOGGER.info('setMode modeTarget [' + modeTarget + '] mode [' + str(mode) + '] scheduleId [' + str(scheduleId) + '] sysId [' + str(sysId) + ']')
        try:
            if (modeTarget not in HVAC_MODE_TARGETS):
                _LOGGER.error('setModeHelper - invalide mode target [' + str(modeTarget) + '] requested, must be in [' + str(HVAC_MODE_TARGETS) + ']')
                return False
            data = '"Data":{"schedules":[{"schedule":{"periods":[{"id":0,"period":{"' + modeTarget + '":"' + str(mode) + '"}'
            data += '}]},"id":' + str(scheduleId) + '}]}'
            _LOGGER.debug('setmode message [' + data + ']')
            await self.publishMessageHelper(sysId, data)
        except Exception as e:
            _LOGGER.error("setmode - Exception " + str(e))
            return False
        _LOGGER.info('setModeHelper success[' + str(mode) + '] scheduleId [' + str(scheduleId) + '] sysId [' + str(sysId) + ']')
        return True

    async def publishMessageHelper(self, sysId, data):
        _LOGGER.info('publishMessageHelper sysId [' + str(sysId) + '] data [' + data + ']')
        try:
            body = '{'
            body += '"MessageType":"Command",'
            body += '"SenderID":"' + self.getClientId() +'",'
            body += '"MessageID":"' + self.getNextMessageId() +'",'
            body += '"TargetID":"' + sysId + '",'
            body += data
            body += '}'

            jsbody = json.loads(body)
            
            _LOGGER.debug('publishMessageHelper message [' + json.dumps(jsbody, indent=4) + ']')

            url = PUBLISH_URL
            headers = {
                'Authorization': self.loginBearerToken,
                'User-Agent' : 'lx_ic3_mobile_appstore/3.75.218 (iPad; iOS 14.4.1; Scale/2.00)',
                'Accept' : '*.*',
                'Content-Type' : 'application/json',
                'Accept-Language' : 'en-US;q=1',
                'Accept-Encoding' : 'gzip, deflate'                
            }
            resp = await self.session.post(url,  headers=headers, data=body)  
            if resp.status != 200:
                _LOGGER.error('publishMessageHelper failed response code [' + str(resp.status) + '] text [' + await resp.text() + ']')
                return False
            _LOGGER.debug(json.dumps(await resp.json(), indent=4))
        except Exception as e:
            _LOGGER.error("publishMessageHelper - Exception " + str(e))
            return False
        _LOGGER.info('publishMessageHelper success sysId [' + str(sysId) + ']')
        return True


    async def setHVACMode(self, sysId, mode, scheduleId):
        _LOGGER.info('setHVACMode mode [' + str(mode) + '] scheduleId [' + str(scheduleId) + '] sysId [' + str(sysId) + ']')
        if (mode not in HVAC_MODES):
            _LOGGER.error('setMode - invalide mode [' + str(mode) + '] requested, must be in [' + str(HVAC_MODES) + ']')
            return False
        return await self.setModeHelper(sysId, 'systemMode', mode, scheduleId)

    async def setFanMode(self, sysId, mode, scheduleId):
        _LOGGER.info('setFanMode mode [' + str(mode) + '] scheduleId [' + str(scheduleId) + '] sysId [' + str(sysId) + ']')
        if (mode not in FAN_MODES):
            _LOGGER.error('setFanMode - invalide mode [' + str(mode) + '] requested, must be in [' + str(FAN_MODES) + ']')
            return False
        return await self.setModeHelper(sysId, 'fanMode', mode, scheduleId)


class lennox_home(object):
    def __init__(self, homeIdx:int, homeId:int, homeName:str, json:json):
        self.idx = homeIdx
        self.id = homeId
        self.name = homeName
        self.json = json
        _LOGGER.info("Creating lennox_home homeIdx [" + str(self.idx) + "] homeId [" + str(self.id) + "] homeName [" + str(self.name) + "] json [" + str(json)+ "]") 

class lennox_system(object):
    def __init__(self, api:s30api_async, home:lennox_home, idx:int, sysId:str):
        self.api = api
        self.idx = idx
        self.sysId = sysId
        self.home = home
        self._zoneList = []
        self._schedules = []
        self._callbacks = []
        self.outdoorTemperature = None
        self.name = self.home.name + '_' + str(self.idx)
        self._en = False
        _LOGGER.info("Creating lennox_system idx [" + str(self.idx) + "] sysId [" + str(self.sysId) + "]") 

    def processMessage(self, message):
        try:
            data = message["Data"]
            if 'system'in data:
                self.processSystemMessage(data['system'])
            if "zones" in data:
                self.processZonesMessage(data['zones'])
            if "schedules" in data:
                self.processSchedules(data['schedules'])
            self.executeOnUpdateCallbacks()
        except Exception as e:
            _LOGGER.error("processMessage - Exception " + str(e))
            return False

    def getOrCreateSchedule(self, id):
        schedule = self.getSchedule(id)
        if schedule != None:
            return schedule
        schedule = lennox_schedule(id)
        self._schedules.append(schedule)
        return schedule

    def getSchedule(self, id):
        for schedule in self._schedules:
            if schedule.id == id:
                return schedule
        return None

    def getSchedules(self):
        return self._schedules

    def processSchedules(self, schedules):
        try:
            for schedule in schedules:
                id = schedule['id']
                if 'schedule' in schedule:
                    if 'name' in schedule['schedule']:
                        lschedule = self.getOrCreateSchedule(id)
                        lschedule.update(schedule)
                        # In manual mode, the updates only hit the schedulde rather than the period within the status.
                        # So here, we look for changes to these schedules and route them to the zone but only
                        # if it is in manual mode.
                        if schedule['id'] in (16, 17, 18, 19):  # Manual Mode Zones 1 .. 4
                            zone_id = id - 16
                            period = schedule['schedule']['periods'][0]['period']
                            zone:lennox_zone = self.getZone(zone_id)
                            if zone.isZoneManualMode():
                                zone.processPeriodMessage(period)
        except Exception as e:
            _LOGGER.error("processSchedules - failed " + str(e))

    def registerOnUpdateCallback(self, callbackfunc):
        self._callbacks.append(callbackfunc)

    def executeOnUpdateCallbacks(self):
#        if self._en == False:
#            return
        for callbackfunc in self._callbacks:
            try:
                callbackfunc()
            except Exception as e:
                _LOGGER.error("executeOnUpdateCallback - failed " + str(e))

    def enableCallbackProcessing(self, en):
        self._en = en
                

    def processSystemMessage(self, message):
        try:
            if 'config'in message:
                config = message['config']
                if 'temperatureUnit' in config:              
                    self.temperatureUnit = config['temperatureUnit']
                if 'dehumidificationMode' in config:              
                   self.dehumidificationMode = config['dehumidificationMode']
                if 'name' in config:
                    self.name = config['name']
                if 'options' in config:
                    options = config['options']
                    self.indoorUnitType = options["indoorUnitType"]
                    self.productType = options["productType"]  # S30
                    self.outdoorUnitType = options["outdoorUnitType"]
                    self.humifidierType = options["humidifierType"]
                    self.dehumidifierType = options["dehumidifierType"]
            if 'status' in message:
                status = message['status']
                if 'outdoorTemperature' in status:
                    self.outdoorTemperature = status['outdoorTemperature']
                if 'outdoorTemperatureC' in status:
                    self.outdoorTemperatureC = status['outdoorTemperatureC']
                if 'diagRuntime' in status:
                    self.diagRuntime = status['diagRuntime']
                if 'diagPoweredHours' in status:
                    self.diagPoweredHours = status['diagPoweredHours']
                if 'numberOfZones' in status:
                    self.numberOfZones = status['numberOfZones']
#                if 'internalStatus' in message:
#                    self.currentCfm = status['internalStatus']['ventilation']['currentCfm']
            # Sometimes a change to system mode is not reflected back into the individual zones; rather it is reflected here as a
            # change to schedule 16.  So we will pass this messages to each zone.
        except Exception as e:
            _LOGGER.error("processSystemMessage - Exception " + str(e))
            return False

    def getZone(self, id):
        for zone in self._zoneList:
            if (zone.id == id):
                return zone
        return None


    def getZones(self):
        return self._zoneList

    def getZoneList(self):
        # todo obsolete this method
        return self._zoneList


    async def setHVACMode(self, mode, scheduleId):
        return await self.api.setHVACMode(self.sysId, mode, scheduleId)

    async def setFanMode(self, mode, scheduleId):
        return await self.api.setFanMode(self.sysId, mode, scheduleId)

    def convertFtoC(self, tempF):
        # Lennox allow Celsius to be specified only in 0.5 degree increments
        float_TempC = ( float(tempF) - 32.0) * (5.0 / 9.0)
        str_TempC = round(float_TempC * 2.0) / 2.0
        return str_TempC

    async def setSchedule(self, zoneId, scheduleId):
        data = '"Data":{"zones":[{"config":{"scheduleId":' + str(scheduleId) + '},"id":' + str(zoneId) + '}]}'
        return await self.api.publishMessageHelper(self.sysId, data)

    async def setpointHelper(self, zoneId, scheduleId, hsp,hspC,csp,cspC):
        # 16 is the schedule id for manual modes, not sure if this is always going to be correct
        scheduleId = 16 + zoneId

        data =  '"Data":{"schedules":[{"schedule":{"periods":[{"id":0,"period":{'
        data += '"hsp":' + str(hsp) +',"cspC":' + str(cspC) + ',"hspC":' + str(hspC) +',"csp":' + str(csp) + '} }]},"id":' + str(scheduleId) + '}]}'
        return await self.api.publishMessageHelper(self.sysId, data)
    
    async def setHeatCoolSPF(self, zoneId, scheduleId, r_hsp, r_csp):
        hsp = str(int(r_hsp))
        hspC = str(self.convertFtoC(r_hsp))
        csp = str(int(r_csp))
        cspC = str(self.convertFtoC(r_csp))
        return await self.setpointHelper(zoneId, scheduleId, hsp,hspC,csp,cspC)

    async def setCoolSPF(self, zoneId, scheduleId, tempF):
        csp = str(int(tempF))        
        cspC = str(self.convertFtoC(tempF))
        schedule = self.getSchedule(scheduleId)
        if schedule is None:
            _LOGGER.error("setCoolSPF - unable to find schedule [" + str(scheduleId) + ']')
            return False
        period = schedule.getPeriod(0)
        if period is None:
            _LOGGER.error("setCoolSPF - unable to find schedule [" + str(scheduleId) + '] period 0')
            return False
        # Lennox App sends both the Heat Setpoints and Cool Setpoints when the App updates just the Cool SP.
        # Grab the existing heatsetpoints
        hsp = period.hsp
        hspC = period.hspC
        return await self.setpointHelper(zoneId, scheduleId, hsp,hspC,csp,cspC)

    async def setHeatSPF(self, zoneId, scheduleId, tempF):
        hsp = str(int(tempF))        
        hspC = str(self.convertFtoC(tempF))
        schedule = self.getSchedule(scheduleId)
        if schedule is None:
            _LOGGER.error("setCoolSPF - unable to find schedule [" + str(scheduleId) + ']')
            return False
        period = schedule.getPeriod(0)
        if period is None:
            _LOGGER.error("setCoolSPF - unable to find schedule [" + str(scheduleId) + '] period 0')
            return False
        # Lennox App sends both the Heat Setpoints and Cool Setpoints when the App updates just the Cool SP.
        # Grab the existing coolsetpoints
        csp = period.csp
        cspC = period.cspC
        return await self.setpointHelper(zoneId, scheduleId, hsp,hspC,csp,cspC)

    def processZonesMessage(self, message):
        try:
            for zone in message:
                id = zone['id']
                lzone = self.getZone(id)
                if (lzone == None):
                    if 'config' in zone:
                        name = zone['config']['name']
                    else:
                        name = "Zone " + str(id+1)
                    if 'status' in zone:
                        lzone = lennox_zone(self, id, name)
                        self._zoneList.append(lzone)
                    else:
                        _LOGGER.info("processZoneMessage skipping unconfigured zone id [" + str(id) + "] name [" + name +"]")
                if (lzone != None):
                    lzone.processMessage(zone)
        except Exception as e:
            _LOGGER.error("processZonesMessage - Exception " + str(e))
            return False

class lennox_zone(object):
    def __init__(self, system, id, name):
        self.id = id
        self.name = name
        self._system = system

        self.temperature = None
        self.humidity = None
        self.systemMode = None
        self.fanMode = None
        self.humidityMode = None
        self.csp = None
        self.hsp = None

        self.heatingOption =  None
        self.maxHsp = None
        self.minHsp = None
        self.coolingOption = None
        self.maxCsp = None
        self.minCsp = None
        self.humidificationOption = None
        self.maxHumSp = None
        self.minHspC = None
        self.emergencyHeatingOption = None
        self.dehumidificationOption = None
        self.maxDehumSp = None
        self.minHspC = None

        self.tempOperation = None
        self.humOperation = None
        self.scheduleId = None

        # PERIOD
        self.systemMode = None
        self.fanMode = None
        self.humidityMode = None
        self.csp = None
        self.cspC = None
        self.hsp = None
        self.hspC = None
        self.desp = None
        self.sp = None
        self.spC = None
        self.husp = None
        self.startTime = None
        self.overrideActive = None

        _LOGGER.info("Creating lennox_zone id [" + str(self.id) + "] name [" + str(self.name) + "]") 

    def processMessage(self, zoneMessage):
        _LOGGER.info("processMessage lennox_zone id [" + str(self.id) + "] name [" + str(self.name) + "]") 
        if 'config' in zoneMessage:
            config = zoneMessage['config']
            if ('heatingOption' in config):
                self.heatingOption = config['heatingOption']
            if ('maxHsp' in config):
                self.maxHsp = config['maxHsp']
            if ('minHsp' in config):
                self.minHsp = config['minHsp']
            if ('coolingOption' in config):
                self.coolingOption = config['coolingOption']
            if ('maxCsp' in config):
                self.maxCsp = config['maxCsp']
            if ('minCsp' in config):
                self.minCsp = config['minCsp']
            if ('humidificationOption' in config):
                self.humidificationOption = config['humidificationOption']
            if ('maxHumSp' in config):
                self.maxHumSp = config['maxHumSp']
            if ('minHspC' in config):
                self.minHspC = config['minHspC']
            if ('emergencyHeatingOption' in config):
                self.emergencyHeatingOption = config['emergencyHeatingOption']
            if ('dehumidificationOption' in config):
                self.dehumidificationOption = config['dehumidificationOption']
            if ('maxDehumSp' in config):
                self.maxDehumSp = config['maxDehumSp']
            if ('minDehumSp' in config):
                self.minHspC = config['minDehumSp']
            if ('scheduleId' in config):
                self.scheduleId = config['scheduleId']
            if ('scheduleHold' in config):
                scheduleHold = config['scheduleHold']
                found = False
                if 'scheduleId' in scheduleHold:
                    if scheduleHold['scheduleId'] == self.getOverdideScheduleId():
                        if scheduleHold['enabled'] == True:
                            self.overrideActive = True
                            found = True
                if found is False:
                    self.overrideActive = False

        if 'status' in zoneMessage:
            status = zoneMessage['status']
            if 'temperature' in status:
                self.temperature = status['temperature']
            if 'humidity' in status:
                self.humidity = status['humidity']
            if 'humidity' in status:
                self.humidity = status['humidity']
            if 'tempOperation' in status:
                self.tempOperation = status['tempOperation']
            if 'humOperation' in status:
                self.humOperation = status['humOperation']

            if 'period' in status:
                period = status['period']
                self.processPeriodMessage(period)

        _LOGGER.debug("lennox_zone id [" + str(self.id) + "] name [" + str(self.name) + "] temperature [" + str(self.getTemperature()) + "] humidity [" + str(self.getHumidity()) + "]")

    def processPeriodMessage(self, period):
        if 'systemMode' in period:
            self.systemMode = period['systemMode']
        if 'fanMode' in period:
            self.fanMode = period['fanMode']
        if 'humidityMode' in period:
            self.humidityMode = period['humidityMode']
        if 'csp' in period:
            self.csp = period['csp']
        if 'cspC' in period:
            self.cspC = period['cspC']
        if 'hsp' in period:
            self.hsp = period['hsp']
        if 'hspC' in period:
            self.hspC = period['hspC']
        if 'desp' in period:
            self.desp = period['desp']
        if 'sp' in period:
            self.sp = period['sp']
        if 'spC' in period:
            self.spC = period['spC']
        if 'husp' in period:
            self.husp = period['husp']
        if 'startTime' in period:
            self.startTime = period['startTime']


    def getTemperature(self):
        return self.temperature

    def getHumidity(self):
        return self.humidity

    def getSystemMode(self):
        return self.systemMode

    def getFanMode(self):
        return self.fanMode

    def getHumidityMode(self):
        return self.humidityMode

    def getCoolSP(self):
        return self.csp

    def getHeatSP(self):
        return self.hsp

    def getTargetTemperatureF(self):
        if self.systemMode == 'off':
            return None
        if self.systemMode == 'cool':
            return self.csp
        if self.systemMode == 'heat':
            return self.hsp

    def getManualModeScheduleId(self) ->int:
        return 16 + self.id

    def getOverdideScheduleId(self) ->int:
        return 32 + self.id


    def isZoneManualMode(self) -> bool:
        if self.scheduleId == self.getManualModeScheduleId():
            return True
        return False

    def isZoneOveride(self) -> bool:
        if self.scheduleId == self.getOverdideScheduleId():
            return True
        return False


    async def setHeatCoolSPF(self, r_hsp, r_csp):
        _LOGGER.info("lennox_zone:setHeatCoolSPF  id [" + str(self.id) + "] hsp [" + str(r_hsp) + "] csp [" + str(r_csp) + "]") 
        # If the zone is in manual mode, the temperature can just be set.
        if self.isZoneManualMode() == True:
            _LOGGER.info("lennox_zone:setHeatCoolSPF zone in manual mode id [" + str(self.id) + "] hsp [" + str(r_hsp) + "] csp [" + str(r_csp) + "]") 
            return await self._system.setHeatCoolSPF(self.id, self.getManualModeScheduleId(), r_hsp, r_csp)
        # If the zone is already over-ridden then we can just set the temperature
        if self.isZoneOveride() == True:
            _LOGGER.info("lennox_zone:setHeatCoolSPF zone in override mode id [" + str(self.id) + "] hsp [" + str(r_hsp) + "] csp [" + str(r_csp) + "]") 
            return await self._system.setHeatCoolSPF(self.id, self.getOverdideScheduleId(), r_hsp, r_csp)

        # Otherwise, we are following a schedule and need to switch into manual over-ride
        # Copy all the data over from the current executing period
        _LOGGER.info("lennox_zone:setHeatCoolSPF zone following schedule, adjusting override schedule [" + str(self.id) + "] hsp [" + str(r_hsp) + "] csp [" + str(r_csp) + "]") 
        hsp = str(int(r_hsp))
        hspC = str(self._system.convertFtoC(r_hsp))
        csp = str(int(r_csp))
        cspC = str(self._system.convertFtoC(r_csp))

        data = '"Data":{"schedules":[{"schedule":{"periods":[{"id":0,"period":'
        data += '{"desp":' + str(self.desp) + ','
        data += '"hsp":' + str(hsp) + ','
        data += '"cspC":' + str(cspC) + ','
        data += '"sp":' + str(self.sp) + ','
        data += '"husp":' + str(self.husp) + ','
        data += '"humidityMode":"' + str(self.humidityMode) + '",'
        data += '"systemMode":"' + str(self.systemMode) + '",'
        data += '"spC":' + str(self.spC) + ','
        data += '"hspC":' + str(hspC) + ','
        data += '"csp":' + str(csp) + ','
        data += '"startTime":' + str(self.startTime) + ','
        data += '"fanMode":"' + self.fanMode + '"}'
        data += '}]},"id":' + str(self.getOverdideScheduleId()) + '}]}'

        result = await self._system.api.publishMessageHelper(self._system.sysId, data)
        if result is False:
            _LOGGER.error("lennox_zone:setHeatCoolSPF failed to create override - zone [" + str(self.id) + "] hsp [" + str(r_hsp) + "] csp [" + str(r_csp) + "]") 
            return False

        _LOGGER.info("lennox_zone:setHeatCoolSPF placing zone in override hold - zone [" + str(self.id) + "] hsp [" + str(r_hsp) + "] csp [" + str(r_csp) + "]") 
        # Add a schedule hold to the zone, for now all hold will expire on next period
        data = '"Data":{"zones":[{"config":{"scheduleHold":'
        data += '{"scheduleId":' + str(self.getOverdideScheduleId()) + ','
        data += '"exceptionType":"hold","enabled":true,"expiresOn":"0","expirationMode":"nextPeriod"}'
        data += '},"id":' + str(self.id) + '}]}'

        result = await self.setScheduleHold(True)
        if result is False:
            _LOGGER.error("lennox_zone:setHeatCoolSPF failed to create schedule hold - zone [" + str(self.id) + "] hsp [" + str(r_hsp) + "] csp [" + str(r_csp) + "]") 
            return False
        return True

    async def setScheduleHold(self, hold:bool) -> bool:
        if hold == True:
            strHold = 'true'
        else:
            strHold = 'false'

        _LOGGER.info("lennox_zone:setScheduleHold zone [" + str(self.id) + "] hold [" + str(strHold) + "]") 

        # Add a schedule hold to the zone, for now all hold will expire on next period
        data = '"Data":{"zones":[{"config":{"scheduleHold":'
        data += '{"scheduleId":' + str(self.getOverdideScheduleId()) + ','
        data += '"exceptionType":"hold","enabled":' + strHold + ','
        data += '"expiresOn":"0","expirationMode":"nextPeriod"}'
        data += '},"id":' + str(self.id) + '}]}'
        result =  await self._system.api.publishMessageHelper(self._system.sysId, data)
        if result is False:
            _LOGGER.error("lennox_zone:setScheduleHold failed zone [" + str(self.id) + "] hold [" + str(strHold) + "]") 
            return False
        return True

    async def setCoolSPF(self, r_csp):
        _LOGGER.info("lennox_zone:setCoolSPF  id [" + str(self.id) + "] csp [" + str(r_csp) + "]") 
        # Lennox API always sends both values, snag the current
        r_hsp = self.hsp
        result = await self.setHeatCoolSPF(r_hsp, r_csp)
        if result is False:
            _LOGGER.error("lennox_zone:setCoolSPF failed zone [" + str(self.id) + "] csp [" + str(r_csp) + "]")
            return False
        return True

    async def setHeatSPF(self, r_hsp):
        _LOGGER.info("lennox_zone:setHeatSPF  id [" + str(self.id) + "] hsp [" + str(r_hsp) + "]") 
        # Lennox API always sends both values, snag the current
        r_csp = self.csp
        result = await self.setHeatCoolSPF(r_hsp, r_csp)
        if result is False:
            _LOGGER.error("lennox_zone:setHeatSPF failed id [" + str(self.id) + "] hsp [" + str(r_hsp) + "]")
            return False
        return True

    async def setSchedule(self, scheduleName):
        scheduleId = None
        for schedule in self._system.getSchedules():
            # Everything above 16 seems to be internal schedules
            if schedule.name == scheduleName:
                scheduleId = schedule.id
                break

        if scheduleId == None:
            _LOGGER.error("setSchedule - unknown schedule [" + scheduleName + "] zone [" + self.name + "]")
            return False

        return await self._system.setSchedule(self.id, scheduleId)

    async def setFanMode(self,fan_mode):
        if self.isZoneManualMode() == True:
            return await self._system.setFanMode(fan_mode, self.getManualModeScheduleId())
        if self.isZoneOveride() == False:
            data = '"Data":{"schedules":[{"schedule":{"periods":[{"id":0,"period":'
            data += '{"desp":' + str(self.desp) + ','
            data += '"hsp":' + str(self.hsp) + ','
            data += '"cspC":' + str(self.cspC) + ','
            data += '"sp":' + str(self.sp) + ','
            data += '"husp":' + str(self.husp) + ','
            data += '"humidityMode":"' + str(self.humidityMode) + '",'
            data += '"systemMode":"' + str(self.systemMode) + '",'
            data += '"spC":' + str(self.spC) + ','
            data += '"hspC":' + str(self.hspC) + ','
            data += '"csp":' + str(self.csp) + ','
            data += '"startTime":' + str(self.startTime) + ','
            data += '"fanMode":"' + self.fanMode + '"}'
            data += '}]},"id":' + str(self.getOverdideScheduleId()) + '}]}'        

            await self._system.api.publishMessageHelper(self._system.sysId, data)
            await self.setScheduleHold(True)
        return await self._system.setFanMode(fan_mode, self.getOverdideScheduleId())

    async def setHVACMode(self, hvac_mode):
        if (self.isZoneManualMode() == False):
            await self._system.setSchedule(self.id, self.getManualModeScheduleId())
        await self._system.setHVACMode(hvac_mode, self.getManualModeScheduleId())

     

class lennox_schedule(object):
    def __init__(self, id):
        self.id = id
        self.name = '<Unknown>'
        self.periodCount = -1
        self._periods = []

    def getOrCreatePeriod(self, id):
        item = self.getPeriod(id)
        if item != None:
            return item
        item = lennox_period(id)
        self._periods.append(item)
        return item

    def getPeriod(self, id):
        for item in self._periods:
            if item.id == id:
                return item
        return None

    def update(self, tschedule):
        if 'schedule' not in tschedule:
            return
        schedule = tschedule['schedule']
        if 'name' in schedule:
            self.name = schedule['name']
        if 'periodCount' in schedule:
            self.periodCount = schedule['periodCount']
        if 'periods' in schedule:
            for periods in schedule['periods']:
                periodId = periods['id']
                lperiod = self.getOrCreatePeriod(periodId)
                lperiod.update(periods)




class lennox_period(object):
    def __init__(self, id):
        self.id = id
        self.enabled = False
        self.startTime = None
        self.systemMode = None
        self.hsp = None
        self.hspC = None
        self.csp = None
        self.cspC = None
        self.sp = None
        self.spC = None
        self.humidityMode = None
        self.husp = None
        self.desp = None
        self.fanMode = None

    def update(self, periods):
        if 'enabled' in periods:
            self.enabled = periods['enabled']
        if 'period' in periods:
            period = periods['period']
            if 'startTime' in period:
                self.startTime = period['startTime']
            if 'systemMode' in period:
                self.systemMode = period['systemMode']
            if 'hsp' in period:
                self.hsp = period['hsp']
            if 'hspC' in period:
                self.hspC = period['hspC']
            if 'csp' in period:
                self.csp = period['csp']
            if 'cspC' in period:
                self.cspC = period['cspC']
            if 'sp' in period:
                self.sp = period['sp']
            if 'spC' in period:
                self.spC = period['spC']
            if 'humidityMode' in period:
                self.humidityMode = period['humidityMode']
            if 'husp' in period:
                self.husp = period['husp']
            if 'desp' in period:
                self.desp = period['desp']
            if 'fanMode' in period:
                self.fanMode = period['fanMode']
    