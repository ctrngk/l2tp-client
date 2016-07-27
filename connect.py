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
	trialTime = 3
	while success == False and i < trialTime:
		i = i + 1
		status = False
		while status == False:
			print("starting service...")
			sh("touch /var/run/xl2tpd/l2tp-control")
			sh("rm -rf /var/run/xl2tpd/l2tp-control")
			sh("touch /var/run/xl2tpd/l2tp-control")
			time.sleep(0.5) 
			sh("service strongswan restart")
			time.sleep(0.5) 
			sh("service xl2tpd force-reload")
			time.sleep(0.8) 
			sh("service xl2tpd restart")
			time.sleep(0.8)
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
def login(waitSeconds=5):
	# need a few seconds to login 
	time.sleep(1)
	auth = r'echo "c XXX-YOUR-CONNECTION-NAME-XXX {} {}" > /var/run/xl2tpd/l2tp-control '.format(user,pwd)
	sh(auth)
	# wait for a few seconds to check auth
	print("waiting {}s for checking in...".format(waitSeconds))
	time.sleep(waitSeconds)
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
# 90 <= Total seconds of Wait
trialTimes = 6
# 90 or 120 recomanded
WaitSecondsToRetryDependOnServerResponds = 30
while i <= trialTimes:
	i = i + 1
	reconnect() # successfully ipsec up
	print("try to login with user and password")
	if login(waitSeconds=3):
		print("ppp established")
		break
	if i >= trialTimes:
		raise  Exception("\n\ncannot login with user name and password. \nunkown error, please try again\nTips: increase login waitSeconds")
	print("login did not bring up ppp. \nYour IP may be blocked for a while. Try all over again. Max time:{} Now:{}".format(trialTimes, i))
	time.sleep(WaitSecondsToRetryDependOnServerResponds)

print("ppp established, adding route...")
try:
	std, e = run_script("ifconfig ppp")
	print(std)
except:
	print("error occur when ifconfig")


time.sleep(0.5)
gateway =  getGW()

# getPTP()
i = 0
sleepSeconds = 1
trialTimes = 30
vpnServerLocalIp = False
while not vpnServerLocalIp:
	time.sleep(sleepSeconds)
	i = i + 1
	if i >= trialTimes:
		print("ppp did not bright up after {} seconds, please increase its waiting time".format(trialTimes))
		sys.exit(1)
	try:
		vpnServerLocalIp = getPTP()
	except: pass
print("P-t-P estabished")


sh("route add {} gw {}".format(ip, gateway))
print(r"route add -net default gw {}".format(vpnServerLocalIp))
sh("route add -net default gw {}".format(vpnServerLocalIp))

print("l2tp connected")
print("finished")
