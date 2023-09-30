import time
from multiprocessing import Pool
import concurrent.futures
import argparse
import numpy as np
from ec2_util.ssh_util import *
from ec2_util.ec2_util import *
from ec2_util.prop_util import *

# Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY as environment variables

PROJECT="tiptoe"
USERNAME="ubuntu"

EC2_FILE = "config/ec2.json"
MACHINES_FILE = "config/machines.json"

parser = argparse.ArgumentParser(description='Performance experiments')
parser.add_argument('-is', '--image_search', action='store_true', default=False)
args = parser.parse_args()

def getEmbedServerName(i):
    return ("full-embed-server-%d") % (i)

def getUrlServerName(i):
    return ("full-url-server-%d") % (i)

def getCoordinatorName():
    return ("full-coordinator")

def getLatClientName():
    return ("full-lat-client")

def getTputClientName():
    return ("full-tput-client")

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
    for i in range(properties["num_embed_servers"]):
        print("Starting embedding server %d" % i)
        startEc2Instance(conn, properties["ami_id"], key, properties["instance_type"], [properties["security"]], properties["placement"], name=getEmbedServerName(i), disk_size=properties["disk_size"])
    print("Started all embedding servers")

    for i in range(properties["num_url_servers"]):
        print("Starting URL server %d" % i)
        startEc2Instance(conn, properties["ami_id"], key, properties["instance_type"], [properties["security"]], properties["placement"], name=getUrlServerName(i), disk_size=properties["disk_size"])
    print("Started all URL servers")
    
    # Start coordinator
    startEc2Instance(conn, properties["ami_id"], key, properties["coordinator_instance_type"], [properties["security"]], properties["placement"], name=getCoordinatorName(), disk_size=properties["disk_size"])
    print("Started coordinator")
    
    # Start latency client
    startEc2Instance(conn, properties["ami_id"], key, properties["lat_client_instance_type"], [properties["security"]], properties["placement"], name=getLatClientName(), disk_size=properties["disk_size"])
    print("Started latency client")

    # Start tput client
    startEc2Instance(conn, properties["ami_id"], key, properties["tput_client_instance_type"], [properties["security"]], properties["placement"], name=getTputClientName(), disk_size=properties["disk_size"])
    print("Started tput client")

    machines['embed_server_ip_address'] = []
    machines['embed_server_private_ip_address'] = []
    for i in range(properties["num_embed_servers"]):
        machines['embed_server_ip_address'].append(getIpByName(conn, getEmbedServerName(i)))
        machines['embed_server_private_ip_address'].append(getPrivateIpByName(conn, getEmbedServerName(i)))
    print(machines['embed_server_ip_address'])

    machines['url_server_ip_address'] = []
    machines['url_server_private_ip_address'] = []
    for i in range(properties["num_url_servers"]):
        machines['url_server_ip_address'].append(getIpByName(conn, getUrlServerName(i)))
        machines['url_server_private_ip_address'].append(getPrivateIpByName(conn, getUrlServerName(i)))
    print(machines['url_server_ip_address'])

    machines['coordinator_ip_address'] = getIpByName(conn, getCoordinatorName())
    machines['coordinator_private_ip_address'] = getPrivateIpByName(conn, getCoordinatorName())

    machines['lat_client_ip_address'] = getIpByName(conn, getLatClientName())
    machines['lat_client_private_ip_address'] = getPrivateIpByName(conn, getLatClientName())

    machines['tput_client_ip_address'] = getIpByName(conn, getTputClientName())
    machines['tput_client_private_ip_address'] = getPrivateIpByName(conn, getTputClientName())

    with open(MACHINES_FILE, 'w') as f:
        json.dump(machines, f)

def setup_machine(ip_addr):
    properties = loadPropertyFile(EC2_FILE)

    executeRemoteCommand(getHostName(ip_addr), 'mkdir -p ~/.aws', key=properties['secret_key_path'])
    sendFile("~/.aws/credentials", getHostName(ip_addr), "~/.aws/credentials", key=properties['secret_key_path'])

    executeRemoteCommand(getHostName(ip_addr), 'ssh-keyscan github.com >> ~/.ssh/known_hosts; git clone git@github.com:ahenzinger/tiptoe.git; source /home/ubuntu/.profile; cd tiptoe; go mod download', key=properties['secret_key_path'], flags="-A")
    #executeRemoteCommand(getHostName(ip_addr), 'ssh-keyscan github.com >> ~/.ssh/known_hosts; cd tiptoe; git pull', key=properties['secret_key_path'], flags="-A")
    #executeRemoteCommand(getHostName(ip_addr), 'sudo sysctl -w net.ipv4.tcp_congestion_control=bbr')

def download_embedding_data(ip_addr, shard_idx):
    properties = loadPropertyFile(EC2_FILE)

    num_logical = properties['servers_per_machine']
    start = num_logical * shard_idx
    end = start + num_logical

    if args.image_search:
        executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 img_download_from_s3.py embedding %d' % start, key=properties['secret_key_path'])
        for i in range(start+1, end):
            executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 img_download_from_s3.py embedding %d' % i, key=properties['secret_key_path'])

    else:
        executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 text_download_from_s3.py embedding %d' % start, key=properties['secret_key_path'])
        for i in range(start+1, end):
            executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 text_download_from_s3.py embedding %d' % i, key=properties['secret_key_path'])
    executeRemoteCommand(getHostName(ip_addr), 'rm ~/.aws/credentials', key=properties['secret_key_path'])


