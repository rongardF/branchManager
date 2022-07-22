
import tkinter as tk
import tkinter.ttk as ttk
import sys, os, traceback, git, re, threading, subprocess

from ignore_setups import ignore_setups
from tkinter import messagebox, StringVar, Toplevel, Label
from subprocess import Popen, CREATE_NEW_CONSOLE

# define constants
repo_path=r'C:\Users\eonrrfe\OneDrive - Ericsson\Ron\Software development\Python\temp_files\testRepo'
wsl_app_path=r'C:\Windows\System32\wsl.exe ~'
sftp_path=r'explorer.exe /e,C:\Users'
timeout=10

class git_gui(tk.Tk):
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

    def __init__(self, git_man, run_event): 
        """
        Parameters
        ----------
        git_man : git_manager
            Instance of git_manager providing backend
        run_event : threading.Event
            Event that signals when the application should shut down
        """
        tk.Tk.__init__(self)
        self.__run_event=run_event
        self.__git_man=git_man
               
        self.__setups_list=[]
        self.__active_setup=""
        
        self.protocol("WM_DELETE_WINDOW", self.__closed)
        self.title("MCP manager")
        self.resizable(False, False) # window size cannot be changed
        self.iconbitmap(os.path.join(sys.path[0],"icons/mcp_icon.ico")) # look into same folder where the script is located
        
        self.__frame=tk.Frame(master=self, width=400, height=160)
        
        self.__var_selected_setup=StringVar(master=self.__frame)
        self.__var_selected_setup.set(self.__active_setup) # set the first setup as default setup
        self.__var_active_setup=StringVar(master=self.__frame)
        self.__var_active_setup.set(self.__active_setup)
        
        self.__label_setup_list_title=tk.Label(master=self.__frame, text="SELECT SETUP", font=('Segoe UI', 10, 'bold'))
        self.__label_setup_list_title.place(x=20,y=20)
        self.__list_selected_setup=ttk.Combobox(master=self.__frame, textvariable=self.__var_selected_setup, values=self.__setups_list, width=30, state='disabled')
        self.__list_selected_setup.place(x=20,y=45)
        
        self.__label_active_setup_title=tk.Label(master=self.__frame, text="ACTIVE SETUP", font=('Segoe UI', 10, 'bold'))
        self.__label_active_setup_title.place(x=20,y=75)
        self.__label_active_setup=tk.Label(master=self.__frame, textvariable=self.__var_active_setup, font=('Segoe UI', 10), width=28, anchor="w") # it is empty when initialized
        self.__label_active_setup.place(x=20,y=100)
        
        self.__button_load_setup=tk.Button(master=self.__frame, text="Load setup", width=16, command=self.__load_setup)
        self.__button_load_setup["state"]="disabled"
        self.__button_load_setup.place(x=260, y=27)
        self.__button_open_wsl=tk.Button(master=self.__frame, text="Open WSL", width=16, command=self.__open_wsl)
        self.__button_open_wsl.place(x=260, y=67)
        self.__button_open_sftp=tk.Button(master=self.__frame, text="Open SFTP folder", width=16, command=self.__open_sftp)
        self.__button_open_sftp.place(x=260, y=107)
        
        self.__frame.pack()
        self.__git_man.start_updating(self.update_setups_list, self.error_print)
        
    def __closed(self):
        # This method is called by tkinter internal functions when a shutdown is started (pressing X)
        self.__run_event.set()
        self.destroy()
    
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
        
        if self.__var_selected_setup.get() not in list_of_setups: # if currently selected setup is not in the new list of setups
            new_selected_setup=list_of_setups[0] # then it does not exist anymore, change selection to first setup in the list - actual change will be doen in the end
        else:
            new_selected_setup=self.__var_selected_setup.get()
            
        if len(self.__var_active_setup.get()) == 0: # if empty string then staring up, load the currently selected branch
            new_selected_setup=self.__git_man.get_active_setup()
        
        if self.__var_active_setup.get() not in list_of_setups: # if currently active setup is not in the new list of setups
            self.__load_setup(new_selected_setup) # then switch to another setup (the one currently selected)
        
        self.__list_selected_setup['values']=list_of_setups 
        
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
        self.__err_win=Toplevel(self) # create a pop up window which is child of the master window
        self.__err_win.title("ERROR")
        self.__err_win.resizable(False, False)
        self.__err_win.iconbitmap(os.path.join(os.path.join(sys.path[0],"icons/error_icon.ico")))
        self.__err_win.protocol("WM_DELETE_WINDOW", self.__closed)
        Label(master=self.__err_win, text=err_str, anchor="w").pack()
       
    def __load_setup(self, new_setup=None):
        # Internal method that is called when a new test setup (branch) needs
        # to be loaded
        if new_setup is None:
            selected_setup=self.__var_selected_setup.get()
        else:
            selected_setup=new_setup
        self.__button_load_setup["state"]="disabled"
        self.__list_selected_setup["state"]="disabled"
        threading.Thread(target=self.__git_man.load_setup, args=(selected_setup, self.setup_loaded)).start() # this implemented in a thread with callback function
    
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
        self.__var_active_setup.set(setup_name)
        self.__var_selected_setup.set(setup_name)
        self.__button_load_setup["state"]="normal"
        self.__list_selected_setup["state"]="readonly"
    
    def __open_wsl(self):
        # Internal method to open up a WSL terminal
        Popen(wsl_app_path, creationflags=CREATE_NEW_CONSOLE) # open a new WSL terminal window
        
    def __open_sftp(self):
        # Internal method to open up FIle Explorer with SFTP folder path
        Popen(sftp_path, creationflags=CREATE_NEW_CONSOLE)


