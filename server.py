#!/usr/bin/env python3
from apiclient.discovery import build
from oauth2client import file,client,tools
from httplib2 import Http
from json import dumps,loads
from os import path,system
from sys import exit
from hashlib import md5
from datetime import datetime

#Setup the drive v3 API
SCOPES='https://www.googleapis.com/auth/drive'
store = file.Storage('credentials.json')
creds = store.get()
if not creds or creds.invalid:
	flow = client.flow_from_clientsecrets('client_secret.json',SCOPES)
	creds = tools.run_flow(flow, store)
service =  build('drive', 'v3', http=creds.authorize(Http()))

def md5cal(fname):
    hash_md5 = md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4*1024**2), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def mailme():
	system('echo "MAIL FROM: log@teamultimate.in\nRCPT TO: mregrey@protonmail.com\nDATA\nSubject:Backup LOGS\n`tail -n3 log.txt`\n.\nquit\n" | nc 127.0.0.1 25')

chunk_size=int(8*1024*1024)
file_path = "/root/fsck/tuup.tar.gz"
file_name=file_path.split('/')[-1]
file_size=path.getsize(file_path)
md5sum_loc=md5cal(file_path)
auth_token=creds.access_token
method="PUT"
#Call the Drive v3 API
results = service.files().list(
	pageSize=10, fields="nextPageToken, files(id, name, size, md5Checksum)").execute()
items = results.get('files', [])

if not items:
	with open("/root/fsck/log.txt","a") as g:
		g.write(str(datetime.now())+" [!] NO files found !\n")
	mailme()
else:
	for item in items:
		if item['name'] == file_name:
			if item['md5Checksum']==md5sum_loc:
				with open("/root/fsck/log.txt","a") as g:
					g.write(str(datetime.now())+" [i] File is already uptodate.\n")
				mailme()
				exit(0)
			fileId=item['id']
			method="PATCH"

h = Http(".cache")
api_url="https://www.googleapis.com/upload/drive/v3/files"
if method=="PATCH":
	with open("/root/fsck/log.txt","a") as g:
		g.write(str(datetime.now())+" [i] Patching file to newer version.\n")
	api_url+="/"+fileId

up_api=api_url+"?uploadType=resumable"
body={
		'name':file_name
	}

headers={
		'Authorization':'Bearer '+auth_token,
		'Content-type': 'application/json; charset=UTF-8',
		'X-Upload-Content-Length':str(file_size)
		}

resp , content = h.request(up_api,method if method=="PATCH" else "POST",headers= headers,body=dumps(body))
if resp.status == 200:
	resume_uri = resp['location']
	f=open(file_path,"rb")
	sent=0
	while f.tell() < file_size:
		body=f.read(chunk_size)
		headers={
			'Content-type': 'application/octet-stream',
			'Content-length':str(len(body)),
			'Content-range':'bytes '+str(sent)+'-'+str(f.tell()-1)+'/'+str(file_size)
			}
		resp, content = h.request(resume_uri,method,headers= headers,body=body)
		if resp.status==200 or resp.status==201:
			results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name, size, md5Checksum)").execute()
			items = results.get('files', [])
			for item in items:
				if item['name'] == file_name:
					if item['md5Checksum']==md5sum_loc:
						with open("/root/fsck/log.txt","a") as g:
							g.write(str(datetime.now())+" [*] File uploaded successfully.\n")
						mailme()
					else:
						with open("/root/fsck/log.txt","a") as g:
							g.write(str(datetime.now())+" [!] Hash match failed !\n")
						mailme()
			break
		sent=int(resp['range'].split('-')[1])+1
		f.seek(sent)

	f.close()
else:
	with open("/root/fsck/log.txt","a") as g:
		g.write(str(datetime.now())+" [!] Some error occured ! Response Code:",resp.status,"\n")
	mailme()