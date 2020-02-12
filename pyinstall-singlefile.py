if __name__ == '__main__':
	from PyInstaller.__main__ import run
	opts = ['main_fun.py', '-w','-D','-F','--icon=./IconFiles/BZT.ico']
	run(opts)