A fully distributed [MQTT](http://mqtt.org/) broker proof-of-concept, based on  [Mosquitto](http://mosquitto.org/) and [Twister](http://twister.net.co/).
---
# Motivation

See [here](http://torlus.github.io/2014/05/08/mqtt-dht/). Now, let's get started.

# Disclaimer

It's only a proof-of-concept, and uses Twister network for illustration purposes,
as it provides all the required features. But please, please, don't bother the
users of this service. Thank you.

# Installation

Instructions are available for Linux only, for now. Sorry about that.
Note that as this project is only a single Python script, the issues you may
encounter are more likely to come from somewhere else. :)

Assuming you'll have everything installed into your $HOME:

- You'll need a working **Python 3** installation.
- Grab the latest **Mosquitto** source from [the official repository](https://bitbucket.org/oojah/mosquitto/), and compile it.
Don't run "make install" as it is not required.
- Grab the latest **Twister** source (twister-core) from [GitHub](https://github.com/miguelfreitas/twister-core), and compile it. That's
often a bit trickier, but YMMV. Again, there is no need to run "make install".
- Clone this repository.

You should end up with three directories: "mosquitto", "twister-core" and
"mosquitto-twister", all located under your $HOME.

Now run:
```
./twister-core/src/twisterd
```

and follow the instructions. Use the recommended defaults. Now you will have
to create two users. I created **mqtt_alice** and **mqtt_bob** on purpose, but
obviously, you can't use them. Use your imagination and create two different users.
Follow the instructions [here](http://twister.net.co/?page_id=58). Basically, all
yo have to do (twice) is:
```
./twisterd createwalletuser myname
./twisterd sendnewusertransaction myname
./twisterd newpostmsg myname 1 "hello world"
```
Please note that you might have to wait a bit before the third command actually works,
as it may take some time for your username to be validated at the blockchain level.

Now install the required Python libraries:
```
pip install -e ../mosquitto/lib/python
pip install git+https://github.com/jgarzik/python-bitcoinrpc.git
```
and you should be ready to go.

# Running the software

Here is the parts involved, from end-to-end:
- A first **MQTT client** (1), that will pulish a message, using...
- A first **MQTT broker** (2), to which will be also connected...
- A first instance of the **mosquitto-twister bridge** (3), associated to the
first Twister user, that will relay the message through the Twister network through...
- A single instance of the **Twister daemon** (4), assuming you're using one single box.
If you want to test with two boxes, you'll have to run one instance per box.
The daemon is responsible for relaying the messages of the network to...
- A second instance of the **mosquitto-twister bridge** (5), associated to the
second Twister user, connected to...
- A second **MQTT broker** (6), that will relay messages to...
- A second **MQTT client** (7), that subscribed to the MQTT topic the message belongs to.

You'll have to run the involved parts in this order: (4) then (2),(6) then (3),(5)
then (7) then (1) at the very end. Phew!

You'll end up running (in a different shell per command):
```
cd $HOME; ./twister-core/src/twisterd
cd $HOME/mosquitto; ./src/mosquitto -p 1883
cd $HOME/mosquitto; ./src/mosquitto -p 2883
cd $HOME/mosquitto-twister; python main.py alice.json
cd $HOME/mosquitto-twister; python main.py bob.json
cd $HOME/mosquitto; LD_LIBRARY_PATH=./lib ./client/mosquitto_sub -p 2883 -t doors/\#
cd $HOME/mosquitto; LD_LIBRARY_PATH=./lib ./client/mosquitto_pub -t doors/1 -m empty
```

Here are the expected output of the first bridge:
```
Checking user status for [mqtt_alice]...
Checking following list...
Expecting at least: mqtt_alice, mqtt_bob
Got: mqtt_alice, mqtt_bob, torlus
Checking subscriptions...
Got: fridges/#, earrings/#
Getting latest public posts...
Getting latest direct messages...
MQTT: Connected successfully.
MQTT: Message received.
Sending direct message to mqtt_bob:{"topic": "doors/1", "payload": "ZW1wdHk=", "qos": 0}
Done.
```

And here what you should expect from the second bridge:
```
Checking user status for [mqtt_bob]...
Checking following list...
Expecting at least: mqtt_bob, mqtt_alice
Got: mqtt_alice, mqtt_bob
Checking subscriptions...
Got: doors/#
Getting latest public posts...
Getting latest direct messages...
MQTT: Connected successfully.
match(sub): doors/#:sensors/temperature/sensor1
match(sub): doors/#:doors/1
b'empty'
MQTT: Message 2 published.
```

# Details

Coming soon...

# Acknowledgments

Developers working on Mosquitto, Twister, Bittorrent, Bitcoin.

Juliusz Chroboczek for his DHT code.

And to all the people fighting against "control freaks".

---
Gregory Estrade
