import sys, json, time, base64, re
import paho.mqtt.client as mqtt
from bitcoinrpc.authproxy import AuthServiceProxy 

################################################################################
# Configuration
################################################################################

if len(sys.argv) <= 1:
	print("usage: " + sys.argv[0] + " <config_file>")
	exit(-1)

config = json.loads(open(sys.argv[1]).read())

# Twister RPC configuration
twister_url = config.get('twister') or "http://user:pwd@127.0.0.1:28332" 
username = config.get('username')
following = config.get('following') or [username]
subscriptions = config.get('subscriptions') or []
publications = config.get('publications') or []
forwards = config.get('forwards') or []

if not username in following:
	following = [username] + following

# Mosquitto client library configuration
mosquitto_address = config.get('mosquitto') or "127.0.0.1:1883"
mosquitto_host, mosquitto_port = mosquitto_address.split(":")

################################################################################
# Twister setup
################################################################################
twister = AuthServiceProxy(twister_url)
all_subs = {}

#print(twister.help())
print("Checking user status for ["+username+"]...")
try:
	twister.follow(username, [username])
except:
	print("Invalid/unknown username: " + username)
	exit(-1)

print("Checking following list...")
print("Expecting at least: " + ', '.join(following))
while True:
	twister_following = twister.getfollowing(username) 
	print("Got: " + ', '.join(twister_following))
	if not set(following) <= set(twister_following):
		print("Updating following list...")
		twister.follow(username, following)
		time.sleep(5)
	else:
		break

print("Checking subscriptions...")
while True:
	data = twister.dhtget(username, "profile", "s")
	try:
		twister_subscriptions = data[0]["p"]["v"]["mqtt_topics"]
	except:
		twister_subscriptions = []
	print("Got: " + ', '.join(twister_subscriptions))
	if not set(subscriptions) <= set(twister_subscriptions):
		print("Updating subscriptions...")
		try:
			seq = data[0]["p"]["seq"] + 1
		except:
			seq = 1
		rc = twister.dhtput(username, "profile", "s", {"mqtt_topics":subscriptions}, username, seq)
		time.sleep(5)
	else:
		break

latest_posts = {}
latest_dms = {}

print("Getting latest public posts...")
for fellow in following:
	posts = twister.getposts(1, [{"username":fellow}], 3)
	try:
		last = posts[0]["userpost"]["k"]
	except:
		last = 0
	latest_posts[fellow] = last

print("Getting latest direct messages...")
for fellow in following:
	dms = twister.getdirectmsgs(fellow, 1, [{"username":username}])
	try:
		last = dms[username][0]["id"]
	except:
		last = 0
	latest_dms[fellow] = last
	#latest_dms[fellow] = 0


################################################################################
# Mosquitto MQTT client initialization
################################################################################
# Mosquitto client library callbacks
def on_connect(mosq, obj, rc):
    if rc == 0:
        print("MQTT: Connected successfully.")

def on_disconnect(mosq, obj, rc):
    print("MQTT: Disconnected.")

def on_publish(mosq, obj, mid):
    print("MQTT: Message "+str(mid)+" published.")
    pass

def on_message(mosq, obj, msg):
	print("MQTT: Message received." + str(msg.mid))
	global all_subs
	msg = { "topic": msg.topic, "qos": msg.qos, 
		"payload": str(base64.b64encode(msg.payload),'ascii') }
	for ward in forwards:
		fw_topic = ward.get("from")
		if not topic_match(fw_topic, msg["topic"]):
			continue
		fw_type = ward.get("type") or "public"
		if fw_type == "public":
			print("Publishing to public timeline:"+json.dumps(msg))
			twister.newpostmsg(username, latest_posts[username] + 1, 
				json.dumps(msg))
			print("Done.")
		else:
			fw_rcpts = ward.get("to") or []
			for rcpt in fw_rcpts:
				subs = all_subs.get(rcpt) or []
				for sub in subs:
					#print("match(pub): " + sub + ":" + msg["topic"])
					if not topic_match(sub, msg["topic"]):
						continue
					print("Sending direct message to "+rcpt+":"+json.dumps(msg))
					twister.newdirectmsg(username, latest_dms[username] + 1, 
						rcpt, json.dumps(msg))
					print("Done.")

def on_subscribe(mosq, obj, mid, qos_list):
    #print("Subscribe with mid "+str(mid)+" received.")
    pass

def on_unsubscribe(mosq, obj, mid):
    #print("Unsubscribe with mid "+str(mid)+" received.")
    pass

client = mqtt.Client(username)

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish
client.on_message = on_message
client.on_subscribe = on_subscribe
client.on_unsubscribe = on_unsubscribe

client.connect(mosquitto_host, int(mosquitto_port))

for topic in publications:
	client.subscribe(topic)

################################################################################
################################################################################
# Main loop
################################################################################
################################################################################

# Ahem...
def topic_match(pattern, value):
	pattern = pattern.replace("#",".*")
	pattern = pattern.replace("+","[^/]*")
	prog = re.compile(pattern)
	return prog.match(value)

def handle_message(mosq, user, msg):
	global subscriptions
	for sub in subscriptions:
		#print("match(sub): " + sub + ":" + msg["topic"])
		if not topic_match(sub, msg["topic"]):
			continue
		#print(base64.b64decode(msg["payload"]))
		client.publish(msg["topic"], bytearray(base64.b64decode(msg["payload"])), msg["qos"])

while(client.loop() == 0):
	for fellow in following:
		# Update posts
		posts = twister.getposts(100, [{"username":fellow, "since_id":latest_posts[fellow]}], 3)
		try:
			last = posts[0]["userpost"]["k"]
		except:
			last = latest_posts[fellow]
		latest_posts[fellow] = last
		for post in posts:
			try:
				sender = post["userpost"]["n"]
			except:
				sender = username
			if not sender == username:
				try:
					handle_message(client, fellow, json.loads(post["userpost"]["msg"]))
				except:
					print("Error while processing post.")

		# Update direct messages
		dms = twister.getdirectmsgs(fellow, 100, [{"username":username, "since_id":latest_dms[fellow]}])
		dms = dms.get(username) or []
		try:
			last = dms[0]["id"]
		except:
			last = latest_dms[fellow]
		latest_dms[fellow] = last
		#print("last:" + fellow + ":"+ str(latest_dms[fellow]))
		for dm in dms:
			try:
				handle_message(client, fellow, json.loads(dm["text"]))
			except:
				print("Error while processing direct message.")

		# Update subscriptions
		data = twister.dhtget(fellow, "profile", "s")
		try:
			all_subs[fellow] = data[0]["p"]["v"]["mqtt_topics"]
		except:
			all_subs[fellow] = []

client.disconnect()

exit(0)


