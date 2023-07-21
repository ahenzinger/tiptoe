# Natach Crooks - 2014
# Contails utility function related to SSH
############################################

import os
import subprocess
import sys
import threading

# Functions include
# executeCommand
# executeCommandNoCheck
# executeCommandWithOutputReturn
# executeRemoteCommand
# executeRemoteCommandNoCheck
# executeRemoteCommandWithOutputReturn
# executeSequenceBlockingRemoteCommand
# executeParallelBlockingRemoteCommand
# executeNonBlockingRemoteCommand
# executeNonBlockingCommand
# killRemoteProcess
# mkdirRemote
# mkdirRemoteHosts
# rmDirRemote
# rmDirRemoteHosts
# rmDirRemoteIfExists
# rmFileRemoteIfExists
# setupTC/deleteTC
# gitPull
# svnUp
# getDirectory
# getDirectoryHosts
# getFile
# getFileHosts

# Executes a command, call is blocking
# Throws a CalledProcessError if
# doesn't succeed.
# Returns the result of the call
def executeCommandWithOutputReturn(command):
	print(command)
	p=subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,encoding='utf-8')
	out,err = p.communicate()
	return out.rstrip()

# Executes command on remote host (synchronously).
# Return output of the process
def executeRemoteCommandWithOutputReturn(host, command, key=None, flags=""):
    flags = "" if len(flags) == 0 else flags + " "
    if not key:
        cmd = "ssh -o StrictHostKeyChecking=no " + flags + host + " \"" + command + "\""
    else:
        cmd = "ssh -o StrictHostKeyChecking=no -i " + key + " " + flags + host + " \"" + command + "\""
    return executeCommandWithOutputReturn(cmd)

# Returns network interface of the remote host
def getRemoteNetInterface(host, key=None):
	cmd = "ifconfig | awk \'NR==1{print \$1 }\'"
	return executeRemoteCommandWithOutputReturn(host,cmd,key)

def executeCommand(command):
    print("Calling " + command)
    try:
    	subprocess.check_call(command, shell=True, stdout=sys.stdout, stderr=sys.stdout)
    except Exception as e:
        print("Terminated " +  command + " " + str(e))


# Executes a command, call is blocking
# Does not check for errors
def executeCommandNoCheck(command):
    print("Calling " + command)
    try:
        subprocess.call(command, shell=True, stdout=sys.stdout, stderr=sys.stdout)
    except Exception as e:
        print("Terminated " + command + " " + str(e))

# Executes command on remote host. Call is synchronous
def executeRemoteCommand(host, command, key=None, flags=""):
    flags = "" if len(flags) == 0 else flags + " "
    if not key:
        cmd = "ssh -o StrictHostKeyChecking=no " + flags + host + " \"" + command + "\""
    else:
        cmd = "ssh -o StrictHostKeyChecking=no -i " + key + " " + flags + host + " \"" + command + "\""
    print(cmd)
    executeCommand(cmd)


# Executes command on remote host without
# waiting for reply
def executeRemoteCommandNoCheck(host, command, key=None):
    if not key:
        cmd = "ssh -o StrictHostKeyChecking=no " + host + " \"" + command + "\""
    else:
        cmd = "ssh -o StrictHostKeyChecking=no -i " + key + " " + host + " \"" + command + "\""
    print("[" + cmd + "]")
    executeCommand(cmd)


# Executes, in sequence, specified command
# on each of the hosts in the list
# If returns an error throws an exception
def executeSequenceBlockingRemoteCommand(hosts, command, key=None):
    for h in hosts:
        if not key:
            cmd = "ssh -o StrictHostKeyChecking=no " + h + "'" + command + "'"
        else:
            cmd = "ssh -o StrictHostKeyChecking=no -i " + \
                  key + " " + h + "'" + command + "'"
        subprocess.check_call(cmd, shell=True)