def download_url_data(ip_addr, shard_idx):
    properties = loadPropertyFile(EC2_FILE)

    num_logical = properties['servers_per_machine']
    start = num_logical * shard_idx
    end = start + num_logical

    if args.image_search:
        executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 img_download_from_s3.py url %d' % start, key=properties['secret_key_path'])
        for i in range(start+1, end):
            executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 img_download_from_s3.py url %d' % i, key=properties['secret_key_path'])
    else:
        executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 text_download_from_s3.py url %d' % start, key=properties['secret_key_path'])
        for i in range(start+1, end):
            executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 text_download_from_s3.py url %d' % i, key=properties['secret_key_path'])
    executeRemoteCommand(getHostName(ip_addr), 'rm ~/.aws/credentials', key=properties['secret_key_path'])

def download_coordinator_data(ip_addr):
    properties = loadPropertyFile(EC2_FILE)
    if args.image_search:
        executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 img_download_from_s3.py coordinator 0', key=properties['secret_key_path'])
    else:
        executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 text_download_from_s3.py coordinator 0', key=properties['secret_key_path'])
    executeRemoteCommand(getHostName(ip_addr), 'rm ~/.aws/credentials', key=properties['secret_key_path'])

def download_client_data(ip_addr):
    properties = loadPropertyFile(EC2_FILE)
    if args.image_search:
        executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 img_download_from_s3.py client 0', key=properties['secret_key_path'])
    else:
        executeRemoteCommand(getHostName(ip_addr), 'cd tiptoe/perf-eval/s3; python3 text_download_from_s3.py client 0', key=properties['secret_key_path'])
    executeRemoteCommand(getHostName(ip_addr), 'rm ~/.aws/credentials', key=properties['secret_key_path'])

def setupAll():
    properties = loadPropertyFile(EC2_FILE)
    machines = loadPropertyFile(MACHINES_FILE)

    with concurrent.futures.ThreadPoolExecutor(max_workers=properties['num_embed_servers']) as executor:
        future_to_res = [executor.submit(setup_machine, machines['embed_server_ip_address'][i]) for i in range(properties['num_embed_servers'])]
        for future in concurrent.futures.as_completed(future_to_res):
            future.result()

    with concurrent.futures.ThreadPoolExecutor(max_workers=properties['num_url_servers']) as executor:
        future_to_res = [executor.submit(setup_machine, machines['url_server_ip_address'][i]) for i in range(properties['num_url_servers'])]
        for future in concurrent.futures.as_completed(future_to_res):
            future.result()

    with concurrent.futures.ThreadPoolExecutor(max_workers=properties['num_embed_servers']) as executor:
        future_to_res = [executor.submit(download_embedding_data, machines['embed_server_ip_address'][i], i) for i in range(properties['num_embed_servers'])]
        for future in concurrent.futures.as_completed(future_to_res):
            future.result()

    with concurrent.futures.ThreadPoolExecutor(max_workers=properties['num_url_servers']) as executor:
        future_to_res = [executor.submit(download_url_data, machines['url_server_ip_address'][i], i) for i in range(properties['num_url_servers'])]
        for future in concurrent.futures.as_completed(future_to_res):
            future.result()

    setup_machine(machines['coordinator_ip_address'])
    download_coordinator_data(machines['coordinator_ip_address'])
    setup_machine(machines['lat_client_ip_address'])
    download_client_data(machines['lat_client_ip_address'])
    setup_machine(machines['tput_client_ip_address'])
    download_client_data(machines['tput_client_ip_address'])

def teardown():
    properties = loadPropertyFile(EC2_FILE)
    conn = startConnection(properties['region'])
    key = getOrCreateKey(conn, properties['keyname'])
    for i in range(properties['num_embed_servers']):
        server_id = getEc2InstancesId(
            conn, 'Name', {'tag:Name':getEmbedServerName(i)}, True)
        terminateEc2Instances(conn, server_id)
        print("Terminated ec2 instance %s" % getEmbedServerName(i))
    for i in range(properties['num_url_servers']):
        server_id = getEc2InstancesId(
            conn, 'Name', {'tag:Name':getUrlServerName(i)}, True)
        terminateEc2Instances(conn, server_id)
        print("Terminated ec2 instance %s" % getUrlServerName(i))
    coordinator_id = getEc2InstancesId(
        conn, 'Name', {'tag:Name':getCoordinatorName()}, True)
    terminateEc2Instances(conn, coordinator_id)
    lat_client_id = getEc2InstancesId(
        conn, 'Name', {'tag:Name':getLatClientName()}, True)
    terminateEc2Instances(conn, lat_client_id)
    tput_client_id = getEc2InstancesId(
        conn, 'Name', {'tag:Name':getTputClientName()}, True)
    terminateEc2Instances(conn, tput_client_id)

