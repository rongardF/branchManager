import tkinter as tk
import tkinter.ttk as ttk
import sys, os, traceback, git, re, threading, subprocess

from ignore_setups import ignore_setups
from tkinter import messagebox, StringVar, Toplevel, simpledialog
from subprocess import Popen, CREATE_NEW_CONSOLE
from configparser import ConfigParser

class SettingsHandler(): # TODO: add docstrings to this class and methods
    """
    Read, write and verify settings for the application
    
    Provides a handler for reading and writing settings data
    from settings.ini file. Instance attributes are acessed directly
    using properties. Class instance is iterable to read and write
    settings in a loop.
    """
    def __init__(self):
        # retrieve settings from file and check that they are valid, if not valid then set them to None
        self._settings_file=os.path.join(sys.path[0],'settings.ini')
        self._attr_list=["repo_path", "wsl_path", "sftp_path", "timeout"]
        self.settings = ConfigParser()
        self.settings.read(self._settings_file) # settings file is always in the same folder as the main script
    
    def __iter__(self):
        self.index=0 # reset the iteration index
        return self
    
    def __next__(self):
        if self.index > 3:
            raise StopIteration
        else:
            index=self.index
            self.index=self.index+1
            return self._attr_list[index], getattr(self, self._attr_list[index]) # return attribute using properties
        
    @property
    def repo_path(self):
        repo_path=self.settings.get('main','repo_path')
        # check that path actually exists
        if os.path.exists(repo_path) is False:
            return '' # in case this path does not exist in this machine then return empty string
        else:
            return repo_path 
    
    @repo_path.setter
    def repo_path(self, path):
        if os.path.exists(path) is False:
            raise ValueError("Specified repository path does not exist")
        else:
            self.settings.set("main","repo_path",path)
            self._write_to_file()
    
    @property
    def wsl_path(self):
        wsl_path=self.settings.get('main','wsl_app_path')
        # check that path actually exists
        if os.path.exists(wsl_path[:-2]) is False: # remove tilde from the end of returned path string
            return '' # in case this path does not exist in this machine then return empty string
        else:
            return wsl_path[:-2]
    
    @wsl_path.setter
    def wsl_path(self, path):
        if os.path.exists(path) is False:
            raise ValueError("Specified WSL path does not exist")
        else:
            self.settings.set("main","wsl_app_path",path+" ~") # append tilde so WSL would open up in home directory
            self._write_to_file()
            
    @property
    def sftp_path(self):
        sftp_path=self.settings.get('main','sftp_path')
        # check that path actually exists
        if os.path.exists(sftp_path.split(',')[1]) is False: # remove explorer command from the start of string
            return '' # in case this path does not exist in this machine then return empty string
        else:
            return sftp_path.split(',')[1]
    
    @sftp_path.setter
    def sftp_path(self, path):
        if os.path.exists(path) is False:
            raise ValueError("Specified SFTP path does not exist")
        else:
            self.settings.set("main","sftp_path","explorer.exe /e,"+path) # prefix path with command to open up file explorer
            self._write_to_file()
    
    @property
    def timeout(self):
        return self.settings.getint('main','timeout')
    
    @timeout.setter
    def timeout(self, timeout):
        if isinstance(timeout, int) is False:
            raise ValueError("Input timeout value must be integer")
        self.settings.set("main","timeout",str(timeout))
        self._write_to_file()
    
    def _write_to_file(self):
        with open(self._settings_file, 'w') as f:
            self.settings.write(f)

