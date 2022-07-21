# branchManager
Simple GUI to manager switching branches on local repository. 

This GUI periodically (10 seconds) retrieves all available branches from the Git server of the repository
and lists them for the user in a drop-down list under 'SELECT SETUP' option. User can select the setup
and click 'Load setup' button which will then retrieve that branch from the server and switch to that branch.
While the branch is being retrieved the 'Load setup' and the drop-down list widgets are disabled (grayed out).
Once the branch is loaded then its name will be displayed under 'ACTIVE SETUP'.

The GUI also has a button to start running WSL terminal and open up a folder (SFTP) in File Explorer - both
of these applications are run with hardcoded path to the executables. 
