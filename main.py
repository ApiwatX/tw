"""
	by pp021#9092
	 latest update 10/1/2022 skid/resellได้
"""

import websocket, json, time, zlib, os, threading, cloudscraper, yaml, requests, re, ctypes, traceback, datetime, sys
from opcodes import *

# preload
cfscraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "desktop": True}, delay=10)
cfscraper.get("https://gift.truemoney.com/campaign/vouchers/asdsad/redeem")

# get current client build
js = requests.get("https://canary.discord.com/assets/" + str(re.compile(r"([a-zA-z0-9]+)\.js", re.I).findall(requests.get("https://discord.com/app").text)[-2]) + ".js").text
clientBuild = int(re.compile(r"\", Build Number: \"\)\.concat\(\"(.*)\",\", Version Hash:").findall(js)[0])
del js

# --------------------------------------------------------------------------------------

twvQueue = []
codeCache = []
clients = []
blacklist = {}
config = None
incoming_balance = 0.0
shutdown = False

# --------------------------------------------------------------------------------------

def acceptThread():
	while 1:
		if len(twvQueue) > 0:
			#### 0 = message data, 1 = account id, 2 = token
			raw = twvQueue.pop(0)
			#log(raw[0], raw[1])

			userid = raw[0]["author"]["id"]
			if userid in blacklist and blacklist[userid] >= config["max-invaild"]:
				continue

			regex = re.compile(r"https:\/\/gift\.truemoney\.com\/campaign\/\?v=(.{18})", re.UNICODE|re.MULTILINE)
			for code in regex.findall(str(raw[0])):
				if code in codeCache:
					continue

				response = cfscraper.post("https://gift.truemoney.com/campaign/vouchers/" + str(code) + "/redeem", json={"mobile": config["phone"].strip(), "voucher_hash": code})
				codeCache.append(code)
				try:
					json = response.json()
					status = json["status"]["code"]
					if status == "SUCCESS":
						global incoming_balance
						amount = float(json["data"]["my_ticket"]["amount_baht"].replace(",", ""))
						incoming_balance += amount
						log(raw[1], "Received " + str(amount) + "thb gift from " + json["data"]["owner_profile"]["full_name"])
						if "guild_id" in raw[0]:
							sendWebhook(0x2ecc70, "Gift Envelope Sniped\namount: " + str(amount) + " thb\nguild: " + getGuildNameById(raw[2], raw[0]["guild_id"]) + "\nfrom: " + raw[0]["author"]["username"] + "#" + raw[0]["author"]["discriminator"] + "\ncreated by: " + json["data"]["owner_profile"]["full_name"])
						else:
							sendWebhook(0x2ecc70, "Gift Envelope Sniped\namount: " + str(amount) + " thb\nguild: (direct message)\nfrom: " + raw[0]["author"]["username"] + "#" + raw[0]["author"]["discriminator"] + "\ncreated by: " + json["data"]["owner_profile"]["full_name"])
					elif status == "VOUCHER_OUT_OF_STOCK":
						lastUsed = json["data"]["tickets"][0]
						lastRedeem = ((round(time.time() * 1000)) - lastUsed["update_date"]) / 60000
						# 10 min
						if lastRedeem < 10:
							if "guild_id" in raw[0]:
								sendWebhook(0x2ecc70, "You missed " + str(lastUsed["amount_baht"]) + " thb\nguild: " + getGuildNameById(raw[2], raw[0]["guild_id"]) + "\nfrom: " + raw[0]["author"]["username"] + "#" + raw[0]["author"]["discriminator"] + "\ncreated by: " + json["data"]["owner_profile"]["full_name"])
							else:
								sendWebhook(0x2ecc70, "You missed " + str(lastUsed["amount_baht"]) + " thb\nguild: (direct message)\nfrom: " + raw[0]["author"]["username"] + "#" + raw[0]["author"]["discriminator"] + "\ncreated by: " + json["data"]["owner_profile"]["full_name"])
							log(raw[1], "Missed " + str(lastUsed["amount_baht"]) + " thb gift from " + json["data"]["owner_profile"]["full_name"])
					elif status == "VOUCHER_NOT_FOUND":
						if not userid in blacklist: blacklist[userid] = 0

						blacklist[userid] += 1
						if blacklist[userid] >= config["max-invaild"]: log(raw[1], "blacklist " + str(userid) + " for sending too many invaild gift")
					elif status == "VOUCHER_EXPIRED":
						if not userid in blacklist: blacklist[userid] = 0

						blacklist[userid] += 1
						if blacklist[userid] >= config["max-invaild"]: log(raw[1], "blacklist " + str(userid) + " for sending too many invaild gift")
					elif status == "CANNOT_GET_OWN_VOUCHER":
						log(raw[1], "Cannot reddem own gift")
						pass
					else:
						log(raw[1], "Unknown status response from tw-api (" + status + ")")
				except BaseException as e:
					log(raw[1], "Error while redeem twv / " + code)
					traceback.print_exc()

		time.sleep(0.01)