class GitGui(tk.Tk):
    '''
    Create a GUI for MCP manager
    
    Creates an object which creates GUI window with labels and buttons.
    Starts running git_manager instance and provides callback functions for
    it. Manages the GUI.
    
    Methods
    -------
    update_setups_list(setups_list)
        Callback function to be provided for git_manager to call when new 
        test setups (branches) are detected
    error_print(err_str)
        Callback function to be provided for git_manager to call when an
        exception is encountered while running git_manager thread.
    setup_loaded(setup_name)
        Callback function to be provided for git_manager to call when
        git_manager finishes loading new setup(branch)
    '''

    def __init__(self, git_man, run_event, settings_ref): 
        """
        Parameters
        ----------
        git_man : git_manager
            Instance of git_manager providing backend
        run_event : threading.Event
            Event that signals when the application should shut down
        """
        tk.Tk.__init__(self)
        self._run_event=run_event
        self._git_man=git_man
        self._settings=settings_ref
        self._wsl_path=self._settings.wsl_path
        self._sftp_path=self._settings.sftp_path
               
        self._setups_list=[]
        self._active_setup=""
        
        self.protocol("WM_DELETE_WINDOW", self._closed_std)
        self.title("MCP manager")
        self.resizable(False, False) # window size cannot be changed
        #self.iconbitmap(default=os.path.join(sys.path[0],"icons/mcp_icon.ico")) # look into same folder where the script is located        print("icon set")
        self._frame=tk.Frame(master=self, width=400, height=160)
        
        self._var_selected_setup=StringVar(master=self._frame)
        self._var_selected_setup.set(self._active_setup) # set the first setup as default setup
        self._var_active_setup=StringVar(master=self._frame)
        self._var_active_setup.set(self._active_setup)
        
        self._label_setup_list_title=tk.Label(master=self._frame, text="SELECT SETUP", font=('Segoe UI', 10, 'bold'))
        self._label_setup_list_title.place(x=20,y=20)
        self._list_selected_setup=ttk.Combobox(master=self._frame, textvariable=self._var_selected_setup, values=self._setups_list, width=30, state='disabled')
        self._list_selected_setup.place(x=20,y=45)
        
        self._label_active_setup_title=tk.Label(master=self._frame, text="ACTIVE SETUP", font=('Segoe UI', 10, 'bold'))
        self._label_active_setup_title.place(x=20,y=75)
        self._label_active_setup=tk.Label(master=self._frame, textvariable=self._var_active_setup, font=('Segoe UI', 10), width=28, anchor="w") # it is empty when initialized
        self._label_active_setup.place(x=20,y=100)
        
        self._button_load_setup=tk.Button(master=self._frame, text="Load setup", width=16, command=self._load_setup)
        self._button_load_setup["state"]="disabled"
        self._button_load_setup.place(x=260, y=27)
        self._button_open_wsl=tk.Button(master=self._frame, text="Open WSL", width=16, command=self._open_wsl)
        self._button_open_wsl.place(x=260, y=67)
        self._button_open_sftp=tk.Button(master=self._frame, text="Open SFTP folder", width=16, command=self._open_sftp)
        self._button_open_sftp.place(x=260, y=107)
        
        # create a menubar with sub-menus
        self._menubar = tk.Menu(master=self)
        self.config(menu=self._menubar)
        self._filemenu = tk.Menu(self._menubar, tearoff=0)
        
        self._filemenu.add_command(label="Set Git polling period", command=self._set_poll_period)
        self._path_menu=tk.Menu(self._filemenu, tearoff=0)
        self._path_menu.add_command(label="Set repository path", command=self._set_repo_path)
        self._path_menu.add_command(label="Set WSL path", command=self._set_wsl_path)
        self._path_menu.add_command(label="Set SFTP folder path", command=self._set_sftp_path)
        
        self._filemenu.add_cascade(label="Set paths", menu=self._path_menu)
        self._menubar.add_cascade(label="Settings", menu=self._filemenu, underline=0)
        
        #self.pack()
        self._frame.pack()
        self._git_man.start_updating(self.update_setups_list, self.error_print)
        
    def _closed_std(self):
        # This method is called by tkinter internal functions when a shutdown is started (pressing X)
        self._run_event.set()
        self.destroy()
        
    def _closed_err(self):
        # This method is called by tkinter internal functions when a shutdown is started by error handler
        self._run_event.set()
        self.quit()
    
    def _set_repo_path(self):
        # method to set a new repository path
        while True:
            try:
                path=simpledialog.askstring("Repository path", "Please specify path to the repository on local machine") 
                if path is None: # user aborted
                    return
                self._settings.repo_path=path
            except ValueError: # input invalid, continue asking until user specifies correct input
                messagebox.showerror(title=None,message="Specified path is not valid!")
                continue
            
            break # if input valid then break 
        
        # change the repo_path in git_manager instance as well - probably need to restart that insatnce or smth??
        self._git_man.update_repo_path(path)
        
    
    def _set_wsl_path(self):
        # method to set a new path pointing to WSL application
        while True:
            try:
                path=simpledialog.askstring("WSL application path", "Please specify path to the WSL executable on local machine") 
                if path is None: # user aborted
                    return
                self._settings.wsl_path=path
                self._wsl_path=path
            except ValueError: # input invalid, continue asking until user specifies correct input
                messagebox.showerror(title=None,message="Specified path is not valid!")
                continue
            
            break # if input valid then break 
    
    def _set_sftp_path(self):
        # method to set a new path to SFTP root folder
        while True:
            try:
                path=simpledialog.askstring("SFTP root path", "Please specify path to the SFTP root folder on local machine") 
                if path is None: # user aborted
                    return
                self._settings.sftp_path=path
                self._sftp_path=path
            except ValueError: # input invalid, continue asking until user specifies correct input
                messagebox.showerror(title=None,message="Specified path is not valid!")
                continue
            
            break # if input valid then break
    
    def _set_poll_period(self):
        # method to set new polling period
        timeout=int(simpledialog.askstring("Git polling period", "Please specify the interval for polling for new setups from Git server")) 
        if timeout is None: # user aborted
                    return
        elif timeout < 10: # TODO: throw error window showing timeout limits to user
            timeout = 0
        self._settings.timeout=timeout
        
        # change the timeout value in git_manager instance
        self._git_man.update_timeout(timeout)
            
    def update_setups_list(self, setups_list):
        """
        Callback to call when new test setups (branches) are detected
        
        This callback method must be provided to git_manager instance
        which will call it whenever new branches (test setups) are 
        found on the server. This method will update widgets in GUI
        accordingly to show new available test setups.
        
        Parameters
        ----------
        setups_list : dict
            dictionary containing available test setups with index 
            number as a key
        """
        list_of_setups=list(setups_list.values()) # convert dictionary into list
        
        if self._var_selected_setup.get() not in list_of_setups: # if currently selected setup is not in the new list of setups
            new_selected_setup=list_of_setups[0] # then it does not exist anymore, change selection to first setup in the list - actual change will be doen in the end
        else:
            new_selected_setup=self._var_selected_setup.get()
            
        if not self._var_active_setup.get(): # if empty string then starting up, load the currently selected branch
            new_selected_setup=self._git_man.get_active_setup()
        
        if self._var_active_setup.get() not in list_of_setups: # if currently active setup is not in the new list of setups
            self._load_setup(new_selected_setup) # then switch to another setup (the one currently selected)
        
        self._list_selected_setup['values']=list_of_setups 
        
    def error_print(self, err_str):
        """
        Callback to call when exception is raised
        
        This callback method must be provided to git_manager instance
        which will call it whenever there is an exception raised while
        executing the thread run method. This method creates a pop-up
        window which displays the exception message for the user.
        
        Parameters
        ----------
        err_str : str
            string containing traceback of the exception
        """
        messagebox.showerror(title="Exception raised",message=err_str)
        self._closed_err()
    
    def _load_setup(self, new_setup=None):
        # Internal method that is called when a new test setup (branch) needs
        # to be loaded
        if new_setup is None:
            selected_setup=self._var_selected_setup.get()
        else:
            selected_setup=new_setup
        self._button_load_setup["state"]="disabled"
        self._list_selected_setup["state"]="disabled"
        threading.Thread(target=self._git_man.load_setup, args=(selected_setup, self.setup_loaded)).start() # this implemented in a thread with callback function
    
    def setup_loaded(self, setup_name):
        """
        Callback function when new setup is loaded
        
        This callback method must be provided to git_manager instance
        when calling load_setup method. This callback will be called
        once the git_manager finishes loading that setup and it is
        ready to use.
        
        Parameters
        ----------
        setup_name : str
            string containing the steup name that was loaded
        """
        self._var_active_setup.set(setup_name)
        self._var_selected_setup.set(setup_name)
        self._button_load_setup["state"]="normal"
        self._list_selected_setup["state"]="readonly"
    
    def _open_wsl(self):
        # Internal method to open up a WSL terminal
        Popen(self._wsl_path+r' ~', creationflags=CREATE_NEW_CONSOLE) # TODO: attribute retrieval should already contain the required commands
        
    def _open_sftp(self):
        # Internal method to open up FIle Explorer with SFTP folder path
        Popen(r"explorer.exe /e,"+self._sftp_path, creationflags=CREATE_NEW_CONSOLE) # TODO: attribute retrieval should already contain the required commands


