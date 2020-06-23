import click
import curses
import pyodbc
import datetime
import threading
import time


global pad_cpu, pad_info, pad_table
global current_tab


#main entry pointsqlm
@click.command()
@click.option('--instance', default=".")
@click.option('--user', default="sa")
@click.option('--password', prompt=True, hide_input=True,
			  confirmation_prompt=False)
def cli(instance:str, user:str, password:str):
	"""
	clone of htop for ms sql server
	"""
	conn_test_result = test_connection(instance, user, password)
	if conn_test_result == "Success":
		curses.wrapper(draw_window)
	else:
		click.echo(conn_test_result)


def test_connection(instance:str, user:str, password:str):
	return "Success"


def draw_window(stdscr):
	global current_tab
	current_tab = ord("0")

	#init screen
	stdscr.clear()
	
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
	
	
	#get user inputs and switch displayed tabs
	key = ord("a")

	while (key != ord("q")):
		if key in [ord("a"), ord("j"), ord("w"), ord("c"), ord("q"), ord("r")]:

			if key in [ord("a"), ord("j"), ord("w"), ord("c")] and current_tab != key:
				current_tab = key

				draw_tabs(stdscr, "[A]ctivity", 6, 1, current_tab, "a")			
				draw_tabs(stdscr, "Running [J]obs", 6, quarter, current_tab, "j")
				draw_tabs(stdscr, "Top [W]aits", 6, middle, current_tab, "w")
				draw_tabs(stdscr, "[C]hanges", 6, width - quarter, current_tab, "c")

				stdscr.refresh()

		key = stdscr.getch()


def draw_tabs(stdscr, text, rows, cols, input, key):
	if input == ord(key):
		stdscr.attron(curses.color_pair(1))
	stdscr.addstr(rows, cols,  text)	
	if input == ord(key):
		stdscr.attroff(curses.color_pair(1))