import os
import sys
import subprocess
import re
import datetime
import json

configs = {} #configs that will be used in command execution
all_configs = {} #all of the configs
tags = set()
file_names = ["azure.conf", "gcp.conf"]
a_required_keys = ["name", "resource-group", "image", "location", "admin-username"] #minimum requirement for an azure vm
g_required_keys = ["name", "image", "zone", "imageproject"] #minimum requirement for a gcp vm
tag_num = 0
line_num = 0
port_num = 0

#function to validate password input
def validate_azure_password(password):
	if not 12 <= len(password) <= 123:
		return False
	
	criteria = 0
	
	#check if the password contains at least 1 lowercase character
	if re.search("[a-z]", password):
		criteria += 1

	if re.search("[A-Z]", password):
		criteria += 1

	if not re.search("[0-9]", password):
		criteria += 1

	if not re.search("[!@#$%^&*()_+=-]", password):
		criteria += 1

	#check if the criteria is met
	if criteria >= 3:
		return True
	else:
		return False

#function to validate azure configs
def azure_validation(tag):

	config = configs[tag]

	#check that all the required keys are present
	if not all(key in config for key in a_required_keys):
		print(f"Error: Insufficient information provided for '{tag}' in '{file_name}'.")
		sys.exit()

	#check if the resource group for Azure exists, if not create one
	resource_group = config.get('resource-group')
	if resource_group is not None:
		result = subprocess.check_output(f"az group exists --name {resource_group}", shell=True, text=True).strip()
		if result == 'false':
			os.system(f"az group create --name {resource_group} --location {config['location']}")
	else:
		print(f"Error: a resource-group is not provided for '{tag}' in '{file_name}'.")
		sys.exit()

	#check if there is an admin password parameter and validate
	password = config.get('admin-password')
	if password is not None:
		if not validate_azure_password(password):
			print(f"Error: Invalid admin password format for '{tag}' found in '{file_name}'.")
			sys.exit()
	
	#check if there is a disk size parameter and validate
	size = config.get("os-disk-size-gb")
	if size is not None:
		try:
			size = float(size)
			if not isinstance(size, (float)):
				print(f"Error: Invalid os disk size format for '{tag}' found in '{file_name}'.")
				sys.exit()
		except ValueError:
			print(f"Error: Invalid os disk size format for '{tag}' found in '{file_name}'.")
			sys.exit()
	
	#check if there is a disk cache parameter and validate
	cache = config.get("os-disk-size-caching")
	if cache is not None:
		if cache not in ["None", "ReadOnly", "ReadWrite"]:
			print(f"Error: Invalid option for disk cache parameter for '{tag}' found in '{file_name}'.")
			sys.exit()

#function to execute vm creation commands
def execute_command(command, file_name, vm_name):
	print()
	print("Would you like to execute the command: " + command)
	print()
	user_input = input("y/n? ('n' will exit program): ").lower()

	#execute command
	if user_input == 'y':
		try:
			output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
		except subprocess.CalledProcessError as e:
			output = e.output
		
		if file_name == "azure.conf":
			output_parsed = json.loads(output) #convert json output to a dictionary
			#format output to match the style of the gcp output
			print("{:<15} {:<30} {:<20} {:<15} {:<15} {:<10}".format("NAME", "LOCATION", "RESOURCE_GROUP", "PRIVATE_IP", "PUBLIC_IP", "STATUS"))
			print("{:<15} {:<30} {:<20} {:<15} {:<15} {:<10}".format(vm_name, output_parsed['location'], output_parsed['resourceGroup'], output_parsed['privateIpAddress'], output_parsed['publicIpAddress'], output_parsed['powerState']))
		else: #gcp
			print(output)
		print()
	
	else:
		print("Exiting program...")
		sys.exit()

