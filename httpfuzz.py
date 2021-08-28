#!/usr/bin/python3
import argparse
import os
import time
import threading
import math
import requests
import queue
import sys
import re
import json
import shutil

#save in /usr/sbin

class color:
	PURPLE = '\033[95m'
	CYAN = '\033[96m'
	DARKCYAN = '\033[36m'
	BLUE = '\033[94m'
	GREEN = '\033[92m'
	YELLOW = '\033[93m'
	RED = '\033[91m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'
	END = '\033[0m'

start_time = time.time()

#manage args

parser=argparse.ArgumentParser()
parser.add_argument('-w', '--wordlist',help="Word List")
parser.add_argument('-u','--url',help="URL with FUZZ keyword")
parser.add_argument('-H','--header',help="Add Header to requests, 'name: value'",action='append')
parser.add_argument('-t','--thread',help="Threads Count",default=1,type=int)
parser.add_argument('-r','--refresh',help="Refresh time (sec) interval.",default=5)
parser.add_argument('--redirect',help="Follow Redirect",action='store_true')
parser.add_argument('--cont',help="Continue Previous Scan, if Any",action='store_true')
parser.add_argument('--head',help="Perform Fuzzing with HEAD requests",action='store_true')

args=parser.parse_args()
if args.wordlist:
	wordlist=args.wordlist
else:
	wordlist=None

if args.url:
	url=args.url
	#create output direcotry as url name
	opdir = re.sub("[^0-9a-zA-Z]+", "_", url)

else:
	url=None
if args.thread:
	threads=args.thread
else:
	threads=None
if args.refresh:
	refresh=args.refresh
else:
	refresh=None
if args.redirect:
	redirect=args.redirect
else:
	redirect=False

if args.cont:
	script_continue=args.cont
else:
	script_continue=False

if args.head:
	headfuzz=args.head
else:
	headfuzz=False

if args.header:
	xheaders=args.header
else:
	xheaders=None



#default headers /useragent
headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36 Edg/91.0.864.37"}
if xheaders is not None:
	for key_val in xheaders:
		key=key_val.split(':')[0].strip()
		val=':'.join(key_val.split(':')[1:]).strip()
		headers[key]=val


#global vars

total_status={}
threads_active=0
status_dict={}
status_dict['url']=url
status_dict['wordlist']=os.path.abspath(wordlist)
status_dict['processed']=0
qlines=None


if (wordlist is None) or (not os.path.isfile(wordlist)):
		print("No Wordlist Found.\nGive with -w")
		exit()


def start_fuzz(th_i):

	global qlines,threads_active,headers,opdir,status_dict

	threads_active+=1
	
	while (not qlines.empty()):
		word=qlines.get()
		status_dict['processed']+=1
		nurl=url.replace('FUZZ',word)
		try:
			if headfuzz:
				r=requests.head(nurl,headers=headers,allow_redirects=redirect)
			else:
				r=r=requests.get(nurl,headers=headers,allow_redirects=redirect)
		except Exception as ex:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			status_key=str(exc_type)
			
		else:
			status_key=str(r.status_code)
		
		if status_key not in total_status:
			total_status[status_key]=1
		else:
			total_status[status_key]+=1
		status_key=re.sub("[^0-9a-zA-Z]+", "_", status_key)
		fd=open(opdir+"/"+status_key,"a")
		print(word,file=fd)
		fd.close()
		
		
		
	threads_active-=1


def start_fuzzing_with_threads():
	global wordlist,url,refresh,threads,total_status,xheaders,status_dict,qlines

	
	nlines=qlines.qsize()
	
	print(color.BOLD+str(nlines)+" Words, "+str(threads)+" Thread(s)."+color.END)
	th_list=[]
	
	for n in range(threads):

		th_list.append(threading.Thread(target=start_fuzz,args=(n,)))
	
	for th in th_list:
		th.start()


	return th_list








def main():
	global wordlist,url,refresh,threads,total_status,xheaders,status_dict,qlines
	


	if url is None:
		print("No URL found.\nGive with -u")
		exit()
	if 'FUZZ' not in url:
		print('Please Give FUZZ keyword in url')
		exit()

	if threads is None:
		threads=1

	if refresh is None:
		refresh=2

	status_fl=None
	#opdir
	if os.path.isdir(opdir):
		
		#read status file
		#check if status file is there
		if script_continue:
			if os.path.isfile(opdir+"/status.json"):
				with open(opdir+"/status.json") as jfl:
					status_fl=json.load(jfl)

		else:
			shutil.rmtree(opdir)
			os.mkdir(opdir)
			with open(opdir+'/status.json','w') as jfl:
				json.dump(status_dict,jfl)
	else:
		os.mkdir(opdir)
		with open(opdir+'/status.json','w') as jfl:
			json.dump(status_dict,jfl)

	all_lines=open(wordlist).readlines()
	all_lines=[x.strip() for x in all_lines]
	total_len=len(all_lines)
	if status_fl is not None:
		all_lines=all_lines[int(status_fl['processed']):]
		print(str(status_fl['processed'])+' Words, Already Processed. Continuing...')
		status_dict['processed']=int(status_fl['processed'])
	qlines=queue.Queue()
	[qlines.put(ln) for ln in all_lines]
		



	th_list=start_fuzzing_with_threads()
	

	
	while threads_active > 0:
		
		
		
		print('W:'+str(status_dict['processed'])+' Th:'+ str(threads_active)+' Res:'+str(total_status),end="\r")
		
		time.sleep(float(refresh))

	for th in th_list:
		th.join()

	print()
	print(color.BOLD+"Total Words Processed : "+str(status_dict['processed'])+color.END)
	print(total_status)
	
	print("Saved in "+color.GREEN+opdir+color.END)
	
	


	
		



if __name__ == "__main__":
	try:
		main()
	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(color.RED,end="")
		print(exc_type, fname, exc_tb.tb_lineno,end="")
		print(color.END)

	finally:
		with open(opdir+'/status.json','w') as jfl:
			json.dump(status_dict,jfl)

print("Finished in "+str(round(time.time() - start_time,2))+"s")
