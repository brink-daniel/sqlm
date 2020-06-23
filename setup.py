from setuptools import setup

setup(
	name='sqlm',
	version='0.1',
	py_modules=['sqlm'
	],
	install_requires=[
		'Click',
		'pyodbc'
	],
	entry_points='''
		[console_scripts]
		sqlm=sqlm:cli
	'''	
)