def setupExp():
    flag = ""
    if args.image_search:
        flag += " -image_search true "

    properties = loadPropertyFile(EC2_FILE)
    machines = loadPropertyFile(MACHINES_FILE)

    num_logical = properties['servers_per_machine']

    for j in range(num_logical):
        for i in range(properties['num_embed_servers']):
            at = num_logical * i + j
            executeRemoteCommand(getHostName(machines['embed_server_ip_address'][i]), ('source /home/ubuntu/.profile; cd tiptoe/search; if pgrep server; then pkill -f server; fi; nohup go run . emb-server %d > /dev/null 2>&1 &') % at, key=properties['secret_key_path'])

        for i in range(properties['num_url_servers']):
            at = num_logical * i + j
            executeRemoteCommand(getHostName(machines['url_server_ip_address'][i]), ('source /home/ubuntu/.profile; cd tiptoe/search; if pgrep server; then pkill -f server; fi; nohup go run . url-server %d > /dev/null 2>&1 &') % at, key=properties['secret_key_path'])
    

        time.sleep(300)

    print("Started all server processes, waiting to start coordinator")

    ip_string = " ".join(np.repeat(machines['embed_server_private_ip_address'], num_logical)) + " " + " ".join(np.repeat(machines['url_server_private_ip_address'], num_logical))
    coordinator_out = executeRemoteCommandWithOutputReturn(getHostName(machines['coordinator_ip_address']), 'source /home/ubuntu/.profile; cd tiptoe/search; if pgrep coordinator; then pkill -f coordinator; fi; nohup go run . coordinator %d %d %s %s > /dev/null 2>&1 &' % (properties['num_embed_servers'] * num_logical, properties['num_url_servers'] * num_logical, ip_string, flag), key=properties['secret_key_path'])

    print("Started coordinator, waiting to start client")

    time.sleep(180)
#    if properties['num_embed_servers'] <= 10:
#        time.sleep(60)
#    else:
#        time.sleep(600)

def runLatencyExp():
    flag = ""
    if args.image_search:
        flag += " -image_search true "

    properties = loadPropertyFile(EC2_FILE)
    machines = loadPropertyFile(MACHINES_FILE)

    client_out = executeRemoteCommandWithOutputReturn(getHostName(machines['lat_client_ip_address']), 'source /home/ubuntu/.profile; cd tiptoe/search; ./wan.sh; go run . client-latency %s %s' % (machines['coordinator_private_ip_address'], flag), key=properties['secret_key_path'])
    print("Latency experiment finished")

    prefix = "camera-ready-text/"
    if args.image_search:
        prefix = "camera-ready-img/"

    fn = prefix + str(properties['num_embed_servers']) + "-" + str(properties['num_url_servers']) + "-" + str(properties['servers_per_machine']) + "-latency.log"
    with open(fn, "w") as f:
        f.write(client_out)

def runTputExp():
    flag = ""
    if args.image_search:
        flag += " -image_search true "

    properties = loadPropertyFile(EC2_FILE)
    machines = loadPropertyFile(MACHINES_FILE)

    client_out = executeRemoteCommandWithOutputReturn(getHostName(machines['tput_client_ip_address']), 'source /home/ubuntu/.profile; cd tiptoe/search; go run . client-tput-embed %s %s' % (machines['coordinator_private_ip_address'], flag), key=properties['secret_key_path'])
    print("Embedding throughput experiment finished")

    prefix = "camera-ready-text/"
    if args.image_search:
        prefix = "camera-ready-img/"

    fn = prefix + str(properties['num_embed_servers']) + "-" + str(properties['num_url_servers']) + "-" + str(properties['servers_per_machine']) + "-tput-embed.log"
    with open(fn, "w") as f:
        f.write(client_out)
 
    client_out = executeRemoteCommandWithOutputReturn(getHostName(machines['tput_client_ip_address']), 'source /home/ubuntu/.profile; cd tiptoe/search; go run . client-tput-url %s' % (machines['coordinator_private_ip_address']), key=properties['secret_key_path'])
    print("URL throughput experiment finished")

    fn = prefix + str(properties['num_embed_servers']) + "-" + str(properties['num_url_servers']) + "-" + str(properties['servers_per_machine']) + "-tput-url.log"
    with open(fn, "w") as f:
        f.write(client_out)

    client_out = executeRemoteCommandWithOutputReturn(getHostName(machines['tput_client_ip_address']), 'source /home/ubuntu/.profile; cd tiptoe/search; go run . client-tput-offline %s' % (machines['coordinator_private_ip_address']), key=properties['secret_key_path'])
    print("Offline throughput experiment finished")

    fn = prefix + str(properties['num_embed_servers']) + "-" + str(properties['num_url_servers']) + "-" + str(properties['servers_per_machine']) + "-tput-offline.log"
    with open(fn, "w") as f:
        f.write(client_out)

provision()
time.sleep(120)
setupAll()
setupExp()
runLatencyExp()
runTputExp()
teardown()

print("Experiments finished.")