class GitManager(threading.Thread):
    """
    Backend to manage git repositories
    
    Manage git repositories on local machine. Tasks include retrieving
    information about new branches in git server, pulling any changes
    for existing branches and providing method for switching between 
    branches. Instance of this class will run a thread that 
    periodically checks for new branches on the git server and pull
    any changes for the existing branches.
    
    Methods
    -------
    get_active_setup()
        Return the branch name which is currently checked out
    load_setup(setup_name, callback_func=None, lock_aquired=False)
        Switch to new branch
    start_updating(callback, err_callback)(setup_name)
        Setup callback functions and start git manager thread
    """
    
    def __init__(self, run_flag, settings_ref):
        """
        Parameters
        ----------
        repo_path : str
            specify the path to the local git repository
        run_flag : threading.Event
            event flag to signal when user has closed GUI
        timeout : int
            time to wait between retrieving new information from git 
            server
        """
        self._settings=settings_ref
        self._timeout=self._settings.timeout 
        self._repo_path=self._settings.repo_path
        os.chdir(self._repo_path) # switch to directory where the repository is located
        self._repo=git.Repo(self._repo_path)
        self._run_flag=run_flag
        self._setups={}
        self._lock=threading.Lock()
        threading.Thread.__init__(self)
        
    def run(self):
        # internal function for threading - this will be run when start() method is called
        while not self._run_flag.is_set(): # while GUI has not been closed
            try:
                self._lock.acquire()
                self._prune_refs()
                new_setups=self._get_setups() # get the list of all branches/setups
                self._lock.release()
                if new_setups != self._setups:
                    self.callback(new_setups)
                    self._setups=new_setups
            except:
                err_str=traceback.format_exc()
                self.err_callback(err_str)
            self._run_flag.wait(self._timeout) # we can increase this value later
    
    def _prune_refs(self):
        # prune the origin repository of stale branches
        subprocess.run(["git", "remote", "prune", "origin"]) # TODO: use git directly with repo.git, ditch the subprocess use
    
    def _get_setups(self):
        # pull any new branches or changes to existing branches, 
        # returns a dictionary of all the branches filtered by
        # ignore_setups list
        try:
            self._repo.remotes.origin.pull()
        except git.exc.GitCommandError: # this will be raised when the branch has been deleted
            self.load_setup("main", None, True) # load main branch temporarely because we know this will never be deleted; we already have a lock and no callback func
        branches=self._repo.refs # get all available branches form GIT server
        setups={} # setups will be in dictionary with key being index in refs list and value being the setup name
        for branch in branches: # convert the ref objects into branch name strings
            if isinstance(branch, git.RemoteReference) and (str(branch) != "origin/HEAD"): # check if valid branch name (e.g. HEAD not valid)
                branch_name=str(branch).split("/")[-1] # get only the branch name
                if branch_name not in ignore_setups: # check if this branch we ignore
                    setups[branches.index(branch)]=branch_name
        
        # if we switched the main then now switch to first available branch not main
        if self.get_active_setup() == "main" or self.get_active_setup() == "master":
            self.load_setup(list(setups.values())[0], None, True) # load first existing setup/branch
        
        return setups   # there needs to be a check to see if any new branch available
    
    def get_active_setup(self):
        """
        Return the branch name which is currently checked out
        
        Returns
        -------
        str
            returns a string of currently checked out branch
        """
        return str(self._repo.head.reference)
    
    def load_setup(self, setup_name, callback_func=None, lock_aquired=False):
        """
        Switch to new branch
        
        Parameters
        ----------
        setup_name : str
            the name of the new branch
        callback_func : function, optional
            reference to the callback function to be called when 
            loading new branch finishes
        lock_aquired : boolean, optional
            indicate if the caller already has the lock or not
        """
        if lock_aquired is False: 
            self._lock.acquire()
        self._prune_refs()
        branches=self._repo.refs
        for branch in branches:
            branch_str=str(branch).split("/")[-1]
            if branch_str == setup_name:
                self._repo.git.checkout(branch_str)
                if callback_func is not None:
                    callback_func(setup_name) 
        
        if lock_aquired is False:
            self._lock.release()
    
    def update_repo_path(self, path):
        self._lock.acquire()
        self._repo_path=path
        os.chdir(self._repo_path) # switch to directory where the repository is located
        self._repo=git.Repo(self._repo_path)
        self._setups={}
        self._lock.release()
    
    def update_timeout(self, timeout):
        self._lock.acquire()
        self._timeout=timeout 
        self._lock.release()
      
    def start_updating(self, callback, err_callback):
        """
        Setup callback functions and start git manager thread
        
        Caller must provide two callback functions. First callback 
        function will be called when the list of branches in git 
        server has changed. The second callback will be called when 
        there is an exception raised while executing the threading loop
        
        Parameters
        ----------
        callback : function
            called when branches list changes
        err_callback : function
            called when exception is raised while executing
        """
        self.callback=callback
        self.err_callback=err_callback
        self.start()
        
