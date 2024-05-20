from pathlib import Path
import sys,json
from patchtool import Revanced
import webbrowser
# For PyQt5 :
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut, QWidget, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox, QVBoxLayout, QLineEdit, QFormLayout, QCheckBox,QTableWidget, QTableWidgetItem, QHeaderView,QPushButton,QFileDialog,QPlainTextEdit, QLabel, QProgressDialog, QProgressBar
from PyQt5 import QtWidgets, QtCore
# import qdarktheme
import qdarkstyle
from PyQt5.QtGui import QKeySequence, QColor
from pyqtspinner import WaitingSpinner

class ProcessWindow(QDialog):

	def __init__(self,app,command,auto=False,progress=None):
		super().__init__()
		self.progress = progress
		self.command = command
		self.p = None
		self.auto = auto
		self.error = ''
		self.res = ''
		self.btn = QPushButton(f"Execute: {app}")
		self.btn.pressed.connect(self.start_process)
		self.text = QPlainTextEdit()
		self.text.setReadOnly(True)

		l = QVBoxLayout()
		if progress is not None:
			l.addWidget(progress)
		l.addWidget(self.btn)
		l.addWidget(self.text)

		
		self.setLayout(l)
		if self.auto:
			self.start_process()

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
		if self.auto:
			super().accept()

class OptionsDialog(QDialog):
	
	def __init__(self, patch):
		super().__init__()
		self.updated = False
		self.patch = patch
		self.setWindowTitle(f"Options: {patch.name}")
		self.description = QLabel(self)
		self.description.setText(patch.description)
		self.description.setAlignment(QtCore.Qt.AlignCenter)
		QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

		self.buttonBox = QDialogButtonBox(QBtn)
		self.buttonBox.accepted.connect(self.submit)
		self.buttonBox.rejected.connect(self.reject)

		self.form = QFormLayout()
		self.form.addWidget(self.description)
		
		for opt in patch.options.values():
			if isinstance(opt.value,bool):
				i = QCheckBox()
				i.setCheckState(opt.value)
				i.stateChanged.connect(lambda text: self.update(opt.key,bool(text)))
			else:
				i = QLineEdit()
				i.setText(opt.value)
				i.textChanged.connect(lambda text: self.update(opt.key,text))
			self.form.addRow(f"{opt.title}:\n{opt.description}",i)
		self.form.addWidget(self.buttonBox)
		self.setLayout(self.form)

	def update(self,field,value):
		self.updated = True
		self.patch.options[field].value = value

	def submit(self):
		if self.updated:
			super().accept()
		else:
			super().reject()

