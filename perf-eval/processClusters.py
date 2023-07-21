import time
from multiprocessing import Pool
import concurrent.futures
from util.ssh_util import *
from util.ec2_util import *
from util.prop_util import *
from util.math_util import *

# Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY as environment variables

PROJECT="tiptoe"
USERNAME="ubuntu"

EC2_FILE = "config/ec2.json"
MACHINES_FILE = "config/process_machines_text.json"
#MACHINES_FILE = "config/process_machines2.json"
NUM_CLUSTERS = 4 * 3500
#NUM_CLUSTERS = 4 * 4000
#NUM_MACHINES = 1
NUM_MACHINES = 100
DISK_SIZE = 40 * 2
#DISK_SIZE = 30 * 2
#INSTANCE_TYPE = "r5.xlarge"
INSTANCE_TYPE = "r5.2xlarge"

def getServerName(i):
    return ("emma-cluster-text-%d" % i)

def getHostName(ip_addr):
    return "%s@%s" % (USERNAME, ip_addr)

def getIpByName(conn, name):
    ips = list()
    while (len(ips)!=1):
        waitUntilInitialised(conn,name,1)
        # Update the IP addresses
        ips = getEc2InstancesPublicIp(conn, 'Name', {'tag:Name':name}, True)
    return ips[0][1]
 
def getPrivateIpByName(conn, name):
    ips = list()
    while (len(ips)!=1):
        waitUntilInitialised(conn,name,1)
        # Update the IP addresses
        ips = getEc2InstancesPrivateIp(conn, 'Name', {'tag:Name':name}, True)
    return ips[0][1]
 
def provision():
    properties = loadPropertyFile(EC2_FILE)
    machines = loadPropertyFile(MACHINES_FILE)

    conn = startConnection(properties["region"])
    print("Started connection")
    key = getOrCreateKey(conn, properties["keyname"])
    print("Got key")

    # Start servers
    for i in range(NUM_MACHINES):
        print("Starting server %d" % i)
        startEc2Instance(conn, properties["ami_id"], key, INSTANCE_TYPE, [properties["security"]], properties["placement"], name=getServerName(i), disk_size=DISK_SIZE)
    print("Started all servers")

    machines['server_ip_address'] = []
    machines['server_private_ip_address'] = []
    for i in range(NUM_MACHINES):
        machines['server_ip_address'].append(getIpByName(conn, getServerName(i)))
        machines['server_private_ip_address'].append(getPrivateIpByName(conn, getServerName(i)))
    print(machines['server_ip_address'])

    with open(MACHINES_FILE, 'w') as f:
        json.dump(machines, f)

def setup_machine(ip_addr):
    properties = loadPropertyFile(EC2_FILE)
    #executeRemoteCommand(getHostName(ip_addr), 'cd private-search; git pull', key=properties['secret_key_path'], flags="-A")
    executeRemoteCommand(getHostName(ip_addr), 'ssh-keyscan github.com >> ~/.ssh/known_hosts; ssh -T git@github.com; git clone git@github.com:ahenzinger/private-search.git', key=properties['secret_key_path'], flags="-A")

def download_data(ip_addr, shard_idx):
    properties = loadPropertyFile(EC2_FILE)
    executeRemoteCommand(getHostName(ip_addr), 'cd private-search/code/perf-eval/s3; python3 download_img_from_s3.py %d' % shard_idx, key=properties['secret_key_path'])

def setupAll():
    properties = loadPropertyFile(EC2_FILE)
    machines = loadPropertyFile(MACHINES_FILE)

    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_MACHINES) as executor:
        future_to_res = [executor.submit(setup_machine, machines['server_ip_address'][i]) for i in range(NUM_MACHINES)]
        for future in concurrent.futures.as_completed(future_to_res):
            future.result()
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_MACHINES) as executor:
        future_to_res = [executor.submit(download_data, machines['server_ip_address'][i], i) for i in range(NUM_MACHINES)]
        for future in concurrent.futures.as_completed(future_to_res):
            future.result()

def teardown():
    properties = loadPropertyFile(EC2_FILE)
    conn = startConnection(properties['region'])
    key = getOrCreateKey(conn, properties['keyname'])
    for i in range(NUM_MACHINES):
        server_id = getEc2InstancesId(
            conn, 'Name', {'tag:Name':getServerName(i)}, True)
        terminateEc2Instances(conn, server_id)
        print("Terminated ec2 instance %s" % getServerName(i))

def processCluster(properties, machines, i):
    shard_size = NUM_CLUSTERS / 100 
    ip_addr = machines['server_ip_address'][i]
    #shard_size = NUM_CLUSTERS / NUM_MACHINES
    executeRemoteCommand(getHostName(ip_addr), 'source /home/ubuntu/.profile; cd private-search/code/cluster/kmeans; python3 process-all.py %d %d %d; cd ../../perf-eval/s3; python3 upload_result_to_s3.py' % (i * shard_size, (i + 1) * shard_size, i), key=properties['secret_key_path'])


def runProcessing():
    properties = loadPropertyFile(EC2_FILE)
    machines = loadPropertyFile(MACHINES_FILE)

    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_MACHINES) as executor:
        future_to_res = [executor.submit(processCluster, properties, machines, i) for i in range(NUM_MACHINES)]
        for future in concurrent.futures.as_completed(future_to_res):
            future.result()

#provision()
#time.sleep(120)
setupAll()
start = time.time()
runProcessing()
end = time.time()
#teardown()
print(end - start)
