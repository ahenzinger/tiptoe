import boto
import logging
import os
import sys
import time

import boto.ec2

all_ec2_regions = [re.name for re in boto.ec2.regions()]
# HACK: these are new EC2 regions which boto
# doesn't currently support
all_ec2_regions = all_ec2_regions + [u"eu-west-2", u"ca-central-1"]
canada_region = boto.ec2.RegionInfo(
    None, u"ca-central-1", "ec2.ca-central-1.amazonaws.com")
euwest_region = boto.ec2.RegionInfo(
    None, u"eu-west-2", "ec2.eu-west-2.amazonaws.com")
useast_region = boto.ec2.RegionInfo(
    None, u"us-east-2", "ec2.us-east-2.amazonaws.com")
no_access_ec2_regions = ['us-gov-west-1', 'cn-north-1']
ec2_regions = [x for x in all_ec2_regions if x not in no_access_ec2_regions]

def waitUntilInitialised(conn,tag, nbInstances = 1):
    initialised = False
    while (not initialised):
        initialised = True
        status = []
        while (len(status) < nbInstances):
            try:
                status = conn.get_all_instance_status(instance_ids=getEc2InstancesId(conn, 'Name', {'tag:Name':tag}, True))
                print(status)
            except Exception as e:
                print(e)
        status = []
        time.sleep(5)
        for s in status:
            print(s.system_status.details['reachability'])
            if (s.system_status.details['reachability'] != 'passed'):
                initialised = False

    print("All initialised")




# Loads appropriate keypair. Creates it if doesn't exist yet
def getOrCreateKey(conn, keyname):
    try:
        key = conn.get_all_key_pairs(keynames=[keyname])[0]
        return key.name
    except boto.exception.EC2ResponseError as e:
        if e.code == 'InvalidKeyPair.NotFound':
            print('Creating keypair: %s' % keyname)
            # Create an SSH key to use when logging into instances.
            key = conn.create_key_pair(keyname)
            # AWS will store the public key but the private key is
            # generated and returned and needs to be stored locally.
            # The save method will also chmod the file to protect
            # your private key.
            key.save(".")
            return key.name
        else:
            raise


# Obtains the instance reservation for a spot request (blocking call)
def getSpotReservation(conn, price, ami_id, key, instance, security, placement, disk=None, ebs_optimized=False):
    spot = conn.request_spot_instances(price, image_id=ami_id, key_name=key, instance_type=instance,
        security_groups=security, block_device_map=disk, ebs_optimized=ebs_optimized, placement=placement) # Set to true again
    fulfilled = None
    while (not fulfilled):
        fulfilled = conn.get_all_spot_instance_requests([spot[0].id], filters={'status-code': 'fulfilled'})
    reservations = conn.get_all_instances(instance_ids=fulfilled[0].instance_id)
    return reservations[0]


# Starts an instance with an optional name
def startEc2Instance(conn, ami_id, key, instance, security, placement, name=None, disk_size=None, spot=None, price=0.3, ebs_optimized=False):
    initialized = False
    while not initialized:
      try:
        # Create an ebs volumne and attach it
        if disk_size:
            # First need to create a block device mapping
            dev_sda1 = boto.ec2.blockdevicemapping.EBSBlockDeviceType(delete_on_termination=True)
            dev_sda1.size = disk_size  # Size in Gigabytes
            bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
            bdm['/dev/sda1'] = dev_sda1
            # After this you can give the block device map in your run_instances call:
            if (not spot):
                reservation = conn.run_instances(ami_id, key_name=key,
                    instance_type=instance, security_groups=security, placement=placement,block_device_map=bdm, ebs_optimized=ebs_optimized)
            else:
                reservation = getSpotReservation(conn, price, ami_id, key, instance, security,
        placement, disk=bdm)
        else:
            if (not spot):
                reservation = conn.run_instances(ami_id, key_name=key,
                    instance_type=instance, security_groups=security, ebs_optimized=ebs_optimized, placement=placement)
            else:
                reservation = getSpotReservation(conn, price, ami_id, key, instance, security, placement)
        if name:
            reservation.instances[0].add_tag('Name', name)
        initialized = True
      except boto.exception.BotoServerError as e:
        print(e)
        time.sleep(5)
      except Exception as e:
        print(e)
        initialized = True


## Stops the list of specified instances (state
## is preserved. Call restartEc2Instances to restart)
## Warning: these will not be restarted with the same
## IP Address
def stopEc2Instances(conn, instance_id_list):
    if len(instance_id_list):
        conn.stopEc2Instances(ami_id_list)

## Restarts the list of specified instance id.
## WARNING: these instances are restarted with a different
## IP Address
def restartEc2Instances(conn, instance_id_list):
    if len(instance_id_list):
        conn.stopEc2Instances(ami_id_list)

## Terminates the list of specified instance ids.
## The associated volume storage is deleted
def terminateEc2Instances(conn, instance_id_list):
    if len(instance_id_list):
        conn.terminate_instances(instance_id_list)


# Returns list of tuples (instance_name, ip_address)
def getEc2InstanceObjects(conn, name_tag, filters=None, active=False):
    instances = []
    if filters:
        reservations = conn.get_all_instances(filters=filters)
    else:
        reservations = conn.get_all_instances()
    for reservation in reservations:
        for instance in reservation.instances:
            if (not active or (instance.state == 'pending' or instance.state == 'running')):
                instances.append(instance)
    return instances