# Executes, in parallel, specified command
# on each of the hosts in the list
# If returns an error throws an exception
def executeParallelBlockingRemoteCommand(hosts, command, key=None):
    thread_list = list()
    for h in hosts:
        if not key:
            cmd = "ssh -o StrictHostKeyChecking=no " + h + " '" + command + "'"
        else:
            cmd = "ssh -o StrictHostKeyChecking=no -i " + \
                  key + " " + h + " '" + command + "'"
        t = threading.Thread(target=executeCommand, args=(cmd,))
        thread_list.append(t)
        for t in thread_list:
            t.start()
    for t in thread_list:
        t.join()


# Executes a remote command in a new thread
# Does not check the error code returned
# Note: need to explicitly call t.start() afterwards
def executeNonBlockingRemoteCommand(host, command, key=None):
    t = threading.Thread(target=executeRemoteCommandNoCheck,
        args=(host, command, key))
    return t


# Executes a command in a new thread
# Note: need to explicitly call t.start() afterwards
def executeNonBlockingCommand(command):
    t = threading.Thread(target=executeCommand,
        args=(command,))
    return t



# Setups TC. TC is a network tool to simulate latency. This call will execute on the remote host and
# setup simulated latency between the remote host and the destHosts
def setupTC(host,latency,destHosts,key=None):
    max_bandwidth="10gibps"
    latency = latency/2
    interface = getNetInterface(host,key)
    command = 'sudo tc qdisc del dev %s root; ' % interface
    command += 'sudo tc qdisc add dev %s root handle 1: htb; ' % interface
    command += 'sudo tc class add dev %s parent 1: classid 1:1 htb rate %s; ' % (interface, max_bandwidth) # we want unlimited bandwidth
    idx = 2
    for d in destHosts:
        command += 'sudo tc class add dev %s parent 1:1 classid 1:%d htb rate %s; ' % (interface, idx, max_bandwidth)
        command += 'sudo tc qdisc add dev %s handle %d: parent 1:%d netem delay %dms; ' % (interface, idx, idx, latency)
        command += 'sudo tc filter add dev %s pref %d protocol ip u32 match ip dst %s flowid 1:%d; ' % (interface, idx, d, idx)
        idx += 1
    print("----------")
    print(command)
    print("----------")
    executeRemoteCommand(host,command,key)

# Deletes TC commands
def deleteTC(host, destHost,key=None):
    interface = getNetInterface(host,key)
    command = 'sudo tc qdisc del dev %s root; ' % interface
    executeRemoteCommand(host,command,key)


## Executes a command asynchronously.
# Call is asynchronous, output is piped
# Args are supplied as a list of args
def startProcess(args):
    return subprocess.Popen(args, stdout=PIPE, stderr=PIPE)


# Kills Process that matches string (using grep)
# Throws CalledProcessError for exception
def killRemoteProcess(host, process, user, key=None):
    try:
        cmd = "kill $(ps aux | grep " + process + " | grep -v grep |  awk '{print $2}') "
        cmd = "killall " + process
        executeRemoteCommand(host, cmd, key)
    except Exception as e:
        print("Killed " + str(e) + " " + cmd)


# Creates Directory on remote host
def mkdirRemote(host, directory, key=None):
    if not key:
        cmd = "ssh -o StrictHostKeyChecking=no " + host + " \'mkdir -p " + directory + " \'"
    else:
        cmd = "ssh -o StrictHostKeyChecking=no -i " + key + \
              " " + host + " \'mkdir -p " + directory + " \'"
    executeCommand(cmd)


# Creates Directory on remote hosts
def mkdirRemoteHosts(hosts, directory, key=None):
    print(hosts)
    for host in hosts:
        mkdirRemote(host, directory, key)

# Deletes remote dir, command fails if it does
# not exist
def rmdirRemoteHosts(hosts, directory, key=None):
    print(hosts)
    for host in hosts:
        try:
            rmdirRemote(host, directory, key)
        except Exception as e:
            print("Directory did not exist")