class git_manager(threading.Thread):
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
    
    def __init__(self, repo_path, run_flag, timeout):
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
        self.__timeout=timeout
        self.__repo_path=repo_path
        os.chdir(self.__repo_path) # switch to directory where the repository is located
        self.__repo=git.Repo(self.__repo_path)
        self.__run_flag=run_flag
        self.__setups={}
        self.__lock=threading.Lock()
        threading.Thread.__init__(self)
        
    def run(self):
        # internal function for threading - this will be run when start() method is called
        while not self.__run_flag.is_set(): # while GUI has not been closed
            try:
                self.__lock.acquire()
                self.__prune_refs()
                new_setups=self.__get_setups() # get the list of all branches/setups
                self.__lock.release()
                if new_setups != self.__setups:
                    self.callback(new_setups)
                    self.__setups=new_setups
            except:
                err_str=traceback.format_exc()
                self.err_callback(err_str)
            self.__run_flag.wait(self.__timeout) # we can increase this value later
    
    def __prune_refs(self):
        # prune the origin repository of stale branches
        subprocess.run(["git", "remote", "prune", "origin"]) # we use subprocess because gitpython does not seem to have a direct way to prune
    
    def __get_setups(self):
        # pull any new branches or changes to existing branches, 
        # returns a dictionary of all the branches filtered by
        # ignore_setups list
        try:
            self.__repo.remotes.origin.pull()
        except git.exc.GitCommandError: # this will be raised when the branch has been deleted
            self.load_setup("main", None, True) # load main branch temporarely because we know this will never be deleted; we already have a lock and no callback func
        branches=self.__repo.refs # get all available branches form GIT server
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
        return str(self.__repo.head.reference)
    
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
            self.__lock.acquire()
        self.__prune_refs()
        branches=self.__repo.refs
        for branch in branches:
            branch_str=str(branch).split("/")[-1]
            if branch_str == setup_name:
                self.__repo.git.checkout(branch_str)
                if callback_func is not None:
                    callback_func(setup_name) 
        
        if lock_aquired is False:
            self.__lock.release()
        
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
            run=threading.Event()
            git_man=git_manager(repo_path, run, timeout)
            gui_app=git_gui(git_man, run)
            gui_app.mainloop() 
    except:
        traceback.print_exc()
        input("PRESS ENTER")
        