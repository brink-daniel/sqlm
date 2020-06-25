import click
import curses
import pyodbc
import datetime
import threading
import time


#curses pads
global pad_cpu, pad_info, pad_table

#general
global current_tab, height, width, middle, quarter

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
	global current_tab, height, width, middle, quarter
	global data_cpu, data_mem, data_info, data_activity, data_jobs, data_waits, data_changes
	global data_cpu_changed, data_mem_changed, data_info_changed, data_activity_changed, data_jobs_changed, data_waits_changed, data_changes_changed
	global pad_cpu, pad_info, pad_table

	#set default values
	data_cpu = [0, 0, 0]
	data_mem = [0, 0, 0]
	data_info = []
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
	stdscr.addstr(height-2, 1, "Press 'q' to exit")
	stdscr.addstr(height-2, width-14, "sqlmedic.com")

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
	pads = threading.Thread(target=thread_draw_pads, daemon=True)
	pads.start()
	
	
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


def thread_draw_pads():
	while True:
		draw_pads()
		time.sleep(5)

def draw_pads():
	global pad_cpu, pad_info, pad_table
	global data_cpu_changed, data_mem_changed, data_info_changed, data_activity_changed, data_jobs_changed, data_waits_changed, data_changes_changed
	global current_tab, height, width, middle, quarter

	if data_cpu_changed or data_mem_changed:
		data_cpu_changed = False
		data_mem_changed = False
		pad_cpu.clear()
		pad_cpu.box()
		pad_cpu.refresh(0,0, 1,1, 4,middle-1)

	if data_info_changed:
		data_info_changed = False
		pad_info.clear()
		pad_info.box()
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
		pad_table.refresh(0,0, 7,1, height-2, width-2)
