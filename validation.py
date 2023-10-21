from pydantic import  Field, AliasPath, validator, BaseModel
from typing import List, Optional,Annotated,Union
from pathlib import Path
from settings import slugify
class Option(BaseModel):
	key:str
	value:Union[bool, str,None] = Field(default=None,alias='default')
	title:str
	description:str
	required:bool
 
class Patch(BaseModel):
	name:str
	description:Optional[str] = Field(default=None)
	use:Optional[bool] = Field(default=None)
	requiresIntegrations:Optional[bool] = Field(default=None)
	options:List[Option]
	versions:Optional[List[str]] = Field(default=None)
	def getOptionsDict(self):
		return {x.key:x for x in self.options}

class App(BaseModel):
	name:str
	patches: List[Patch]
	def getLatest(self):
		newst = []
		for patch in self.patches:
			if patch.versions:
				newst += patch.versions
		if len(newst) > 0:
			return sorted(newst)[-1]
			
		return "Latest"
	def getPatches(self):
		for i in range(len(self.patches)):
			yield f'\t[{i:02}] - {self.patches[i].name:<50} - {self.patches[i].description} - Options:{len(self.patches[i].options)}'
   
   
   
class Apk(BaseModel):
	path:Path
	name:str
	version:str = Field(default="0.0")
	title:str
	outputFolder:Optional[Path] = Field(default=None)
	@property
	def errorLog(self):
		if self.outputFolder is None:
			return self.path.with_suffix('.error')
		return self.outputFile.with_suffix('.error')
	@property
	def options(self):
		return self.path.with_suffix('.json')
	@property
	def patches(self):
		return self.path.with_suffix('.patches.json')
	@property
	def outputFile(self):
		if self.outputFolder is not None:
			self.outputFolder.mkdir(parents=True,exist_ok=True)
			return self.outputFolder / f'ReVanced-{self.title}-{self.version}.apk'
	def normalizeName(self):
		if self.version != "0.0":
			uniformapk = self.path.parent / slugify(f'{self.title}-{self.version}.apk')
			if uniformapk != self.path and not uniformapk.exists():
				self.path = self.path.rename(uniformapk)
				return True
		return False