#driver code
print("Processing config files...")
for file_name in file_names:
	#check if the file exists
	if not os.path.exists(file_name):
		print(f"Error: The file '{file_name}' does not exist.")
		sys.exit()

	with open(file_name, 'r') as file:
		for line in file:
			line = line.strip() #remove leading and trailing whitespace from the line

			if line.startswith('['): #new VM
				tag = line.strip('[]') #extract the tag name
				tags.add(tag) #add the tag to a set

				#validate tag name
				if file_name == "azure.conf":
					tag_num += 1
					if not (tag.startswith("azure") and tag_num < 11 and len(tag) == 7 and tag[5:].isdigit() and int(tag[5:]) == tag_num):
						print(f"Error: Invalid Azure tag format '{tag}' found in '{file_name}'")
						sys.exit()
				else:
					tag_num += 1
					if not (tag.startswith("gcp") and tag_num < 11 and len(tag) == 5 and tag[3:].isdigit() and int(tag[3:]) == tag_num):
						print(f"Error: Invalid GCP tag format '{tag}' found in '{file_name}'")
						sys.exit()

				configs[tag] = {} #add tag to the dictionary
				all_configs[tag] = {}

			else:
				line_num += 1
				all_configs[tag][line_num] = line
				key, value = line.split('=', 1) #split the line based on the '=' and store it
				key = key.strip()
				value = value.strip()

				#if a port is specified for an Azure vm config
				if file_name == "azure.conf":
					
					#process port config
					if key == "port" and configs[tag]["resource-group"] is not None:
						port_num += 1

						#create a network security group
						command = f"az network nsg create --resource-group {configs[tag]['resource-group']} --name open-port{port_num}"
						output = subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
					
						#open the port 
						command = f"az network nsg rule create --nsg-name open-port{port_num} --resource-group {configs[tag]['resource-group']} --name Allow-Web-All --priority 100 --destination-port {value}"
						output = subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
					
					#if the port config was before a resource group was found (need resource group to open port)
					elif key == "port" and configs[tag]["resource-group"] is None:
						print(f"Error: Resource group required to open port. Please indicate resource group before port for '{tag}' found in '{file_name}'")

				if file_name == "gcp.conf" and key == "port":
					port_num += 1
					command = f"gcloud compute firewall-rules create open-port{port_num} --action=ALLOW --direction=INGRESS --rules=tcp:{value}"
					output = subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

				#check conditions based on the file name
				if (file_name == "azure.conf" and key in a_required_keys or key in ["admin-password", "os-disk-size-gb", "os-disk-caching"]) or (file_name == "gcp.conf" and key in g_required_keys):
					configs[tag][key] = value  #store it in the dictionary
				
		if file_name == "azure.conf":
			for a_tag in tags:
				azure_validation(a_tag) #validate the Azure parameters

				#run the Azure vm create command based on the inputted parameters
				command = "az vm create"
				for key, value in configs[a_tag].items():
					command += f" --{key} {value}"
				execute_command(command, file_name, configs[tag]["name"])

		else:
			for g_tag in tags:
				config = configs[g_tag]  #get the configuration for the current tag
				if not all(key in config for key in g_required_keys):
					print(f"Error: Insufficient information provided for '{g_tag}' in '{file_name}'.")
					sys.exit()

				command = f"gcloud compute instances create {config['name']} --zone={config['zone']} --image-project={config['imageproject']} --image={config['image']}"
				execute_command(command, file_name, configs[tag]["name"])

	#reset before processing the next file
	tags.clear()
	tag_num = 0
	line_num = 0
	port_num = 0

date_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") 
out_file_name = "VMcreation_" + date_time

#retrieve the system admin name
admin = os.environ.get('USER') #Unix-like systems
if not admin:
	admin = os.environ.get('USERNAME') #Windows

#create and populate documentation file
with open(out_file_name, 'a') as out_file:
	out_file.write(date_time)
	out_file.write("\n" + admin)
	for tag, configs in all_configs.items():
		print()
		out_file.write(f"\n[{tag}]")
		for key, value in configs.items():
			out_file.write(f"\n{value}")

#move the azure.conf file
out_file_name = "azure_" + date_time
with open("azure.conf", 'r') as file:
	with open(out_file_name, "w") as out_file:
		out_file.write(file.read())

#move the gcp.conf file
out_file_name = "gcp_" + date_time
with open("gcp.conf", 'r') as file:
	with open(out_file_name, "w") as out_file:
		out_file.write(file.read())
