
import tkinter as tk
from tkinter import StringVar
from tkinter import *
import tkinter.ttk as ttk
from subprocess import Popen, CREATE_NEW_CONSOLE
import git
import threading
import sys, os, traceback
import subprocess
from ignore_setups import ignore_setups

class load_window(threading.Thread):
    
    def __init__(self):  
        super(load_window, self).__init__()
        
    def run(self):
        self.window=tk.Tk()
        self.window.resizable(False, False)
        frame=tk.Frame(self.window, width=400, height=160)
        frame.grid(row=0, column=0, sticky="NE")
        label= tk.Label(self.window, text="Starting up MCP manager...", font= ('Helvetica 14 bold'))
        label.config(anchor=tk.CENTER)
        label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        #self.window.overrideredirect(1)
        self.window.attributes('-topmost',True)
        self.window.mainloop()
    
    def close(self):
        self.window.quit()
        #self.window.destroy()
        print("closed")

class git_gui():
    '''
    Create a GUI for MCP manager
    '''

    def __init__(self, git_man, run_event): 
        self.run_event=run_event
        self.git_man=git_man
               
        self.setups_list=[]
        self.active_setup=""
        
        self.err_win=None # if there is an exception then this will hold the error window object
        self.window=tk.Tk()
        self.window.protocol("WM_DELETE_WINDOW", self.closed)
        self.window.title("MCP manager")
        self.window.resizable(False, False) # window size cannot be changed
        self.window.iconbitmap(os.path.join(sys.path[0],"icons/mcp_icon.ico")) # look into same folder where the script is located
        
        self.frame=tk.Frame(master=self.window, width=400, height=160)
        
        self.var_selected_setup=StringVar(master=self.frame)
        self.var_selected_setup.set(self.active_setup) # set the first setup as default setup
        self.var_active_setup=StringVar(master=self.frame)
        self.var_active_setup.set(self.active_setup)
        
        self.label_setup_list_title=tk.Label(master=self.frame, text="SELECT SETUP", font=('Segoe UI', 10, 'bold'))
        self.label_setup_list_title.place(x=20,y=20)
        self.list_selected_setup=ttk.Combobox(master=self.frame, textvariable=self.var_selected_setup, values=self.setups_list, width=30, state='disabled')
        self.list_selected_setup.place(x=20,y=45)
        
        self.label_active_setup_title=tk.Label(master=self.frame, text="ACTIVE SETUP", font=('Segoe UI', 10, 'bold'))
        self.label_active_setup_title.place(x=20,y=75)
        self.label_active_setup=tk.Label(master=self.frame, textvariable=self.var_active_setup, font=('Segoe UI', 10), width=28, anchor="w") # it is empty when initialized
        self.label_active_setup.place(x=20,y=100)
        
        self.button_load_setup=tk.Button(master=self.frame, text="Load setup", width=16, command=self.load_setup)
        self.button_load_setup["state"]="disabled"
        self.button_load_setup.place(x=260, y=27)
        self.button_open_wsl=tk.Button(master=self.frame, text="Open WSL", width=16, command=self.open_wsl)
        self.button_open_wsl.place(x=260, y=67)
        self.button_open_sftp=tk.Button(master=self.frame, text="Open SFTP folder", width=16, command=self.open_sftp)
        self.button_open_sftp.place(x=260, y=107)
        
        self.frame.pack()
        self.git_man.start_updating(self.update_setups_list, self.error_print)
        self.window.mainloop() 
        
    def closed(self):
        self.run_event.set()
        self.window.destroy()
        # if self.err_win:
        #     self.err_win.destroy()
    
    def update_setups_list(self, setups_list):
        list_of_setups=list(setups_list.values()) # convert dictionary into list
        
        if self.var_selected_setup.get() not in list_of_setups: # if currently selected setup is not in the new list of setups
            new_selected_setup=list_of_setups[0] # then it does not exist anymore, change selection to first setup in the list - actual change will be doen in the end
        else:
            new_selected_setup=self.var_selected_setup.get()
            
        if len(self.var_active_setup.get()) == 0: # if empty string then staring up, load the currently selected branch
            new_selected_setup=self.git_man.get_active_setup()
        
        if self.var_active_setup.get() not in list_of_setups: # if currently active setup is not in the new list of setups
            self.load_setup(new_selected_setup) # then switch to another setup (the one currently selected)
        
        self.list_selected_setup['values']=list_of_setups 
        
    def error_print(self, err_str):
        self.err_win=Toplevel(self.window) # create a pop up window which is child of the master window
        self.err_win.title("ERROR")
        self.err_win.resizable(False, False)
        self.err_win.iconbitmap(os.path.join(os.path.join(sys.path[0],"icons/error_icon.ico")))
        self.err_win.protocol("WM_DELETE_WINDOW", self.closed)
        Label(master=self.err_win, text=err_str, anchor="w").pack()
        
    def warning_print(self, war_str):
        self.war_win=tk.Tk()
        self.war_win.title("WARNING")
        self.war_win.resizable(False, False)
        self.war_win.iconbitmap(os.path.join(os.path.join(sys.path[0],"error_icon.ico")))
        self.war_win.protocol("WM_DELETE_WINDOW", self.closed)
        self.lab=tk.Label(master=self.war_win, text=war_str, anchor="w")
        self.lab.pack()
        self.war_win.mainloop()
       
    def load_setup(self, new_setup=None):
        if new_setup is None:
            selected_setup=self.var_selected_setup.get()
        else:
            selected_setup=new_setup
        self.button_load_setup["state"]="disabled"
        self.list_selected_setup["state"]="disabled"
        threading.Thread(target=self.git_man.load_setup, args=(selected_setup, self.setup_loaded)).start() # this implemented in a thread with callback function
    
    def setup_loaded(self, setup_name):
        """
        Callback function which is called when setup finsihes loading.
        """
        self.var_active_setup.set(setup_name)
        self.var_selected_setup.set(setup_name)
        self.button_load_setup["state"]="normal"
        self.list_selected_setup["state"]="readonly"
    
    def open_wsl(self):
        Popen(r'C:\Windows\System32\wsl.exe ~', creationflags=CREATE_NEW_CONSOLE) # open a new WSL terminal window
        
    def open_sftp(self):
        Popen(r'explorer.exe /e,C:\Users', creationflags=CREATE_NEW_CONSOLE)


