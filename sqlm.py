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
@click.option('-S', '--server', default=".")
@click.option('-U', '--user', default="sa")
@click.option('-P', '--password', prompt=True, hide_input=True,
			  confirmation_prompt=False)
def cli(server:str, user:str, password:str):
	conn_test_result = test_connection(server, user, password)
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
	data_activity_changed = True
	data_jobs_changed = True
	data_waits_changed = True
	data_changes_changed = True
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


	#auto refresh data displayed
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

			data_activity_tmp = get_activity_data()
			if data_activity_tmp != data_activity:
				data_activity = data_activity_tmp
				data_activity_changed = True

			data_jobs_tmp = get_jobs_data()
			if data_jobs_tmp != data_jobs:
				data_jobs = data_jobs_tmp
				data_jobs_changed = True

			data_waits_tmp = get_waits_data()
			if data_waits_tmp != data_waits:
				data_waits = data_waits_tmp
				data_waits_changed = True

			data_changes_tmp = get_changes_data()
			if data_changes_tmp != data_changes:
				data_changes = data_changes_tmp
				data_changes_changed = True	

			if (data_activity_changed 
					or data_changes_changed 
					or data_cpu_changed 
					or data_info_changed 
					or data_jobs_changed 
					or data_mem_changed 
					or data_waits_changed):	
				draw_pads()
		time.sleep(2)

def get_activity_data():
	cursor = db_connection.cursor()
	cursor.execute("""
		select
			r.session_id as spid
			,r.blocking_session_id as blocked_by
			,r.status
			,isnull(cast(object_name(t.objectid, t.dbid) as varchar(1000)), i.event_info) as object_name	
			,db_name(r.database_id) as [db]	
			,convert(decimal(26,2), r.cpu_time / 1000.0) as cpu_time
			,convert(decimal(26,2), r.total_elapsed_time / 1000.0) as total_time
			,(r.reads * 8) / 1000 as reads_mb
			,(r.writes * 8) / 1000 as writes_mb
			,cast((r.logical_reads * 8) / 1000000.0 as decimal(26,2)) as logical_reads_gb
			,r.row_count as [rows]
			,(r.granted_query_memory * 8) /1000 as memory_mb
			,r.open_transaction_count as open_tran
			,s.program_name as program	
			,isnull(nullif(s.login_name, ''), s.original_login_name) as login
			,s.host_name

		from
			sys.dm_exec_requests as r

			inner join sys.dm_exec_sessions as s
			on s.session_id = r.session_id
				and s.is_user_process = 1
			
			cross apply sys.dm_exec_sql_text(r.sql_handle) as t

			cross apply sys.dm_exec_input_buffer(s.session_id, r.request_id) as i
			
		where 
			r.session_id <> @@spid
			and s.program_name not like 'SQLAgent - TSQL JobStep (Job % : Step %)' 
			and r.cpu_time > 0

		order by
			r.total_elapsed_time desc
	""")
	rows = cursor.fetchall()
	if rows:
		return [0]
	else:
		return [0]

def get_jobs_data():
	cursor = db_connection.cursor()
	cursor.execute("""
		select
			r.session_id as spid
			,r.blocking_session_id as blocked_by
			,r.status
			,isnull(cast(object_name(t.objectid, t.dbid) as varchar(1000)), i.event_info) as object_name	
			,db_name(r.database_id) as [db]	
			,convert(decimal(26,2), r.cpu_time / 1000.0) as cpu_time
			,convert(decimal(26,2), r.total_elapsed_time / 1000.0) as total_time
			,(r.reads * 8) / 1000 as reads_mb
			,(r.writes * 8) / 1000 as writes_mb
			,cast((r.logical_reads * 8) / 1000000.0 as decimal(26,2)) as logical_reads_gb
			,r.row_count as [rows]
			,(r.granted_query_memory * 8) /1000 as memory_mb
			,r.open_transaction_count as open_tran
			,j.name as program	
			,isnull(nullif(s.login_name, ''), s.original_login_name) as login
			,s.host_name			

		from
			sys.dm_exec_requests as r

			inner join sys.dm_exec_sessions as s
			on s.session_id = r.session_id
				and s.is_user_process = 1
			
			cross apply sys.dm_exec_sql_text(r.sql_handle) as t

			cross apply sys.dm_exec_input_buffer(s.session_id, r.request_id) as i

			inner join msdb..sysjobs as j
			on j.job_id = case when s.program_name like 'SQLAgent - TSQL JobStep (Job % : Step %)' then cast(Convert(binary(16), substring(s.program_name, 30, 34), 1) as uniqueidentifier) else null end
						
				
		where 
			r.session_id <> @@spid
			and r.cpu_time > 0

		order by
			r.total_elapsed_time desc
	""")
	rows = cursor.fetchall()
	if rows:
		return [0]
	else:
		return [0]


def get_waits_data():
	cursor = db_connection.cursor()
	cursor.execute("""
		select 
			wait_type
			, waiting_tasks_count
			, wait_time_ms
			, max_wait_time_ms
			, signal_wait_time_ms
		from sys.dm_os_wait_stats
		where	
			waiting_tasks_count != 0
			or wait_time_ms != 0
			or max_wait_time_ms != 0
			or signal_wait_time_ms != 0
		order by 
			wait_time_ms desc
	""")
	rows = cursor.fetchall()
	if rows:
		return [0]
	else:
		return [0]

def get_changes_data():
	cursor = db_connection.cursor()
	cursor.execute("""
		create table #changes (
			[Database] varchar(250),
			[Object] varchar(250),
			[Type] varchar(250),
			[Created] datetime,
			[Modified] datetime
		)

		exec sp_msforeachdb '

		if ''?'' not in (''tempdb'', ''msdb'', ''master'', ''model'')
		begin

			insert into #changes ([Database],[Object],[Type],[Created],[Modified])
			select 
				''?'' as [Database],
				name as [Object], 
				type_desc as [Type],
				create_date as [Created],
				nullif(modify_date, create_date) as [Modified]
				
			from [?].sys.objects
			where
				is_ms_shipped = 0
				and (
					create_date > dateadd(day, -30, getdate())
					or modify_date > dateadd(day, -30, getdate())
				)
				
			order by
				name	
				
		end
			
		'

		select * from #changes
		order by
			[Database],
			[Object]
			
		drop table #changes
	""")
	row = cursor.fetchone()
	if row:
		return [0]
	else:
		return [0]


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
	pad_cpu.insstr(0, middle - 6, str(data_cpu[0]).rjust(3, ' ') + "%]")	

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
	pad_table.insstr(0, 0, "activity")
	pass

def draw_jobs():
	global pad_table, data_jobs
	pad_table.insstr(0, 0, "jobs")
	pass

def draw_waits():
	global pad_table, data_waits
	pad_table.insstr(0, 0, "waits")
	pass

def draw_changes():
	global pad_table, data_changes
	pad_table.insstr(0, 0, "changes")
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
	