def is_running(): # this function checks if there is an MCP manager app running already
    """
    Check if MCP manager instance ia already running
    
    Returns
    -------
    boolean
        True is running, False if not
    """
    output = subprocess.check_output(('TASKLIST', '/FI', 'WINDOWTITLE eq MCP manager'))
    if re.search("Console", str(output)):
        return True
    else:
        return False

if __name__ == "__main__":
    try:
        if is_running(): # if already running then don't open another app
            info_win=tk.Tk()
            info_win.withdraw()
            messagebox.showinfo(title=None,message="MCP manager already running!")
        else: 
            settings=SettingsHandler()
            input_win=tk.Tk() # root object in case we need to create input or error windows
            input_win.withdraw() # make it invisible
            input_win.iconbitmap(default=os.path.join(sys.path[0],"icons/mcp_icon.ico")) # all windows have the same MCP icon
            for setting, value in settings: # retrieve all settings and check they are valid
                while True:
                    try:
                        if (not value) and (setting == "repo_path"): # if setting value is unset then its an empty string
                            value=simpledialog.askstring("Repository path", "Please specify path to the repository on local machine")
                        elif (not value) and (setting == "wsl_path"):
                            value=simpledialog.askstring("WSL application path", "Please specify path to the WSL executable on local machine")
                        elif (not value) and (setting == "sftp_path"):
                            value=simpledialog.askstring("SFTP root path", "Please specify path to the SFTP root folder on local machine")

                        if value is None: # user pressed X or Cancelled
                            input_win.destroy()  
                            sys.exit()
                        setattr(settings, setting, value) # save the user provided input to settings file
                    except ValueError: # input invalid, continue asking until user specifies correct input
                        messagebox.showerror(title=None,message="Specified path is not valid!")
                        continue
                    
                    break # if input valid then break 
            input_win.destroy() # we will use MCP root window later if any messageboxes need to be created
            del input_win
                          
            run=threading.Event()
            git_man=GitManager(run, settings)
            git_gui=GitGui(git_man, run, settings)
            git_gui.mainloop() 
    except SystemExit:
        pass # just close application
    except:
        traceback.print_exc()
        input("PRESS ENTER TO CLOSE")
        