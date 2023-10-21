from pathlib import Path
import sys,json
from patchtool import Revanced
import webbrowser
# For PyQt5 :
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut, QWidget, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox, QVBoxLayout, QLineEdit, QFormLayout, QCheckBox,QTableWidget, QTableWidgetItem, QHeaderView,QPushButton,QFileDialog,QPlainTextEdit
from PyQt5 import QtWidgets, QtCore
# import qdarktheme
import qdarkstyle
from PyQt5.QtGui import QKeySequence, QColor
from pyqtspinner import WaitingSpinner

class ProcessWindow(QDialog):

	def __init__(self,command):
		super().__init__()
		self.command = command
		self.p = None
		self.error = ''
		self.res = ''
		self.btn = QPushButton("Execute")
		self.btn.pressed.connect(self.start_process)
		self.text = QPlainTextEdit()
		self.text.setReadOnly(True)

		l = QVBoxLayout()
		l.addWidget(self.btn)
		l.addWidget(self.text)

		
		self.setLayout(l)

	def message(self, s):
		self.text.appendPlainText(s)

	def start_process(self):
		if self.p is None:  # No process running.
			self.message("Executing process")
			self.p = QtCore.QProcess()  # Keep a reference to the QProcess (e.g. on self) while it's running.
			self.p.readyReadStandardOutput.connect(self.handle_stdout)
			self.p.readyReadStandardError.connect(self.handle_stderr)
			self.p.stateChanged.connect(self.handle_state)
			self.p.finished.connect(self.process_finished)  # Clean up once complete.
			self.p.start(self.command)

	def handle_stderr(self):
		data = self.p.readAllStandardError()
		stderr = bytes(data).decode("utf8")
		self.error += stderr
		self.message(stderr)

	def handle_stdout(self):
		data = self.p.readAllStandardOutput()
		stdout = bytes(data).decode("utf8")
		self.res += stdout
		self.message(stdout)

	def handle_state(self, state):
		states = {
			QtCore.QProcess.NotRunning: 'Not running',
			QtCore.QProcess.Starting: 'Starting',
			QtCore.QProcess.Running: 'Running',
		}
		state_name = states[state]
		self.message(f"State changed: {state_name}")

	def process_finished(self):
		self.message("Process finished.")
		self.p = None

class OptionsDialog(QDialog):
	
	def __init__(self, name, options):
		super().__init__()
		self.fields = {}

		self.setWindowTitle(f"Options: {name}")

		QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

		self.buttonBox = QDialogButtonBox(QBtn)
		self.buttonBox.accepted.connect(self.accept)
		self.buttonBox.rejected.connect(self.reject)

		self.form = QFormLayout()
		for opt in options.values():
			if isinstance(opt['value'],bool):
				i = QCheckBox()
				i.setCheckState(2)
				i.stateChanged.connect(lambda text: self.update(opt['key'],bool(text)))
			else:
				i = QLineEdit()
				i.setText(opt['value'])
				i.textChanged.connect(lambda text: self.update(opt['key'],text))
			self.fields[opt['key']] = {
				'key':opt['key'],
				'value':opt['value'],
				'w':i
			}
			self.form.addRow(f"{opt['title']}:\n{opt['description']}",i)
		self.form.addWidget(self.buttonBox)
		self.setLayout(self.form)

	def update(self,field,value):
		self.updated = True
		self.fields[field]['value'] = value

	def accept(self):
		if self.updated:
			for v in self.fields.values():			
				v.pop('w')
			super().accept()