def getEc2Instances(conn, name_tag, filters=None):
    instances = []  # (instance_name, public_ip_address,private_ip_address)
    if filters:
        reservations = conn.get_all_instances(filters=filters)
    else:
        reservations = conn.get_all_instances()
    for reservation in reservations:
        for instance in reservation.instances:
            instance_name = instance.tags.get(name_tag)
            priv_ip_address = getattr(instance, 'private_ip_address')
            ip_address = getattr(instance, 'ip_address')
            if ip_address and priv_ip_address:
                pair = (instance_name, ip_address, priv_ip_address)
                instances.append(pair)
    return instances


# Returns list of dns 
def getEc2InstancesDns(conn, name_tag, filters=None,
active=False):
    instances = []  # (instance_name, ip_address)
    if filters:
        reservations = conn.get_all_instances(filters=filters)
    else:
        reservations = conn.get_all_instances()
    for reservation in reservations:
        for instance in reservation.instances:
            instance_name = instance.tags.get(name_tag)
            ip_address = getattr(instance, 'public_dns_name')
            if ip_address and (not active or (instance.state == 'pending' or instance.state == 'running')):
                pair = (instance_name, ip_address)
                instances.append(pair)
    return instances

# Returns list of public ips
def getEc2InstancesPublicIp(conn, name_tag, filters=None,
active=False):
    instances = []  # (instance_name, ip_address)
    if filters:
        reservations = conn.get_all_instances(filters=filters)
    else:
        reservations = conn.get_all_instances()
    for reservation in reservations:
        for instance in reservation.instances:
            instance_name = instance.tags.get(name_tag)
            ip_address = getattr(instance, 'ip_address')
            if ip_address and (not active or (instance.state == 'pending' or instance.state == 'running')):
                pair = (instance_name, ip_address)
                instances.append(pair)
    return instances


def getEc2InstancesPrivateIp(conn, name_tag, filters=None, active=False):
    instances = []  # (instance_name, ip_address)
    if filters:
        reservations = conn.get_all_instances(filters=filters)
    else:
        reservations = conn.get_all_instances()
    for reservation in reservations:
        for instance in reservation.instances:
            instance_name = instance.tags.get(name_tag)
            ip_address = getattr(instance, 'private_ip_address')
            if ip_address and (not active or (instance.state == 'pending' or instance.state == 'running')):
                pair = (instance_name, ip_address)
                instances.append(pair)
    return instances


# Returns list of instance ids


def getEc2InstancesId(conn, name_tag, filters=None, active=False):
    instances = []  # (instance_name, ip_address)
    if filters:
        reservations = conn.get_all_instances(filters=filters)
    else:
        reservations = conn.get_all_instances()
    for reservation in reservations:
        for instance in reservation.instances:
            instance_name = instance.tags.get(name_tag)
            instance_id = getattr(instance, 'id')
            if instance_id and (not active or (instance.state == 'pending' or instance.state == 'running')):
                instances.append(instance_id)
    return instances





# Initialises an EC2 connetion
# Returns null if fails to connect
# Region should be a string of the format
# "us-west-2' for example


def startConnection(region):
    # boto.set_stream_logger('boto')
    logging.getLogger('boto').setLevel(logging.ERROR)
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not aws_key:
        print("Error: AWS_KEY not set")
    if not aws_secret:
        print("Error: AWS_SECRET not set")
    if region == u"eu-west-2" or region == u"ca-central-1" or region == u"us-east-2":
        if region == u"eu-west-2":
            reg = euwest_region
        if region == u"us-east-2":
            reg = useast_region
        if region == u"ca-central-1":
            reg = canada_region
    else:
        reg = boto.ec2.get_region(region,
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret)
    try:
        conn = boto.ec2.connection.EC2Connection(
            aws_key, aws_secret, region=reg)
        return conn
    except:
        print("Failed to connect")


# Utility method for ssh configuration
def printSshConfig(instances):
    """ Print out as ssh-config file format """
    for instance_name, ip_address in instances:
        # double quote if name contains space
        instance_name = '"{0}"'.format(
            instance_name) if ' ' in instance_name else instance_name
        print("Host %s" % instance_name)
        print("Hostname %s" % ip_address)
        print("")


# Prints out EC2 configuration
def printEc2Config(region, filter):
    filters = dict([f.split('=', 1) for f in filter])
    ip_addr_attr = 'ip_address'
    ip_addr_attr_priv = 'private_ip_address'
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    # validation
    if not aws_key or not aws_secret:
        if not aws_key:
            print("AWS_ACCESS_KEY_ID not set in environment and not", \
                "specified by -k AWS_KEY or --aws-key AWS_KEY", file=sys.stderr)
        if not aws_secret:
            print("AWS_SECRET_ACCESS_KEY not set in envoronment and not", \
                "specified by -s AWS_SECRET or --aws-secret AWS_SECRET", file=sys.stderr)
        sys.exit(2)

    if region == u"eu-west-2" or region == u"ca-central-1":
        if region == u"eu-west-2":
            reg = euwest_region
        else:
            reg = canada_region
    else:
        region = region and boto.ec2.get_region(region,
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret)
    try:
        conn = boto.ec2.connection.EC2Connection(aws_key, aws_secret,
            region=region)
    except:
        print("Connection failed ")

    # list of (instance_name, ip_address)
    instances = get_ec2_instances(conn, name_tag, filters)
    print(instances)

    # sort by name
    instances = sorted(instances)

    # print out
    printSshConfig(instances, prefix, suffix, domain)
