import click
import curses
import pyodbc
import datetime
import threading
import time
import random


#curses pads
global pad_cpu, pad_info, pad_table

#general
global current_tab, height, width, middle, quarter, init_complete

#data
global data_cpu, data_mem, data_info, data_activity, data_jobs, data_waits, data_changes
global data_cpu_changed, data_mem_changed, data_info_changed, data_activity_changed, data_jobs_changed, data_waits_changed, data_changes_changed
global db_connection


#main entry point
@click.command()
@click.option('--instance', default=".")
@click.option('--user', default="sa")
@click.option('--password', prompt=True, hide_input=True,
			  confirmation_prompt=False)
def cli(instance:str, user:str, password:str):
	conn_test_result = test_connection(instance, user, password)
	if conn_test_result == "Success":
		curses.wrapper(draw_screen)
	else:
		click.echo(conn_test_result)


def test_connection(instance:str, user:str, password:str):
	try:
		open_conn(instance, user, password)
		return "Success"
	except pyodbc.Error as ex:
		return ex.args[1]

	


def draw_screen(stdscr):
	global current_tab, height, width, middle, quarter, init_complete
	global data_cpu, data_mem, data_info, data_activity, data_jobs, data_waits, data_changes
	global data_cpu_changed, data_mem_changed, data_info_changed, data_activity_changed, data_jobs_changed, data_waits_changed, data_changes_changed
	global pad_cpu, pad_info, pad_table

	#set default values
	data_cpu = [0, 0, 0]
	data_mem = [0, 0, 0]
	data_info = ["", "", "", ""]
	data_activity = []
	data_jobs = []
	data_waits = []
	data_changes = []
	current_tab = ord("0")
	data_cpu_changed = True
	data_mem_changed = True
	data_info_changed = True
	data_activity_changed = False
	data_jobs_changed = False
	data_waits_changed = False
	data_changes_changed = False
	init_complete = False

	#init screen
	stdscr.clear()
	stdscr.refresh()
	
	#hide cursor
	curses.curs_set(0)
	
	#get screen size
	height, width = stdscr.getmaxyx()
	middle = int(width // 2)
	quarter = int(width // 4)

	#define colours
	curses.start_color()
	curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_RED)

	#draw content	
	stdscr.insstr(height-2, 1, "Press 'q' to exit")
	stdscr.insstr(height-2, width-14, "sqlmedic.com")

	pad_cpu = curses.newpad(4, middle-1)
	pad_cpu.refresh(0,0, 1,1, 4,middle-1)

	pad_info = curses.newpad(4, middle-1)
	pad_info.refresh(0,0, 1,middle + 1, 4,width - 1)

	pad_table = curses.newpad(height - 9, width - 2)
	pad_table.refresh(0,0, 7,1, height-2, width-2)

	#initial data load
	data_cpu = get_cpu_data()
	data_mem = get_mem_data()
	data_info = get_info_data()


	#auto refrsh pads
	data_refresh = threading.Thread(target=thread_data_refresh, daemon=True)
	data_refresh.start()
	
	
	#get user inputs and switch displayed tabs
	key = ord("a")

	while (key != ord("q")):
		if key in [ord("a"), ord("j"), ord("w"), ord("c"), ord("q"), ord("r")]:

			if key in [ord("a"), ord("j"), ord("w"), ord("c")] and current_tab != key:
				current_tab = key

				draw_tabs(stdscr, "[A]ctivity", 6, 1, "a")			
				draw_tabs(stdscr, "Running [J]obs", 6, quarter, "j")
				draw_tabs(stdscr, "Top [W]aits", 6, middle, "w")
				draw_tabs(stdscr, "[C]hanges", 6, width - quarter, "c")

				stdscr.refresh()

				draw_pads()

		key = stdscr.getch()


def draw_tabs(stdscr, text, rows, cols, key):
	global current_tab
	if current_tab == ord(key):
		stdscr.attron(curses.color_pair(1))
	stdscr.addstr(rows, cols,  text)	
	if current_tab == ord(key):
		stdscr.attroff(curses.color_pair(1))


def thread_data_refresh():
	global data_cpu, data_mem, data_info, data_activity, data_jobs, data_waits, data_changes
	global data_cpu_changed, data_mem_changed, data_info_changed, data_activity_changed, data_jobs_changed, data_waits_changed, data_changes_changed
	while True:
		if init_complete:
			data_cpu_tmp = get_cpu_data()
			if data_cpu_tmp != data_cpu:
				data_cpu = data_cpu_tmp
				data_cpu_changed = True	

			data_mem_tmp = get_mem_data()
			if data_mem_tmp != data_mem: 
				data_mem = data_mem_tmp
				data_mem_changed = True

			data_info_tmp = get_info_data()
			if data_info_tmp != data_info: 
				data_info = data_info_tmp
				data_info_changed = True	

			if data_activity_changed or data_changes_changed or data_cpu_changed or data_info_changed or data_jobs_changed or data_mem_changed or data_waits_changed:	
				draw_pads()
		time.sleep(2)


def get_cpu_data():
	cursor = db_connection.cursor()
	cursor.execute("""
		select top 1
			dateadd(millisecond, -1 * ((
				select 
					cpu_ticks/(cpu_ticks/ms_ticks) 
				from sys.dm_os_sys_info
			) - [timestamp]), getdate()) as [Time],
			SystemIdle as [Idle],
			ProcessUtilization as [SQL],
			100 - SystemIdle - ProcessUtilization as Other

		from (

			select 	
				[timestamp],		
				record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int') as SystemIdle,
				record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') as ProcessUtilization		
			
			from 
				(
					select			
						[timestamp],
						convert(xml, record) AS [record]			 
					from sys.dm_os_ring_buffers
					where 
						ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
						and record like '%<SystemHealth>%'		
				) as x

		) as y

		order by [Time] desc

	""")
	row = cursor.fetchone()
	if row:
		return [row.SQL, row.Other, row.Idle]
	else:
		return [0, 0, 0]
		


def get_mem_data():
	cursor = db_connection.cursor()
	cursor.execute("""
		select
			(
				select 
					cast(physical_memory_kb/1024.0/1024.0 as int)
				from sys.dm_os_sys_info
			) as Physical
			, (
				select 
					cast(cast(value_in_use as bigint)/1024.0 as int)
				from sys.configurations
				where name = 'max server memory (MB)'
			) as Max
			, (
				select
					cast(cast(cntr_value as bigint)/1024.0/1024.0 as int)
				from sys.dm_os_performance_counters
				where counter_name = 'Target Server Memory (KB)'
			) as Target
			, (
				select
					cast(cast(cntr_value as bigint)/1024.0/1024.0 as int)
				from sys.dm_os_performance_counters
				where counter_name = 'Total Server Memory (KB)'
			) as Total
	""")
	row = cursor.fetchone()
	if row:
		physical = row.Physical
		if row.Max < physical:
			physical = row.Max

		return [(row.Total / physical) * 100, row.Target, physical]
	else:
		return [0, 0, 0]



def get_info_data():
	cursor = db_connection.cursor()
	cursor.execute("""
		declare @startDate datetime = (
			select sqlserver_start_time from sys.dm_os_sys_info
		)

		select
			upper(@@servername) as servername,
			'Microsoft SQL Server '
			+ case cast(serverproperty('ProductMajorVersion') as int) 
				when 14 then '2017'
				when 15 then '2019'
			end + ' (' 
			+ cast(serverproperty('ProductLevel') as varchar) + '-' 
			+ cast(serverproperty('ProductUpdateLevel') as varchar) + ') (' 
			+ cast(serverproperty('ProductUpdateReference') as varchar) + ') - ' 
			+ cast(serverproperty('ProductVersion') as varchar)
			as version,
			cast(serverproperty('Edition') as varchar) as edition,
			convert(varchar, datediff(hour, @startDate, getdate()) / 24) + ' days, ' 
			+ convert(varchar, datediff(hour, @startDate, getdate()) % 24) + ' hours & ' 
			+ convert(varchar, datediff(minute, @startDate, getdate()) % 60) + ' minutes' as uptime
	""")
	row = cursor.fetchone()
	if row:
		return [row.servername, row.version, row.edition, row.uptime]
	else:
		return ["", "", "", ""]


def draw_pads():
	global pad_cpu, pad_info, pad_table
	global data_cpu_changed, data_mem_changed, data_info_changed, data_activity_changed, data_jobs_changed, data_waits_changed, data_changes_changed
	global current_tab, height, width, middle, quarter, init_complete

	if data_cpu_changed or data_mem_changed:		
		pad_cpu.clear()
		draw_cpu()
		draw_mem()
		data_cpu_changed = False
		data_mem_changed = False
		pad_cpu.refresh(0,0, 1,1, 4,middle-1)

	if data_info_changed:
		data_info_changed = False
		pad_info.clear()
		draw_info()
		pad_info.refresh(0,0, 1,middle + 1, 4,width - 1)

	refresh_table = False

	if current_tab == ord("a") and data_activity_changed:
		data_activity_changed = False
		refresh_table = True
	elif current_tab == ord("j") and data_jobs_changed:
		data_jobs_changed = False
		refresh_table = True
	elif current_tab == ord("w") and data_waits_changed:
		data_waits_changed = False
		refresh_table = True
	elif current_tab == ord("c") and data_changes_changed:
		data_changes_changed = False
		refresh_table = True

	if refresh_table:
		pad_table.clear()
		pad_table.box()
		if current_tab == ord("a"):
			draw_activity()
		elif current_tab == ord("j"):
			draw_jobs()
		elif current_tab == ord("w"):
			draw_waits()
		elif current_tab == ord("c"):
			draw_changes()
		pad_table.refresh(0,0, 7,1, height-2, width-2)


	init_complete = True



def draw_cpu():
	global pad_cpu, data_cpu, middle
	pad_cpu.insstr(0, 0, "SQL   [" + percent_string(data_cpu[0], middle-14))	
	#pad_cpu.insstr(1, 0, "Other [" + percent_string(data_cpu[1], middle-14))
	#pad_cpu.insstr(2, 0, "Idle  [" + percent_string(data_cpu[2], middle-14))	

	pad_cpu.insstr(0, middle - 6, str(data_cpu[0]).rjust(3, ' ') + "%]")	
	#pad_cpu.insstr(1, middle - 6, str(data_cpu[1]).rjust(3, ' ') + "%]")
	#pad_cpu.insstr(2, middle - 6, str(data_cpu[2]).rjust(3, ' ') + "%]")	

def draw_mem():
	global pad_cpu, data_mem, middle

	s = str(data_mem[1]) + "G/" + str(data_mem[2]) +  "G]"
	
	pad_cpu.insstr(1, 0, "Mem   [" + percent_string(data_mem[0], middle-(len(s) + 9)))
	pad_cpu.insstr(1, middle - (len(s) + 1), s)


def draw_info():
	global pad_info, data_info
	pad_info.insstr(0, 0, data_info[0])	
	pad_info.insstr(1, 0, data_info[1])
	pad_info.insstr(2, 0, data_info[2])	
	pad_info.insstr(3, 0, data_info[3])	

def draw_activity():
	global pad_table, data_activity
	pass

def draw_jobs():
	global pad_table, data_jobs
	pass

def draw_waits():
	global pad_table, data_waits
	pass

def draw_changes():
	global pad_table, data_changes
	pass


def percent_string(percent, cols):
	return "|" * int((cols * 1.0) * ((percent * 1.0) / 100.0))


def open_conn(instance, user, password):
	global db_connection
	db_connection = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'
		+'SERVER=tcp:' + instance
		+';DATABASE=master'
		+';UID=' + user
		+';PWD=' + password, autocommit=True)
	return db_connection
	