class ApkDetailView(QListWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.parent = parent
		self.app = parent.app
		self.apk = self.parent.apkdetails
		self.selectedPatch = None
		self.options = {}
		# Right Click Menu
		self.doubleClicked.connect(self.set_Option)
		self.itemClicked.connect(self.select)

	def select(self,item):
		self.selectedPatch = item

	def loadDefaults(self):
		if self.apk.options.exists():
			opts = json.loads(self.apk.options.read_text())
			for x in opts:
				for y in x['options']:
					try:
						self.app.patches[x['patchName']].options[y['key']].value = y['value']
					except:
						continue

	def loadList(self):
		self.selectedPatch = None
		self.clear()
		self.loadDefaults()
		for patch in self.app.patches.values():
			item = QListWidgetItem(patch.name)
			if patch.use:
				item.setCheckState(2)
			else:
				item.setCheckState(0)
			if patch.versions is not None and self.parent.apkdetails.version not in patch.versions:
				item.setBackground( QColor('#880000') )
				item.setCheckState(0)
			if any(x for x in patch.options.values()):
				item.setBackground( QColor('#000055') )
			if any(x for x in patch.options.values() if x.required):
				item.setBackground( QColor('#000088') )
				if item.checkState() == 2:
					item.setCheckState(1)
			self.addItem(item)

	def set_Option(self):
		k = OptionsDialog(self.app.patches[self.selectedPatch.text()])
		if k.exec_():
			self.save_Options()
			self.selectedPatch.setCheckState(2)
		pass
  
	def save_Options(self):	
		json.dump(self.app.getOptions(),self.apk.options.open('w'))

class ApkListView(QWidget):
	def __init__(self, folder,parent=None):
		super().__init__(parent)
		self.parent = parent
		self.folder = folder
		self.layout = QtWidgets.QGridLayout()
		self.setLayout(self.layout)
  
		self.selectedAPK = None
		self.selectedAPKtext = None
		self.app = None
		self.apkdetails = None

		self.apks = {}
		self.apps = {}
		self.loadTable()

		# Right Click Menu

	def loadTable(self):
		self.apkTable = QTableWidget()
		self.apkTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.apkTable.customContextMenuRequested.connect(self.right_menu)
		self.apkTable.verticalHeader().hide()
		self.apkpatches = ApkDetailView(self)
		self.commandText = QtWidgets.QTextBrowser()
  
		self.commandBtn = QPushButton()
		self.commandBtn.setText('Show Command')
		self.runBtn = QPushButton()
		self.runBtn.setText("Run Command")
		self.saveBtn = QPushButton()
		self.saveBtn.setText('Save Patches')
  
		self.apklist = list(self.folder.rglob('*.apk'))

		self.apkTable.setRowCount(len(self.apklist))
		self.apkTable.setColumnCount(4)
		self.apkTable.setHorizontalHeaderLabels(['name','version','update','output'])
		self.apkTable.setColumnWidth(3,10)
		count =0
		for apk in self.apklist:
			apkinfo = self.parent.rev.loadAPK(apk)
			if apkinfo is None: continue
			self.apks[apk.as_posix()] = apkinfo
			self.apps[apk.as_posix()] = self.parent.rev.getApkPatches(apkinfo.name)

			self.apkTable.setItem(count,0, QTableWidgetItem(apk.as_posix())) 
			self.apkTable.setItem(count,1, QTableWidgetItem(apkinfo.version)) 
			self.apkTable.setItem(count,2, QTableWidgetItem(self.apps[apk.as_posix()].getLatest()))
			dld = QTableWidgetItem(str(apkinfo.outputFile))
			if apkinfo.outputFile.exists():
				dld.setBackground(QColor('#005500'))
			self.apkTable.setItem(count,3, dld)

			count+=1
		# self.apkTable.horizontalHeader().setStretchLastSection(True) 
		self.apkTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) 
		self.apkTable.resizeColumnsToContents()
  
		self.layout.addWidget(self.apkTable,1,1,1,3)
		self.layout.addWidget(self.commandText,2,1,1,1)
		self.layout.addWidget(self.apkpatches,2,2,1,2)
  
		self.layout.addWidget(self.commandBtn,3,1,1,1)
		self.layout.addWidget(self.runBtn,3,2,1,1)
		self.layout.addWidget(self.saveBtn,3,3,1,1)

		self.apkTable.itemClicked.connect(self.tableSelections)
		# self.apkTable.
		self.commandBtn.clicked.connect(self.command)
		self.saveBtn.clicked.connect(self.savePatches)
		self.runBtn.clicked.connect(self.runCommand)
		self.apkTable.clicked.connect(self.loadAPKPatches)
		self.apkTable.doubleClicked.connect(self.openMirror)

	def tableSelections(self,selection):
		self.selectedAPK = self.apkTable.item(selection.row(), 0)
		self.selectedAPKtext = self.selectedAPK.text()
		self.apkdetails = self.apks[self.selectedAPKtext]
		self.app = self.apps[self.selectedAPKtext]

	def savePatches(self):
		if self.selectedAPK is None: return
		checked_items = []
		for index in range(self.apkpatches.count()):
			if self.apkpatches.item(index).checkState() == QtCore.Qt.Checked:
				checked_items.append(self.apkpatches.item(index).text())
		if len(checked_items) > 0:
			json.dump(checked_items,self.apkdetails.patches.open('w'))

	def runCommand(self,auto=False):
		if self.selectedAPK is None: return
		command = self.command()
		if not command.startswith('ERROR:'):
			self.term = ProcessWindow(self.selectedAPKtext,command,auto)
			self.term.exec_()
			pass

	def command(self):
		if self.selectedAPK is None: return
		self.savePatches()
		res = self.parent.rev.getPatchCommand(self.apkdetails)
		self.commandText.setText(res)
		return res

	def loadAPKPatches(self):
		self.apkoptions = {}
		if self.selectedAPK is None: return
		self.apkpatches.app = self.app
		self.apkpatches.apk = self.apkdetails
	  
		self.apkpatches.loadList()
		
	def openMirror(self):
		url = f"https://www.apkmirror.com/?s='{self.apkdetails.name}'"
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
		if self.apkdetails.normalizeName():
			self.selectedAPK.setText(self.apkdetails.path.as_posix())

