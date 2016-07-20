#!/usr/bin/env python3
import sys
import os
def sh(script):
    os.system("bash -c '%s'" % script)

def run_script(script, stdin=None):
    """Returns (stdout, stderr), raises error on non-zero return code"""
    import subprocess
    # Note: by using a list here (['bash', ...]) you avoid quoting issues, as the
    # arguments are passed in exactly this order (spaces, quotes, and newlines won't
    # cause problems):
    proc = subprocess.Popen(['bash', '-c', script],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    stdout = stdout.decode('utf-8', 'ignore')

    if proc.returncode:
        raise ScriptException(proc.returncode, stdout, stderr, script)
    return stdout, stderr

class ScriptException(Exception):
    def __init__(self, returncode, stdout, stderr, script):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        Exception.__init__('Error in script')


from configparser import ConfigParser
parser = ConfigParser()
parser.read('config.ini')
ip = parser.get('vpn_l2tp','serverip')
user = parser.get('vpn_l2tp','username')
pwd = parser.get('vpn_l2tp','password')
psk = parser.get('vpn_l2tp','sharedpsk')

sh("cp ipsec.conf /etc/ipsec.conf")
sh(r'sed -i "s/ipip/{}/g" /etc/ipsec.conf'.format(ip))

sh("cp ipsec.secrets /etc/ipsec.secrets")
sh(r'echo ": PSK \"{}\"" > /etc/ipsec.secrets'.format(psk))

sh("cp xl2tpd.conf /etc/xl2tpd/xl2tpd.conf")
sh(r'sed -i "s/ipip/{}/g" /etc/xl2tpd/xl2tpd.conf'.format(ip))

sh("cp options.l2tpd.client /etc/ppp/options.l2tpd.client")

sh("mkdir -p /var/run/xl2tpd")

import time

def checkRunning():
	try:
		strongswan, err = run_script("service strongswan status | grep Active")
		xl2tpd, err = run_script("service xl2tpd status | grep Active")
	except:
		return False
	if "running" in strongswan and "running" in xl2tpd:
		return True
	return False

def reconnect():
	success = False
	i = 0
	trialTime = 100
	while success == False and i < trialTime:
		i = i + 1
		status = False
		while status == False:
			print("starting service...")
			sh("touch /var/run/xl2tpd/l2tp-control")
			sh("rm -rf /var/run/xl2tpd/l2tp-control")
			sh("touch /var/run/xl2tpd/l2tp-control")
			time.sleep(0.2) 
			sh("service strongswan restart")
			time.sleep(0.2) 
			sh("service xl2tpd force-reload")
			time.sleep(0.2) 
			sh("service xl2tpd restart")
			time.sleep(0.2)
			status = checkRunning()
			
		print("ipsec up......")
		try: stdout, stderror = run_script(r"ipsec down XXX-YOUR-CONNECTION-NAME-XXX")
		except: pass
		try: stdout, stderror = run_script(r"ipsec up XXX-YOUR-CONNECTION-NAME-XXX")
		except: pass
		if "established successfully" in stdout:
			# success = True
			print("ipsec up established successfully")
			return True
		else:
			success = False
			print("ipsec up failed, try again{}".format(i))
		if success == False and i >= trialTime:
			raise Exception("\n\nip address failed, try again")
def login():
	# need a few seconds to login 
	auth = r'echo "c XXX-YOUR-CONNECTION-NAME-XXX {} {}" > /var/run/xl2tpd/l2tp-control '.format(user,pwd)
	sh(auth)
	i = 0
	time.sleep(6)
	# wait for a few seconds to check
	while i < 2:
		time.sleep(1)
		i = i + 1
		print("elaspTime: {}s".format(i))
		try:
			ppp, stderr = run_script(r"ip a | grep ppp")
			return True
		except: pass
	return False

def getGW():
	stdout, stderror = run_script(r"route -n | grep UG | awk '{print $2}' | sort | uniq")
	return stdout
def getPTP():
	try: stdout, stderror = run_script(r'ip a | grep -o -P "(?<=peer ).+(?=\/)" ')
	except: return False
	return stdout

i = 0
loginTime = 20
while i < loginTime:
	i = i + 1
	reconnect()
	print("try to login")
	if login():
		print("ppp established")
		break
	if i >= loginTime:
		raise  Exception("\n\nunkown error, please try again")
	print("login did not bring up ppp. try again")

print("ppp established, adding route...")

time.sleep(0.5)
gateway =  getGW()

vpnServerLocalIp = False
elasp = 0
while not vpnServerLocalIp:
	time.sleep(1)
	elasp += 1
	print("elasp {}s".format(elasp))
	vpnServerLocalIp = getPTP()
	if elasp > 30:
		print("ppp shut down unexpectedly, please try again")
		sys.exit(1)

sh("route add {} gw {}".format(ip, gateway))
sh("route add -net default gw {}".format(vpnServerLocalIp))

print("l2tp connected")