# Deletes remote dir, command fails if it does not exist
def rmdirRemote(host, directory, key=None):
    if not key:
        cmd = "ssh -o StrictHostKeyChecking=no " + host + " \'rm -r " + directory + "\'"
    else:
        cmd = "ssh -o StrictHostKeyChecking=no -i " + key + " " + host + " \'rm -r " + directory + "\'"
    executeCommand(cmd)


# Deletes remote dir, if it exists, otherwise, do nothing
def rmdirRemoteIfExists(host, directory, key=None):
    if not key:
        cmd = "ssh -o StrictHostKeyChecking=no " + host + " \'rm -r " + directory + "\'"
    else:
        cmd = "ssh -o StrictHostKeyChecking=no -i " + key + " " + host + " \'rm -r " + directory + "\'"
    executeCommandNoCheck(cmd)


# Deletes remote dir, if it exists, otherwise, do nothing
def rmfileRemoteIfExists(host, filee, key=None):
    if not key:
        cmd = "ssh -o StrictHostKeyChecking=no " + host + " \'rm " + filee + "\'"
    else:
        cmd = "ssh -o StrictHostKeyChecking=no -i " + key + " " + host + " \'rm " + filee + "\'"
    executeCommandNoCheck(cmd)


# Updates repository (GIT)
def gitPull(directory):
    cwd = os.getcwd()
    os.chdir(directory)
    cmd = "git pull"
    executeCommand(cmd)
    os.chdir(cwd)


# Updates repository (SVN)
def svnUp(directory):
    cwd = os.getcwd()
    os.chdir(directory)
    cmd = "svn up"
    executeCommand(cmd)

# Downloads folder remote_dir from all hosts in to local_dir
def getDirectory(local_dir, hosts, remote_dir, key=None):
    print(hosts)
    for h in hosts:
        if not key:
            cmd = "scp -o StrictHostKeyChecking=no -r " + \
                  h + ":" + remote_dir + " " + local_dir
        else:
            cmd = "scp -o StrictHostKeyChecking=no -i " + key + \
                  " -r " + h + ":" + remote_dir + " " + local_dir
        executeCommand(cmd)

# Downloads file from all hosts into local_dir
def getFile(local_dir, hosts, remote_file, key=None):
    print(hosts)
    for h in hosts:
        if not key:
            cmd = "scp  -o StrictHostKeyChecking=no " + \
                  h + ":" + remote_file + " " + local_dir
        else:
            cmd = "scp -o StrictHostKeyChecking=no -i " + key + \
                  " " + h + ":" + remote_file + " " + local_dir
        executeCommand(cmd)


# Sends file to remote host
def sendFile(local_file, h, remote_dir, key=None):
    if not key:
        cmd = "scp -o StrictHostKeyChecking=no  " + \
              local_file + " " + h + ":" + remote_dir
    else:
        cmd = "scp -o StrictHostKeyChecking=no -i " + key + \
              " " + local_file + " " + h + ":" + remote_dir
    executeCommand(cmd)


# Sends file to list of remote hosts
def sendFileHosts(local_file, hosts, remote_dir, key=None):
    for h in hosts:
        if not key:
            cmd = "scp  -o StrictHostKeyChecking=no " + \
                  local_file + " " + h + ":" + remote_dir
        else:
            cmd = "scp -o StrictHostKeyChecking=no -i " + key + \
                  " " + local_file + " " + h + ":" + remote_dir
        executeCommand(cmd)



# Install list of packages on list of hosts
def installPackages(hosts, package_list, key=None, assumeTrue = True):
    for package in package_list:
        if (assumeTrue):
    	    cmd = "sudo apt-get --yes install " + package
        else:
            cmd = "sudo apt-get install " + package
            try:
                executeParallelBlockingRemoteCommand(hosts, cmd, key)
            except Exception as e:
                print("Failed to install package " + package + " " + str(e))