class ApkDetailView(QListWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.parent = parent
		self.app = parent.app
		self.apk = self.parent.apkdetails
		self.options = {}
		# Right Click Menu
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.right_menu)

	def loadDefaults(self):
		defaults = {}
		for patch in self.app.patches:
			if len(patch.options) > 0 :
				defaults[patch.name] = patch.model_dump()
				defaults[patch.name]['options'] = {}
				for option in patch.options:
					defaults[patch.name]['options'][option.key] = option.model_dump()
					pass
		self.options = defaults
		if self.apk.options.exists():
			opts = json.loads(self.apk.options.read_text())
			for x in opts:
				for y in x['options']:
					self.options[x['patchName']]['options'][y['key']].update(y)

	def loadList(self):
		self.clear()
		self.loadDefaults()
		for patch in self.app.patches:
			item = QListWidgetItem(patch.name)
			if patch.use:
				item.setCheckState(2)
			else:
				item.setCheckState(0)
			if patch.versions is not None and self.parent.apkdetails.version not in patch.versions:
				item.setBackground( QColor('#880000') )
				item.setCheckState(0)
			if any(x for x in patch.options if x.required):
				item.setBackground( QColor('#000088') )
				if item.checkState() == 2:
					item.setCheckState(1)
			self.addItem(item)

	def right_menu(self,pos):
		
		menu = QtWidgets.QMenu()
		key = self.currentItem().text()
		# Add menu options
		addAll_option = menu.addAction('SetOption')

		# Menu option events
		addAll_option.triggered.connect(self.set_Option)

		# Position
		menu.exec_(self.mapToGlobal(pos))
	
	def set_Option(self):
		key = self.currentItem().text()
		k = OptionsDialog(key,self.options[key]['options'])
		if k.exec_():
			for x,y in k.fields.items():
				self.options[key]['options'][x].update(y)
			self.save_Options()
		pass
  
	def save_Options(self):	
		tmp = []
		for x in self.options.values():
			tmp.append({
				'patchName':x['name'],
				'options':[{'key':y['key'],'value':y['value']} for y in x['options'].values()]
			})

		json.dump(tmp,self.apk.options.open('w'))

class ApkListView(QWidget):
	def __init__(self, folder,parent=None):
		super().__init__(parent)
		self.parent = parent
		self.folder = folder
		self.layout = QtWidgets.QGridLayout()
		self.setLayout(self.layout)
		self.app = None
		self.apkdetails = None
		self.apks = {}
		self.apps = {}
		# self.loadAPKs()
		self.loadTable()
		# Right Click Menu
		self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.right_menu)

	def loadTable(self):
		self.wlist = QTableWidget()
		self.wlist.verticalHeader().hide()
		self.apkdetailslist = ApkDetailView(self)
		self.details = QtWidgets.QTextBrowser()
  
		self.commandBtn = QPushButton()
		self.commandBtn.setText('Show Command')
		self.runBtn = QPushButton()
		self.runBtn.setText("Run Command")
		self.saveBtn = QPushButton()
		self.saveBtn.setText('Save Patches')
  
		self.apklist = list(self.folder.rglob('*.apk'))

		self.wlist.setRowCount(len(self.apklist))
		self.wlist.setColumnCount(3)
		self.wlist.setHorizontalHeaderLabels(['name','version','update'])
		count =0
		for apk in self.apklist:
			apkinfo = self.parent.rev.loadAPK(apk)
			if apkinfo is None: continue
			self.apks[apk.as_posix()] = apkinfo
			self.apps[apk.as_posix()] = self.parent.rev.getApkPatches(apkinfo.name)

			self.wlist.setItem(count,0, QTableWidgetItem(apk.as_posix())) 
			self.wlist.setItem(count,1, QTableWidgetItem(apkinfo.version)) 
			self.wlist.setItem(count,2, QTableWidgetItem(self.apps[apk.as_posix()].getLatest()))

			count+=1
		self.wlist.horizontalHeader().setStretchLastSection(True) 
		self.wlist.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) 
		self.wlist.resizeColumnsToContents()
  
		self.layout.addWidget(self.wlist,1,1,1,3)
		self.layout.addWidget(self.details,2,1,1,1)
		self.layout.addWidget(self.apkdetailslist,2,2,1,2)
  
		self.layout.addWidget(self.commandBtn,3,1,1,1)
		self.layout.addWidget(self.runBtn,3,2,1,1)
		self.layout.addWidget(self.saveBtn,3,3,1,1)


		self.commandBtn.clicked.connect(self.command)
		self.saveBtn.clicked.connect(self.savePatches)
		self.runBtn.clicked.connect(self.runCommand)
		self.wlist.clicked.connect(self.loadAPKDetails)
		self.wlist.doubleClicked.connect(self.openMirror)

	def savePatches(self):
		if self.wlist.item(self.wlist.currentRow(), 0) is None: return
		ca = self.wlist.item(self.wlist.currentRow(), 0).text()
		checked_items = []
		for index in range(self.apkdetailslist.count()):
			if self.apkdetailslist.item(index).checkState() == QtCore.Qt.Checked:
				checked_items.append(self.apkdetailslist.item(index).text())
		if len(checked_items) > 0:
			json.dump(checked_items,self.apks[ca].patches.open('w'))

	def runCommand(self):
		if self.wlist.item(self.wlist.currentRow(), 0) is None: return
		ca = self.wlist.item(self.wlist.currentRow(), 0).text()
		command = self.command()
		self.term = ProcessWindow(command)
		self.term.exec_()
		pass

	def command(self):
		if self.wlist.item(self.wlist.currentRow(), 0) is None: return
		ca = self.wlist.item(self.wlist.currentRow(), 0).text()
		self.savePatches()
		res = self.parent.rev.getPatchCommand(self.apks[ca])
		self.details.setText(res)
		return res

	def loadAPKDetails(self):
		self.apkoptions = {}
		if self.wlist.item(self.wlist.currentRow(), 0) is None: return
		ca = self.wlist.item(self.wlist.currentRow(), 0).text()
		self.apkdetails = self.apks[ca]
		self.app = self.apps[ca]
		self.apkdetailslist.app = self.app
		self.apkdetailslist.apk = self.apkdetails
	  
		self.apkdetailslist.loadList()
		
	def openMirror(self):
		url = f"https://www.apkmirror.com/?s='{self.apkdetails['name']}'"
		webbrowser.open(url)
		pass

	def right_menu(self,pos):
		
		menu = QtWidgets.QMenu()
		# Add menu options
		addAll_option = menu.addAction('Normalize')

		# Menu option events
		addAll_option.triggered.connect(self.normalize)

		# Position
		menu.exec_(self.mapToGlobal(pos))

	def normalize(self):
		ca = self.wlist.item(self.wlist.currentRow(), 0)
		if self.apks[ca.text()].normalizeName():
			ca.setText(self.apks[ca.text()].path.as_posix())

