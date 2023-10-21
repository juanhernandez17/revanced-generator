from pathlib import Path
import yaml,json
import re
from datetime import datetime
import unicodedata
from typing import Any

def handle_exceptions(f):
	def wrapper(*args, **kw):
		try:
			return *f(*args, **kw), True
		except Exception as e:
			return e, False
	return wrapper

def parse_date(value):
	formats = [
		"%Y-%m-%dT%H:%M:%SZ","%Y-%m-%d %H:%M:%S","%Y-%m-%d","%Y"
	]
	if value is not None:
		for format in formats:
			try:
				return datetime.strptime(value,format)
			except:
				continue
	return datetime.fromtimestamp(0)

class _settings:
	defaults = {
		'lastupDate':datetime.fromtimestamp(0).date(),
		'keystoreFile':'revanced\\revanced.keystore',
		'toolsjsonFile':'revanced\\tools.json',
		'optionsjsonFile':'revanced\\options.json',
		# tool folders
		'revancedcliFolder':'revanced\\revanced-cli',
		'revancedintegrationsFolder':'revanced\\revanced-integrations',
		'revancedpatchesFolder':'revanced\\revanced-patches',
		'apkFolder':'apks',
		'toolsjsonendpoint':'https://releases.revanced.app/tools',
		'apkeditorlink':'https://github.com/REAndroid/APKEditor/releases/latest',
		'aaptFile':'adb\\aapt',
		'outputFolder':'output', 
		'apksFolder':'apks',
		'javaFile':'zulu17\\bin\\java.exe',
		'revancedCacheFolder':'revanced-cache',
		"keystoreFile": "revanced\\revanced.keystore",
		"keystorealias": "revanced",
		"errorFile":"error.txt"
	}	
	settings = {}
	def __init__(self,configFile:Path):
		self.load_config(configFile)

	def __setattr__(self, name: str, value: Any) -> None:
		try:
			self.settings[name] = value
		except KeyError:
			return getattr(self.args, name)
		pass

	def __getattr__(self, name):
		try:
			return self.settings[name]
		except KeyError:
			return getattr(self.args, name)	# turn strings to Path types
	def load_config(self,configFile):
		print('Loading config',end='\r')
		if configFile.exists():
			config = self.defaults | yaml.load(configFile.read_text(),yaml.Loader)
		else: 
			config = self.defaults
		self.from_dict(config)

	def from_dict(self,data):
		for x, y in data.items():
			if x.endswith('Folder'):
				self.settings[x] = Path(y)
				self.settings[x].mkdir(parents=True,exist_ok=True)
			elif x.endswith('File'):
				self.settings[x] = Path(y)
			elif x.endswith('Date'):
				self.settings[x] = parse_date(y)
			else:
				self.settings[x] = y
				

	# turns a Path object into a nested dict
	def to_dict(self,data=None):
		if data is None: data=self.settings
		jsondata = {}
		for k,v in data.items():
			if k.endswith('Date'):
				jsondata[k] = v.strftime('%Y-%m-%d %H:%M:%S')
			else:
				jsondata[k] = str(v)
		return jsondata

  
# https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename
	# edited to not lowercase and allow dots
def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\.\w\s-]', '', value)
    return re.sub(r'[-\s]+', '-', value).strip('-_')