def titleThread():
	while 1:
		ready = 0
		for client in clients:
			if client.ready:
				ready += 1
		ctypes.windll.kernel32.SetConsoleTitleW("Ready client: " + str(ready) + "  |  Balance: " + str(incoming_balance))
		time.sleep(1)

# --------------------------------------------------------------------------------------

class GatewaySocket:
	compress=False; buffer = bytearray(); accId=-1; kpThread=False; token=None; tokenInvaild=False; interval=None; session_id=None; seq=0; ready=False; connected=False; ws=False; resumable=False; decompressor=None; lastErr=None

	def __init__(self, token, id):
		self.ws = self.createWebsocket()
		self.token = token
		self.accId = id

		def ct1():
			self.run()
		threading._start_new_thread(ct1, ())
		

	def createWebsocket(self):
		def ct1(ws):
			self.onOpen(ws)
		def ct2(ws, data):
			a = {}
			try:
				self.onData(ws, data, a)
			except BaseException as e:
				if isinstance(e, zlib.error):
					self.compress = False
					self.close("decompresssion failed bruh", True)
					self.ws = self.createWebsocket()
					return

				log(self.accId, "error throw while processing event " + str(opcodeToClean(a[0])))
				traceback.print_exc()
		def ct3(ws, message):
			self.onError(ws, message)
		def ct4(ws, code, message):
			self.onClose(ws, code, message)
		return websocket.WebSocketApp("wss://gateway.discord.gg/?encoding=json&v=9" + ("&compress=zlib-stream" if self.compress else ""),
			header={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0", "Sec-WebSocket-Extensions": "permessage-deflate", "Accept-Encoding": "gzip, deflate, br"},
			on_open=ct1,
			on_message=ct2,
			on_error=ct3,
			on_close=ct4,
		)

	def onOpen(self, ws):
		log(self.accId, "ws connected")
		self.connected = True

		if not self.resumable:
			auth = {
				"op": IDENTIFY,
				"d": {
					"token": self.token,
					"capabilities": 4093,
					"properties": {
						"os": "Windows",
						"browser": "Firefox",
						"device": "",
						"system_locale": "en-US",
						"browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0",
						"browser_version": "111.0",
						"os_version": "10",
						"referrer": "",
						"referrer_domain": "",
						"referrer_current": "",
						"referring_domain_current": "",
						"release_channel": "canary",
						"client_build_number": clientBuild,
						"client_event_source": None
					},
					"presence": {
						"status": "invisible", # :fire:
						"since": 0,
						"activities": [],
						"afk": False
					},
					"compress": False,
					"client_state":{
						"guild_versions": {},
						"highest_last_message_id": "0",
						"read_state_version": 0,
						"user_guild_settings_version": -1,
						"user_settings_version": -1,
						"private_channels_version": "0",
						"api_code_version": 0
					}
				}
			}
			self.send(auth)
		else:
			self.resumable = False
			self.send({"op": RESUME, "d": {"token": self.token, "session_id": self.session_id, "seq": self.seq - 1}})

	def onData(self, ws, data, thing):
		if self.compress:
			self.buffer.extend(data)
			if len(data) < 4 or data[-4:] != b"\x00\x00\xff\xff":
				return None

			data = self.decompressor.decompress(self.buffer)
			self.buffer = bytearray()

			data = json.loads(data.decode("UTF-8"))
		else:
			data = json.loads(data)
		#print("data recev " + str(data))
		opcode = data["op"]
		thing[0] = opcode
		#print(data)
		# resume thing
		if opcode != HEARTBEAT_ACK:
			self.seq += 1

		# keepalive (heartbeat)
		if opcode == HELLO:
			self.interval = data["d"]["heartbeat_interval"] / 1000
			#threading.Thread(target=self.keepalive, daemon=True).start()
			threading._start_new_thread(self.keepalive, ())

		if opcode == HEARTBEAT:
			self.send({"op": HEARTBEAT, "d": self.seq})

		# TODO: fix this w connect
		if opcode == INVALID_SESSION:
			log(self.accId, "invaild session")
			self.resumable = False
			self.seq = 0
			self.close("Invaild session")

		if opcode == RECONNECT:
			self.close("Server force reconnect")

		if data["t"] == "READY":
			self.session_id = data["d"]["session_id"]
			log(self.accId, "got session")

		if data["t"] == "READY_SUPPLEMENTAL":
			self.ready = True
			self.send({"op": VOICE_STATE_UPDATE, "d": {"guild_id": None, "channel_id": None, "self_mute": True, "self_deaf": False, "self_video": False}})
			log(self.accId, "ready")

		if data["t"] == "MESSAGE_CREATE":
			author = data["d"]["author"]

			if "https://gift.truemoney.com/campaign/" in str(data["d"]):
				twvQueue.append([data["d"], self.accId, self.token])



	def onError(self, ws, errMessage):
		log(self.accId, "Error " + str(errMessage))
		lastErr = errMessage

	def onClose(self, ws, code, message):
		log(self.accId, "Closed " + str(code) + " " + str(message))
		self.connected = False
		self.ready = False

		if code:
			if not (4000 < code <= 4010):
				self.resumable = True
				self.lastError = "reconnecting - resume"
				return
			if code == 4004:
				self.tokenInvaild = True
				return
			if code in (1000, 1001, 1006):
				self.lastError = "uh idk why it closed / " + message
				return
		elif code == None and message == None:
			self.lastErr = "ctrl + c?"

	def keepalive(self):
		if self.kpThread: return

		while self.connected:
			if self.interval == None: self.interval = 41.25
			time.sleep(self.interval)
			#print("keepalive sent " + str(self.interval))

			if not self.connected: break
			self.send({"op": HEARTBEAT,"d": self.seq})

		self.kpThread = False

	def run(self):
		while 1:
			try:
				self.decompressor = zlib.decompressobj()
				self.ws.run_forever(ping_interval=10, ping_timeout=5)

				if self.lastErr != None:
					if isinstance(self.lastErr, BaseException):
						raise self.lastErr
					raise Exception("Something went wrong... (" + str(self.lastErr) + ")")
				if self.tokenInvaild:
					log(self.accId, "Invaild token")
					break
				raise Exception("uh idk crashed?")
			except BaseException as e:
				self.lastErr = None
				if isinstance(e, KeyboardInterrupt):
					sys.exit(0)

				log(self.accId, str(e))
				time.sleep(4)
				if shutdown: break

	def send(self, data):
		self.ws.send(json.dumps(data))

	def close(self, reason="", reset=False):
		self.connected = False
		self.ready = False
		self.lastErr = "manually close, " + reason
		if reset:
			self.resumable = False
			self.seq = 0
		self.ws.close()

# --------------------------------------------------------------------------------------

def log(id, message):
	print("  [" + str(id) + "] - " + str(message))

def setPriority():
	if not ctypes.windll.shell32.IsUserAnAdmin(): return None

	import subprocess
	subprocess.Popen("wmic process where processid=" + str(os.getpid()) + " call setpriority high", creationflags=0x00000200|0x00000008)
	del subprocess, sys.modules["subprocess"]

def sendWebhook(color, message):
	data = {
		"content": None,
		"embeds": [{
			"description": "```java\n" + message + "\n```",
			"color": color,
			"footer": { "text": datetime.datetime.today().strftime("%A") },
			"timestamp": datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
		}],
		"username": "Rxd",
		"avatar_url": "https://cdn.discordapp.com/attachments/721713679216672838/954751652181717032/old_pfp.png"
	}

	requests.post(config["log-webhook"], json=data)

def getGuildNameById(token, id):
	try:
		return requests.get("https://discord.com/api/v9/guilds/" + str(id), headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0", "authorization": token, "x-super-properties": base64.b64encode(f"""{"os":"Windows","browser":"Firefox","device":"","system_locale":"en-US","browser_user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0","browser_version":"111.0","os_version":"10","referrer":"","referring_domain":"","referrer_current":"","referring_domain_current":"","release_channel":"ptb","client_build_number":{clientBuild},"client_event_source":null}""".encode())}).json()["name"]
	except:
		return "Unknown"

def initConfig():
	if not os.path.isfile("settings.yml"):
		print("  settings file not exits.")
		os.system("timeout 3 > nul")
		sys.exit(1)

	try:
		cfg = open("settings.yml", "r", encoding="utf-8")
		global config
		config = yaml.load(cfg, Loader=yaml.FullLoader)
		cfg.close()
	except Exception as e:
		print("  invaild yaml syntax :(\n" + str(e))
		os.system("timeout 3 > nul")
		sys.exit(1)

	if len(config["phone"]) != 10 or not config["phone"].isnumeric():
		print("  invaild phone number")
		os.system("timeout 3 > nul")
		sys.exit(1)

	if not config["log-webhook"].startswith("http") or requests.get(config["log-webhook"]).status_code != 200:
		print("  invaild webhook url")
		os.system("timeout 3 > nul")
		sys.exit(1)

def ct1(token, id):
	clients.append(GatewaySocket(token, id))

if __name__ == "__main__":
	initConfig()
	setPriority()

	threading._start_new_thread(acceptThread, ())
	threading._start_new_thread(titleThread, ())

	os.system("cls")

	if not os.path.isfile("tokens.txt"):
		print("  tokens.txt not exits.")
		os.system("timeout 3 > nul")
		sys.exit(1)

	f = open("tokens.txt")
	accounts = f.read().split("\n")
	f.close()



	for i, token in enumerate(accounts):
		threading._start_new_thread(ct1, (token, i+1, ))
		time.sleep(0.17)

print("\033[?25l", end="")

# lock
while 1:
	try:
		time.sleep(1)
	except:
		print("\033[?25h", end="")
		shutdown = True
		for client in clients:
			client.close()

		time.sleep(5)
		sys.exit(0)