class ApksWindow(QDialog):

	def __init__(self,parent):
		super().__init__(parent)
		self.organizer = QtWidgets.QVBoxLayout()
		self.setLayout(self.organizer)
		self.apkTable = QTableWidget()
		# self.apkTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		# self.apkTable.customContextMenuRequested.connect(self.right_menu)
		self.apkTable.verticalHeader().hide()	
		self.apkTable.setRowCount(len(parent.rev.apps)-1)
		self.apkTable.setColumnCount(2)
		self.apkTable.setHorizontalHeaderLabels(['name','version'])
		self.apkTable.setColumnWidth(3,10)
		self.apks = {x:y for x,y in parent.rev.apps.items() if y.name != 'General Apps'}
		count = 0
		for apk in self.apks.values():

			self.apkTable.setItem(count,0, QTableWidgetItem(apk.name)) 
			self.apkTable.setItem(count,1, QTableWidgetItem(apk.getLatest()))
			# dld = QTableWidgetItem(str(apkinfo.outputFile))
			# if apkinfo.outputFile.exists():
			# 	dld.setBackground(QColor('#005500'))
			# self.apkTable.setItem(count,3, dld)

			count+=1
		self.apkTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) 
		self.apkTable.resizeColumnsToContents()
		self.organizer.addWidget(self.apkTable)
		self.apkTable.doubleClicked.connect(self.openMirror)

	def openMirror(self,selection):
		self.selectedAPK = self.apks[self.apkTable.item(selection.row(), 0).text()]
		version = self.apkTable.item(selection.row(), 1).text()
		q = self.selectedAPK.name
		if version != 'Latest':
			q += ' '+version
		url = f"https://www.apkmirror.com/?s={q}"
		webbrowser.open(url)
		pass

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
		patch_action = QtWidgets.QAction("Patch All", self)
		load_action = QtWidgets.QAction("ReLoad", self)
		folder_action = QtWidgets.QAction("Select Folder", self)
		toggle_action = QtWidgets.QAction("Toggle Layout", self)
		patches_action = QtWidgets.QAction("Show Apks", self)
		close_action = QtWidgets.QAction("Close App", self)

		view_menu.addAction(patch_action)
		view_menu.addAction(folder_action)
		view_menu.addAction(load_action)
		view_menu.addAction(toggle_action)
		view_menu.addAction(patches_action)
		view_menu.addAction(close_action)

		patches_action.triggered.connect(self.apks)
		patch_action.triggered.connect(self.patchAll)
		folder_action.triggered.connect(self.selectFolder)
		close_action.triggered.connect(sys.exit)
		load_action.triggered.connect(self.reload)

		self.setWindowTitle("ReVancedGEN")
		self.startView()
		self.show()

	def apks(self):
		self.ws = ApksWindow(self)
		self.ws.setWindowModality(QtCore.Qt.ApplicationModal)
		self.ws.show()

	def patchAll(self):
		sz = self.lsv.apkTable.rowCount()
		progress = QProgressBar(self)
		progress.setMinimum(0)
		progress.setMaximum(sz)
		self.rn = ProcessWindow('','',progress=progress)
		self.rn.auto = True
		self.rn.setWindowModality(QtCore.Qt.ApplicationModal)
		for row in range(sz):
			_item = self.lsv.apkTable.item(row, 0)
			self.lsv.tableSelections(_item)
			command = self.lsv.command()
			if not command.startswith('ERROR:'):
				self.rn.command = command
				self.rn.start_process()
				self.rn.show()
			self.rn.progress.setValue(row)

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
