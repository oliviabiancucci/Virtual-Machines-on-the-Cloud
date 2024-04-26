#
# Example code to create an EC2 instance
#
import boto3

#
# Connect to the ec2 resource
# To run this example on your system: you might not be able to use the CA zone - use
# a the zone that your account is in.
#
ec2 = boto3.resource('ec2','ca-central-1')

#
# Launch one Amazon Linux AMI 2018.03.0 (HVM), SSD Volume Type
# To run this example on your system: you must create a KeyName (not use the one here)
# For information about keys see: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html
#
instance = ec2.create_instances(
   ImageId='ami-0c00c714c7f84b49d', # AWS Amazon Linux 2023 AMI 2023.3.20240122.0 x86_64 HVM kernel-6.1
   MinCount=1,                      # MinCount: This species the minimum number of instances to launch. This is a mandatory parameter.
   MaxCount=1,                      # MaxCount: This species the maximum number of instances to launch. This is a mandatory parameter.
   InstanceType='t2.micro',    # choose one with free tier eligible
   KeyName='4010EC2-01-key'     # can use existing one
)[0]

#
# Wait for the instance to be created...
# This code is using a routine that waits on the instance to be running
# and then reloads information about the instance
#
instance.wait_until_running()
instance.reload()

#
# show_instances will list all of your VMs of a given status
#
def show_instances(status):
   instances = ec2.instances.filter(
      Filters=[{'Name': 'instance-state-name','Values': [status]}])
   for inst in instances:
      print(inst.id, inst.instance_type, inst.image_id, inst.public_ip_address)

#
# List all of your running EC2 instances - you should see the new VM
#
show_instances('running')


