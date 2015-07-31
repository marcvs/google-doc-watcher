#!/usr/bin/env python 

import urllib2
import fileinput
from re import search
from datetime import datetime
import hashlib
import os
import argparse
import glob
from sys import stdout
import smtplib
import subprocess
# some timezone stuff
import pytz


defaultpath = os.getenv("HOME")+"/google-docs"


parser = argparse.ArgumentParser(description='batterymonitor')
parser.add_argument('--verbose','-v', dest='verbose', action='count',
					default=0)
parser.add_argument('--config','-c', dest='configfile',
					default=os.getenv("HOME")+"/.google-doc-downloaderrc")
parser.add_argument('--email','-e', dest='email',
					default="marcus@hardt-it.de")
parser.add_argument('--outputdir','-o', dest='basedir',
					default=defaultpath)
					#default=os.getenv("HOME")+"/.google-doc-downloader")
parser.add_argument('--width','-w', dest='mailOutputWidth',
					default=66)
parser.add_argument('--no-reflow', dest='mailOutputReflow',
					action='store_false', default=True)
parser.add_argument('--colordiffOptions', dest='colordiffOptions',
					default='-u7')
parser.add_argument('--ansi2html', dest='path_ansitohtml',
					default=defaultpath+"/ansi2html.sh")

args = parser.parse_args()

startupCwd = os.getcwd()
os.chdir(args.basedir)

def downloadFromGoogleDoc(resourceId, fileFormat, outputBaseFileWithDate):
	outputFile		= outputBaseFileWithDate+"."+fileFormat

	req=urllib2.Request("https://docs.google.com/feeds/download/documents/export/Export?id="+resourceId+"&exportFormat="+fileFormat)

	googledoc = urllib2.urlopen(req)

	file = open(outputFile, 'w+')
	file.write(googledoc.read())
	file.close()
	if args.verbose:
		for file in (glob.glob(args.basedir+"/"+outputBaseFileWithDate+"*")):
			print "=> %s" %file

def  ANewVersionWasDownloaded(outputBaseFile):
	retVal = True
	fileFormat = "txt"
	fileversions = (glob.glob(args.basedir+"/"+outputBaseFile+"*"+fileFormat))
	fileversions.sort()

	hashes = [(fversion, hashlib.md5(open(fversion, 'rb').read()).hexdigest()) for fversion in fileversions]
	previous_fileversion = ""
	previous_hashvalue	 = ""
	pre_previous_fileversion = ""
	for (fileversion, hashvalue) in hashes:
		if args.verbose:
			print (("\n%s : %s") % (fileversion, hashvalue))
		if (previous_hashvalue == hashvalue):
			os.remove (fileversion)
			retVal = False
		else:
			pre_previous_fileversion = previous_fileversion
			previous_fileversion = fileversion
			previous_hashvalue	 = hashvalue
	return retVal, os.path.basename(pre_previous_fileversion)

def sendMail(FROM, TO, SUBJECT, CONTENT):
	now = datetime.now(tz=pytz.timezone(os.getenv("TZ")))
	now = now.strftime("%a, %d %b %Y %H:%M:%S %z")

	# Import the email modules we'll need
	from email.mime.text import MIMEText
	from email.mime.multipart import MIMEMultipart

	htmlcontent = MIMEText(CONTENT, "html")
	msg = MIMEMultipart()

	msg['Subject'] = SUBJECT
	msg['From'] = FROM
	msg['To'] = TO
	msg['Date'] = now
	msg.preamble = "This is an email"
	msg.attach(htmlcontent)

	# Send the message via our own SMTP server, but don't include the
	# envelope header.
	s = smtplib.SMTP('hardt-it.de')
	s.sendmail(FROM, TO , msg.as_string())
	s.quit()