class git_manager(threading.Thread):
    
    def __init__(self, repo_path, run_flag):
        self.repo_path=repo_path
        os.chdir(self.repo_path)
        self.repo=git.Repo(self.repo_path)
        self.run_flag=run_flag
        self.setups={}
        self.lock=threading.Lock()
        threading.Thread.__init__(self)
        
    def run(self):
        while not self.run_flag.is_set():
            try:
                self.lock.acquire()
                self.update_refs()
                new_setups=self.get_setups() # get the list of all branches/setups
                self.lock.release()
                if new_setups != self.setups:
                    self.callback(new_setups)
                    self.setups=new_setups
                raise ValueError()
            except:
                err_str=traceback.format_exc()
                self.err_callback(err_str)
            self.run_flag.wait(10) # we can increase this value later
    
    def update_refs(self):
        # prune the origin repository of stale branches - we use subprocess because gitpython does not seem to have a direct way to prune
        subprocess.run(["git", "remote", "prune", "origin"])
    
    def get_setups(self):
        try:
            self.repo.remotes.origin.pull()
        except git.exc.GitCommandError: # this will be raised when the branch has been deleted
            self.load_setup("main", None, True) # load main branch temporarely because we know this will never be deleted; we already have a lock and no callback func
        branches=self.repo.refs # get all available branches form GIT server
        setups={} # setups will be in dictionary with key being index in refs list and value being the setup name
        for branch in branches: # convert the ref objects into branch name strings
            if isinstance(branch, git.RemoteReference) and (str(branch) != "origin/HEAD"): # check if valid branch name (e.g. HEAD not valid)
                branch_name=str(branch).split("/")[-1] # get only the branch name
                if branch_name not in ignore_setups: # check if this branch we ignore
                    setups[branches.index(branch)]=branch_name
        
        if self.get_active_setup() == "main":
            self.load_setup(list(setups.values())[0], None, True) # load first existing setup/branch
        
        return setups   # there needs to be a check to see if any new branch available
    
    def get_active_setup(self):
        return str(self.repo.head.reference)
    
    def load_setup(self, setup_name, callback_func=None, lock_aquired=False):
        if lock_aquired is False: 
            self.lock.acquire()
        self.update_refs()
        branches=self.repo.refs
        for branch in branches:
            branch_str=str(branch).split("/")[-1]
            if branch_str == setup_name:
                self.repo.git.checkout(branch_str)
                # self.repo.head.reference=branch
                # self.repo.head.reset(index=True, working_tree=True)
                if callback_func is not None:
                    callback_func(setup_name) # if okay then return with None
        
        if lock_aquired is False:
            self.lock.release()
        
    def start_updating(self, callback, err_callback):
        self.callback=callback
        self.err_callback=err_callback
        self.start()
        
def is_running(): # this function checks if there is an MCP manager app running already
    # needs to be implmented yet
    return False

if __name__ == "__main__":
    try:
        repo_path=r'C:\Users\eonrrfe\OneDrive - Ericsson\Ron\Software development\Python\temp_files\testRepo'
        if is_running(): # if already running then don't open another app
            sys.exit()
            
        run=threading.Event()
        git_man=git_manager(repo_path, run)
        gui_app=git_gui(git_man, run)
        
    except:
        traceback.print_exc()
        input("PRESS ENTER")