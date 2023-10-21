from pathlib import Path
import requests
import json, yaml
import os
import re
import subprocess
from hashlib import md5
from tqdm import tqdm
import shutil
from datetime import datetime
import unicodedata
from validation import App
import atexit
from typing import Any
from settings import _settings, handle_exceptions
from validation import Apk
from tempfile import NamedTemporaryFile

class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKCYAN = '\033[96m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'


class Revanced:
	def __init__(self, settings='settings.yaml'):
		self.settingsFile = Path(settings)
		self.loadSettings()
		atexit.register(self.saveSettings)
		self.storepass = None
		self.loadPatches()
  
	def loadSettings(self):
		self.settings = _settings(self.settingsFile)
		self.getTools()
  
	def getLocalTools(self):
		files = list(self.settings.revancedcliFolder.rglob('revanced-cli*.jar'))
		self.revancedcli = max(files, key=os.path.getctime) if len(files)>0 else None
		files = list(self.settings.revancedintegrationsFolder.rglob('revanced-integrations*.apk'))
		self.revancedinteg = max(files, key=os.path.getctime) if len(files)>0 else None
		files = list(self.settings.revancedpatchesFolder.rglob('revanced-patches*.jar'))
		self.revancedpatch = max(files, key=os.path.getctime) if len(files)>0 else None
		files = list(self.settings.revancedpatchesFolder.rglob('revanced-patches*.json'))
		self.revancedpatches = max(files, key=os.path.getctime) if len(files)>0 else None
  
	def saveSettings(self):
		tmp = self.settings.to_dict()
		yaml.dump(tmp,self.settingsFile.open('w',encoding='utf-8'))

	def getTools(self):
		if self.settings.lastupDate != datetime.now().date():
			res = requests.get(self.settings.toolsjsonendpoint)
			if res.status_code == 200:
				tools = res.json()['tools']
				json.dump(tools, self.settings.toolsjsonFile.open('w'))
				self.settings.lastupDate = datetime.now().date()
				toollocation = None
				for tool in tqdm(tools, 'Getting Tools'):
					repo = tool['repository']
					ct = tool['content_type']
					if repo == 'revanced/revanced-patches' and ct == 'application/java-archive':
						toollocation = self.settings.revancedpatchesFolder / tool['name']
					elif repo == 'revanced/revanced-patches' and ct == 'application/json':
						toollocation = self.settings.revancedpatchesFolder / ('revanced-patches-' + tool['version'] + '.json')
					elif repo == 'revanced/revanced-integrations':
						toollocation = self.settings.revancedintegrationsFolder / tool['name']
					elif repo == 'revanced/revanced-cli':
						toollocation = self.settings.revancedcliFolder / tool['name']
					if toollocation and not toollocation.exists():
						dlTool(tool['browser_download_url'], toollocation)
		self.getLocalTools()

	def getApkInfo(self,apkpath):
		command = f'aapt dump badging "{apkpath.absolute().as_posix()}"'
		res, errors ,succ = self.launchCommand(command)
		if succ:
			res = res.decode()
			pat = r"package: name='(.*)' versionCode='[0-9]*' versionName='(.*)' "# platformBuildVersionName='[\w]*'"
			title = re.search(r"application-label:'(.*?)'",res).group(1).replace(' ', '_')
			name, ver = re.search(pat, res).groups()
			return Apk(
				path=apkpath,
				name= name,
				version= ver,
				title= title
			)
		if errors:
			self.settings.errorFile.open('a').write(errors)
		return None

	def loadPatches(self):
		self.apps = {}
		patches = json.load(self.revancedpatches.open('r'))
		tmp = {'defaults':{'name':"General Apps",'description':"Can be applied to any app",'patches':[patch for patch in patches if patch['compatiblePackages'] is None]}}
		for patch in patches:
			apps = patch.pop('compatiblePackages')
			if apps is None:
				continue
			for app in apps:
				apatch = patch.copy()
				apatch['versions'] = app.pop('versions')
				if app['name'] not in tmp:
					tmp[app['name']] = app
					tmp[app['name']]['patches'] = tmp['defaults']['patches']+[apatch]
				else:
					tmp[app['name']]['patches'].append(apatch)

		self.apps = {x:App(**y) for x,y in tmp.items()}

	def loadAPK(self,apkpath,normalize=False):
		apk = self.getApkInfo(apkpath)
		if normalize: apk.normalizeName()
		apk.outputFolder = self.settings.outputFolder
		return apk

	def run(self,apks:list=None,normalize=False,runcommand=True):
		if apks is None:
			apks = list(self.settings.apkFolder.rglob('*.apk'))
		for apkpath in tqdm(apks, 'Patching APKs'):
			apk = self.loadAPK(apkpath,normalize)
			command = self.getPatchCommand(apk)
			if runcommand and not command.startswith('ERROR:'):
				self.runCommand(command,apk)

	def runCommand(self,command,apk):
		res, errors ,succ = self.launchCommand(command)
		if errors:
			apk.errorLog.open('w').write(errors)
		return res,errors,succ

	def getPatchCommand(self,apk):
		patches = ''
		app = self.getApkPatches(apk.name)
		if apk.patches.exists():
			for i in json.loads(apk.patches.read_text()):
				patches += f' -i "{i}" '
		elif any(x for x in app.patches.values() if x.use):
			pass
		else:
			return "ERROR: No Patches Selected and No defaults Found"
		command = (
			f'"{self.settings.javaFile.absolute().as_posix()}" -jar ',
			f'"{self.revancedcli.absolute().as_posix()}" patch ', 
			f'--out "{apk.outputFile.absolute().as_posix()}" ',
			f'--patch-bundle "{self.revancedpatch.absolute().as_posix()}" ',
			f'--merge "{self.revancedinteg.absolute().as_posix()}" ' ,
			patches,
			f'--options "{apk.options.absolute().as_posix()}" ' if apk.options.exists() else '',
			# f'--keystore "{self.keystore.absolute().as_posix()}" --common-name Revanced '
			f'"{apk.path.absolute().as_posix()}"'
		)
		return ''.join(command)

	def getApkPatches(self,appname):
		if appname in self.apps:
			return self.apps[appname]
		return self.apps['defaults']

	@handle_exceptions
	def launchCommand(self,command):
		f = NamedTemporaryFile(mode='w', delete=False)
		res = subprocess.check_output(command, stderr=f)
		f.close()
		with open(f.name, "r") as new_f:
			errors = new_f.read()
			return res, errors

def genMD5(data):
	return md5(json.dumps(data).encode('utf-8')).hexdigest()

def dlTool(url, location):
	try:
		response = requests.get(url)
		with location.open("wb") as f:
			f.write(response.content)
		return True
	except:
		return False


if __name__ == "__main__":
	rev = Revanced()

	rev.run()
	