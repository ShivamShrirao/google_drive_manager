#!/usr/bin/env python3
from apiclient.discovery import build
from oauth2client import file,client,tools
from httplib2 import Http
from json import dumps,loads
from os import path
from sys import stdout

#Setup the drive v3 API
SCOPES='https://www.googleapis.com/auth/drive'
store = file.Storage('credentials.json')
creds = store.get()
if not creds or creds.invalid:
	flow = client.flow_from_clientsecrets('client_secret.json',SCOPES)
	creds = tools.run_flow(flow, store)
service =  build('drive', 'v3', http=creds.authorize(Http()))

print("[*] Logged in.")

file_path = "/home/archer/Downloads/sublime_text_3_build_3170_x64.tar.bz2"
file_name=file_path.split('/')[-1]
file_size=path.getsize(file_path)
auth_token=creds.access_token

#Call the Drive v3 API
results = service.files().list(
	pageSize=10, fields="nextPageToken, files(id, name, size, md5Checksum)").execute()
items = results.get('files', [])
print("[*] Current contents in drive:")
if not items:
	print('No files found.')
else:
	for item in items:
		print('\tName: %s\tSize: %.2f MB md5sum: %s id(%s)' % (item['name'], int(item['size'])/1024**2, item['md5Checksum'], item['id']))
		
h = Http(".cache")

api_url="https://www.googleapis.com/upload/drive/v3/files"
up_api=api_url+"?uploadType=resumable"
chunk_size=int(0.5*1024*1024)
body={
		'name':file_name
	}

headers={
		'Authorization':'Bearer '+auth_token,
		'Content-type': 'application/json; charset=UTF-8',
		'X-Upload-Content-Length':str(file_size)
		}

resp , content = h.request(up_api,"POST",headers= headers,body=dumps(body))
if resp.status == 200:
	resume_uri = resp['location']
	print("[*] Resume URI:",resume_uri)
	f=open(file_path,"rb")
	sent=0
	while f.tell() < file_size:
		body=f.read(chunk_size)
		headers={
			'Content-type': 'application/octet-stream',
			'Content-length':str(len(body)),
			'Content-range':'bytes '+str(sent)+'-'+str(f.tell()-1)+'/'+str(file_size)
			}
		print("[*] Sent",headers['Content-range'])
		resp, content = h.request(resume_uri,"PUT",headers= headers,body=body)
		try:
			print("[*] Received by server:",resp['range'])
		except:
			pass
		if resp.status==200 or resp.status==201:
			print("[*] File uploaded.")
			content=loads(content.decode("UTF-8"))
			print("Name: {0} id({1})".format(content["name"],content["id"]))
			break
		sent=int(resp['range'].split('-')[1])+1
		f.seek(sent)

	f.close()