def shellcall(commandline):
	tmpout = "/tmp/google-doc-downloader-"+os.getpid().__str__()+"out"
	tmperr = "/tmp/google-doc-downloader-"+os.getpid().__str__()+"err"

	retval = subprocess.call(commandline, shell=True, 
					stdout = open(tmpout, "w"), stderr = open(tmperr, "w"))

	output = open(tmpout, "r").read()
	errors = open(tmperr, "r").read()

	os.remove (tmpout)
	os.remove (tmperr)

	return retval, output, errors

def  mailLatestDiff(outputBaseFile, newFile, oldFile, emails):
	fileFormat = 'txt'
	print "\nEmailing diffs for %s to" %(outputBaseFile)
	width = str(args.mailOutputWidth)

	tmp1 = "/tmp/google-doc-downloader-"+os.getpid().__str__()+outputBaseFile+"-old"
	tmp2 = "/tmp/google-doc-downloader-"+os.getpid().__str__()+outputBaseFile+"-new"

	if args.mailOutputReflow:
		shellcall ("cat "+oldFile+" | par "+width+" > "+tmp1)
		shellcall ("cat "+newFile+" | par "+width+" > "+tmp2)
	else:
		shellcall ("cat "+oldFile+" > "+tmp1)
		shellcall ("cat "+newFile+" > "+tmp2)

	(retval, output, errors) = shellcall ("colordiff "+args.colordiffOptions+" "+tmp1+" "+tmp2+" | "+ args.path_ansitohtml)

	os.remove (tmp1)
	os.remove (tmp2)

	for email in emails.split(":"):
		print ("    "+email)
		sendMail ("marcus@hardt-it.de", email, "Updates on %s" % outputBaseFile, output)

	print "email(s) sent"

def downloadFilesFromRc():
	now = datetime.now()
	now = now.strftime("%Y-%m-%d-%H:%M")
	print ("Checking for updates")
	for line in fileinput.input(args.configfile):
		# read line of config file
		if search ("#", line):
			continue
		if search ("^$", line):
			continue

		entries = line.split ()
		try:
			resourceId		= entries[0]
			outputBaseFile	= entries[1]
			fileFormats		= entries[2]
			emails			= entries[3]
		except IndexError:
			print ("""
Error Parsing the config:
You have probably not provided enough options in the config file. The template is as follows:

# google-doc-id                 outputfile      fileFormat # the txt version is always downloaded
1qtjlH2NzuOHkN11wJ9nz_NmddVHIGKS9BdDRqP1eOe4    aarc-amsterdam-report  pdf:doc:odt:docx:rtf:html marcus@hardt-it.de:hardt@kit.edu
1F8PI8q0KxtOg-GVqt17AR8K4UK-CvLwz4wTfcKmNY_8    indigo-d4.2             docx marcus@hardt-it.de:hardt@kit.edu

		""")

		# derive config based values
		outputBaseFileWithDate=outputBaseFile+"--"+now

		stdout.write ("%s: " % (outputBaseFile))
		stdout.flush()

		# download txt version
		downloadFromGoogleDoc(resourceId, 'txt', outputBaseFileWithDate)

		# check dupes
		(newFileAvailable, secondLastFileVersion) = ANewVersionWasDownloaded(outputBaseFile)
		if newFileAvailable:
			# if not dupe: download other formats
			stdout.write("Fetching new version: ")
			for fileFormat in fileFormats.split(":"):
				stdout.write ("[%s] " % fileFormat); stdout.flush()
				downloadFromGoogleDoc(resourceId, fileFormat, outputBaseFileWithDate)

			# send email with latest diff
			mailLatestDiff(outputBaseFile, outputBaseFileWithDate+".txt", secondLastFileVersion, emails)
		else:
			stdout.write ("No changes")


		print ("")

downloadFilesFromRc()

fnamelst = []
fnamelst.append("d4.2--2015-07-30-15:26.txt")

os.chdir(startupCwd)






#wget -O 2nd.odt https://docs.google.com/feeds/download/documents/export/Export?id=$resourceId&exportFormat=odt
