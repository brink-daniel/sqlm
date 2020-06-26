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


#main entry point
@click.command()
@click.option('--instance', default=".")
@click.option('--user', default="sa")
@click.option('--password', prompt=True, hide_input=True,
			  confirmation_prompt=False)
def cli(instance:str, user:str, password:str):
	"""
	Diagnostics tool for ms sql server
	"""
	conn_test_result = test_connection(instance, user, password)
	if conn_test_result == "Success":
		curses.wrapper(draw_screen)
	else:
		click.echo(conn_test_result)


def test_connection(instance:str, user:str, password:str):
	return "Success"


def draw_screen(stdscr):
	global current_tab, height, width, middle, quarter, init_complete
	global data_cpu, data_mem, data_info, data_activity, data_jobs, data_waits, data_changes
	global data_cpu_changed, data_mem_changed, data_info_changed, data_activity_changed, data_jobs_changed, data_waits_changed, data_changes_changed
	global pad_cpu, pad_info, pad_table

	#set default values
	data_cpu = [0, 0, 0]
	data_mem = [0, 0, 0]
	data_info = ["Line 1", "Line 2", "Line 3", "Line 4"]
	data_activity = []
	data_jobs = []
	data_waits = []
	data_changes = []
	current_tab = ord("0")
	data_cpu_changed = False
	data_mem_changed = False
	data_info_changed = False
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
	pad_cpu.box()
	pad_cpu.refresh(0,0, 1,1, 4,middle-1)

	pad_info = curses.newpad(4, middle-1)
	pad_info.box()
	pad_info.refresh(0,0, 1,middle + 1, 4,width - 1)

	pad_table = curses.newpad(height - 9, width - 2)
	pad_table.box()
	pad_table.refresh(0,0, 7,1, height-2, width-2)

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
			data_cpu = [random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)]	
			data_cpu_changed = True	
			draw_pads()
		time.sleep(5)

def draw_pads():
	global pad_cpu, pad_info, pad_table
	global data_cpu_changed, data_mem_changed, data_info_changed, data_activity_changed, data_jobs_changed, data_waits_changed, data_changes_changed
	global current_tab, height, width, middle, quarter, init_complete

	if data_cpu_changed or data_mem_changed:		
		pad_cpu.clear()
		if data_cpu_changed:
			draw_cpu()
		if data_mem_changed:
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
	pad_cpu.insstr(1, 0, "Other [" + percent_string(data_cpu[1], middle-14))
	pad_cpu.insstr(2, 0, "Idle  [" + percent_string(data_cpu[2], middle-14))	

	pad_cpu.insstr(0, middle - 6, str(data_cpu[0]).rjust(3, ' ') + "%]")	
	pad_cpu.insstr(1, middle - 6, str(data_cpu[1]).rjust(3, ' ') + "%]")
	pad_cpu.insstr(2, middle - 6, str(data_cpu[2]).rjust(3, ' ') + "%]")	

def draw_mem():
	global pad_cpu, data_mem, middle

	offset = 0
	if data_mem[1] >= 1000 or data_mem[2] >= 1000:
		offset = 6
	elif data_mem[1] >= 100 or data_mem[2] >= 100:
		offset = 4
	elif data_mem[1] >= 10 or data_mem[2] >= 10:
		offset = 2
	
	pad_cpu.insstr(3, 0, "Mem   [" + percent_string(data_mem[0], middle-(15 + offset)))
	pad_cpu.insstr(3, middle - (7 + offset), (str(data_mem[1]) + "G/" + str(data_mem[2]) +  "G]"))


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
