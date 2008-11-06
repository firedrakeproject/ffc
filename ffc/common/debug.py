"""A common interface for diagnostic messages. Only messages with
debug level lower than or equal to the current debug level will be
printed. To see more messages, raise the debug level."""

__author__ = "Anders Logg (logg@simula.no)"
__date__ = "2005-02-04 -- 2008-09-27"
__copyright__ = "Copyright (C) 2005-2008 Anders Logg"
__license__  = "GNU GPL version 3 or any later version"

import sys

from utils import *

__level = -1
__indent = 0
__continuation = False
__continuation_level = 0

def debug(string, debuglevel=0):
    "Print given string at given debug level"

    global __level, __indent, __continuation, __continuation_level

    # Set indentation
    indentation = 2*__indent

    # Print message (note fancy handling of strings containing ...)
    if debuglevel <= __level:
        if __continuation:
            if __continuation_level == debuglevel:
                print string
            else:
                print "\n" + indent(string, indentation)
            __continuation = False
        elif "..." in string:
            print indent(string, indentation),
            __continuation = True
            __continuation_level = debuglevel
        else:
            print indent(string, indentation)

    # Flush buffer so messages are printed *now*
    sys.stdout.flush()

def debug_indent(increment=1):
    "Set indentation of debug messages"
    global __indent
    __indent += increment

def debug_begin(string):
    "Begin task"
    debug(string)
    debug("".join(["-" for i in range(len(string))]))
    debug("")
    debug_indent()

def debug_end():
    "End task"
    debug("")
    debug_indent(-1)

def setlevel(newlevel):
    "Set debug level"
    global __level
    __level = newlevel

def getlevel():
    "Get debug level"
    return __level

def warning(string, debuglevel=-1):
    "Print a warning"
    debug("Warning: " + string, debuglevel)

def error(string, debuglevel=-1):
    "Print an error"
    debug("*** Error: " + string, debuglevel)