class MainWindow(QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		self.rev = Revanced()

		# self.setGeometry(1000, 1000, 300, 300)
		self.folder = self.rev.settings.apkFolder
		self.currentlayout = None
		self.centerW = None
  
		self.ref = QtWidgets.QLabel('Wait...', self)

		# keyboard shortcuts used to work but need to update their code since the way the players are loaded has changed
		self.shortcut = QShortcut(QKeySequence("F5"), self)
		self.shortcut.activated.connect(self.reload)

		self.setFullscreen = QShortcut(QKeySequence("F11"), self)
		# self.setFullscreen.activated.connect(self.toggleFullScreen)

		menu_bar = self.menuBar()
		# Right Click Menu
		# self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		# self.customContextMenuRequested.connect(self.right_menu)

		# View menu
		view_menu = menu_bar.addMenu("View")

		# Add actions to view menu
		load_action = QtWidgets.QAction("ReLoad", self)
		folder_action = QtWidgets.QAction("Select Folder", self)
		toggle_action = QtWidgets.QAction("Toggle Layout", self)
		close_action = QtWidgets.QAction("Close App", self)

		view_menu.addAction(folder_action)
		view_menu.addAction(load_action)
		view_menu.addAction(toggle_action)
		view_menu.addAction(close_action)

		folder_action.triggered.connect(self.selectFolder)
		close_action.triggered.connect(sys.exit)
		load_action.triggered.connect(self.reload)

		self.setWindowTitle("ReVancedGEN")
		self.startView()
		self.show()

	def startView(self):
		self.lsv = ApkListView(self.folder,self)
		self.centerW = self.lsv
		self.setCentralWidget(self.centerW)

	def reload(self):
		spinner = WaitingSpinner(self, True, True)
		spinner.start()
		self.startView()
		spinner.stop()
  
	def selectFolder(self):
		dialog = QFileDialog()
		dialog.setFileMode(QFileDialog.DirectoryOnly)
		if dialog.exec_() == QDialog.Accepted:
			path = dialog.selectedFiles()[0]  # returns a list
			self.folder = Path(path)
			self.reload()
		pass


if __name__ == '__main__':
	if len(sys.argv)>1:
		rev = Revanced()
		rev.run()
	app = QApplication(sys.argv)
	app.setStyleSheet(qdarkstyle.load_stylesheet())
	w = MainWindow()
	sys.exit(app.exec_())
