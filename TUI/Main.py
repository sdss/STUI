#!/usr/bin/env python
"""Telescope User Interface.
This is the main routine that calls everything else.

2003-02-27 ROwen    First version with history.
                    Modified to use the new Hub authorization
2003-03-20 ROwen    Added DIS
2003-03-25 ROwen    Moved TCC widgets into TCC subdirectory;
    modified to load TUI windows from TUIWindow.py
    and to auto-load windows from TCC, Inst and Misc directories
2003-04-04 ROwen    Fixed auto-load code to be platform-independent.
2003-04-22 ROwen    Modified to not auto-load window modules
                    whose file name begins with ".".
2003-06-09 ROwen    Modified to use TUIModel.
2003-06-18 ROwen    Modified to print a full traceback for unexpected errors;
                    modified to exclude SystemExit and KeyboardInterrupt
                    when testing for general exceptions.
2003-12-17 ROwen    Modified to auto load windows from all of the
                    TCC package (instead of specific sub-packages)
                    and also from TUISharedAdditions and TUIUserAdditions.
2004-01-23 ROwen    Modified to not rely on modules being loaded from the
                    same dir as this file. This simplifies generating a
                    Mac standalone app.
                    Modified to load *all* windows in TUI,
                    rather than searching specific directories.
                    Improved error handling of loadWindows:
                    - if TUI cannot be loaded, fail
                    - reject module names with "." in them
                    (both changes help debug problems with making
                    standalone apps).
2004-02-05 ROwen    Changed the algorithm for finding user additions.
2004-02-06 ROwen    Adapted to RO.OS.walkDirs->RO.OS.findFiles.
2004-02-17 ROwen    Changed to call buildMenus instead of buildAutoMenus
                    in the "None.Status" toplevel. .
2004-03-03 ROwen    Modified to print the version number during startup.
2004-03-09 ROwen    Bug fix: unix code was broken.
2004-05-17 ROwen    Modified to be runnable by an external script (e.g. runtui.py).
                    Modified to print version to log rather than stdout.
2004-07-09 ROwen    Modified to use TUI.TUIPaths
2004-10-06 ROwen    Modified to use TUI.MenuBar.
2005-06-16 ROwen    Modified to use improved KeyDispatcher.logMsg.
2005-07-22 ROwen    Modified to hide tk's console window if present.
2005-08-01 ROwen    Modified to use TUI.LoadStdModules, a step towards
                    allowing TUI code to be run from a zip file.
2005-08-08 ROwen    Moved loadWindows and findWindowsModules to WindowModuleUtil.py
2005-09-22 ROwen    Modified to use TUI.TUIPaths.getAddPaths instead of getTUIPaths.
2006-10-25 ROwen    Modified to not send dispatcher to BackgroundTasks.
2007-01-22 ROwen    Modified to make sure sys.executable is absolute,
                    as required for use with pyinstaller 1.3.
2007-12-20 ROwen    Import and configure matplotlib here and stop configuring it elsewhere. This works around
                    a problem in matplotlib 0.91.1: "use" can't be called after "import matplotlib.backends".
2009-08-06 ROwen    Stopped setting matplotlib numerix parameter; it is obsolete as of matplotlib 0.99.0.
2009-11-05 ROwen    Fix matplotlib warning by calling use before loading any TUI modules.
2010-03-12 ROwen    Changed to use Models.getModel.
2010-05-05 ROwen    Configure twisted.internet to use Tk right away. Formerly that was done in the TUI model,
                    but by then various parts of twisted were imported so this seems safer.
2010-05-10 ROwen    Fix ticket #825: main tk window visible (broken in the 2010-05-05 changes).
2010-05-21 ROwen    Undo the changes of 2010-05-05 and 2010-05-10 since it broke test code.
2010-11-17 ROwen    Suppress numpy division warnings.
2010-11-18 ROwen    Disabled all numpy warnings to suppress "Warning: invalid value encountered in divide"
                    (simply disabling divide warnings did not do it).
2012-07-18 ROwen    Modified to use RO 3.0 and optionally communicate using Twisted framework.
2013-07-19 ROwen    Modified to print some info to stdout (e.g. the log) on startup.
                    Modified to only show the version name, not version date, in the log at startup.
2013-09-04 ROwen    Use application name instead of TUI in several places.
2014-02-12 ROwen    Added a call to reopen script windows.
"""
import os
import sys
import time
import Tkinter
import numpy

numpy.seterr(all="ignore") # suppress "Warning: invalid value encountered in divide"
import matplotlib
matplotlib.use("Agg")
# controls the background of the axis label regions (which default to gray)
matplotlib.rc("figure", facecolor="white")
matplotlib.rc("axes", titlesize="medium") # default is large, which is too big
matplotlib.rc("legend", fontsize="medium") # default is large, which is too big

import RO.Comm.Generic
RO.Comm.Generic.setFramework("tk")

import TUI.Base.ScriptLoader
import TUI.BackgroundTasks
import TUI.LoadStdModules
import TUI.MenuBar
import TUI.TUIPaths
import TUI.Models
from TUI.Models.TUIModel import getPlatform
import TUI.WindowModuleUtil
import TUI.Version
from TUI.Actorkeys import getActorkeysPath, refreshActorkeys, getSTUIPath

# hack for pyinstaller 1.3
sys.executable = os.path.abspath(sys.executable)

def runTUI():
    """Run TUI.
    """
    # Hide the Tk root; must do this before setting up preferences (which is done by the tui model).
    tkRoot = Tkinter.Tk()
    tkRoot.withdraw()
    # if console exists, hide it
    try:
        tkRoot.tk.call("console", "hide")
    except Tkinter.TclError:
        pass

    # Update location of actorkeys. We respect any $PYTHONPATH already existing and
    # append the downloaded actorkeys to it. Worst case, will revert to the internal
    # bundled copy.
    actorkeys_path = getActorkeysPath()
    try:
        if not os.path.exists(actorkeys_path):
            sys.stdout.write('Downloading actorkeys ... ')
            refreshActorkeys()
    except Exception as ee:
        sys.stdout.write('Failed downloading actorkeys %s' % str(ee))
    else:
        sys.path.insert(0, getSTUIPath())

    # create and obtain the TUI model
    tuiModel = TUI.Models.getModel("tui")

    # set up background tasks
    backgroundHandler = TUI.BackgroundTasks.BackgroundKwds()

    # get locations to look for windows
    addPathList = TUI.TUIPaths.getAddPaths()

    # add additional paths to sys.path
    sys.path += addPathList

    TUI.LoadStdModules.loadAll()

    # load additional windows modules
    for winPath in addPathList:
        TUI.WindowModuleUtil.loadWindows(
            path = winPath,
            tlSet = tuiModel.tlSet,
            logFunc = tuiModel.logMsg,
        )

    # load scripts
    TUI.Base.ScriptLoader.reopenScriptWindows()

    # add the main menu
    TUI.MenuBar.MenuBar()

    tuiModel.logMsg(
        "%s %s: ready to connect" % (TUI.Version.ApplicationName, TUI.Version.VersionName)
    )
    startTimeStr = time.strftime("%Y-%m-%dT%H:%M:%S")
    platformStr = getPlatform()
    sys.stdout.write("%s %s running on %s started %s\n" % \
        (TUI.Version.ApplicationName, TUI.Version.VersionName, platformStr, startTimeStr))

    tuiModel.reactor.run()

if __name__ == "__main__":
    runTUI()
