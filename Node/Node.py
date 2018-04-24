import socket
import queue
import threading
import fcntl, os
import errno
import sys
import select
import tty
import termios

class Node(threading.Thread):

	def __init__(self, TCP_IP, TCP_PORT, IS_HA, BUFFER_SIZE=1024):
		super().__init__()
		self.routerIP = TCP_IP
		self.routerPort = TCP_PORT
		self.ip = ""
		self.bufferSize = BUFFER_SIZE
		#self.pktQueue = queue.Queue()
		self.responseQueue = queue.Queue()
		self.conn = self.setConnection(self.routerIP, self.routerPort)
		self.isHomeAgent = IS_HA
		self.firstStart = True
		self.regNodes = []
		self.start()

	def run(self):
		print("Mobile Node Starting")
		if self.isHomeAgent:
			threading.Thread(target=self.homeAgentWorker).start()
		else:
			threading.Thread(target=self.nodeWorker).start()
		threading.Thread(target=self.responseWorker).start()
		#threading.Thread(target=self.pktWorker).start()

	def nodeWorker(self):
		"""
		:Description:	Thread that handles simple node protocol
		:Return:		void
		"""
		msg = None
		response = None
		while msg != "exit":
			# Register with router on first start
			if self.firstStart:
				msg = "REGISTER"
				threading.Thread(target=self.sendWorker, args=(msg,)).start()
				# response = self.register(msg)
				# print("Router Response: " + response)
				self.firstStart = False
			else:
				# Split message
				tokens = msg.split(' ')
				tokensLen = len(tokens)
				assert tokensLen > 0
				if tokens[0] == "MOVE":
					# Connect to new router on a different network
					assert tokensLen == 3
					newIP = tokens[1]
					newPort = tokens[2]
					self.closeConnection()
					self.conn = self.setConnection(newIP, int(newPort))
				else: # Otherwise, start a new messaging thread
					threading.Thread(target=self.sendWorker, args=(msg,)).start()
			msg = str(input("Enter a message or enter exit to quit: "))
		self.closeConnection()

	def homeAgentWorker(self):
		"""
		:Description:	Thread that handles the home agent protocol
		:Return:		void
		"""
		msg = ""
		response = ""
		rdata = []
		rDataLen = 0
		done = False
		while True:
			# Register with router on first start
			if self.firstStart:
				msg = "REGISTER HA"
				response = self.register(msg)
				print("Router Response: " + response)
				self.firstStart = False
			else:
				# Wait for a packet
				print("Waiting for packet")
				response = self.conn.recv(self.bufferSize).decode()
				print("Packet received: " + response)
				#self.pktQueue.put(response, block=True)	# Place response in packet queue
				rdata = response.split(' ')
				assert len(rdata) == 3
				src = rdata[0]
				dst = rdata[1]
				payload = rdata[2]
				if dst == self.ip:
					print("Message received from " + src + ": " + response)
					# Add node to registered nodes list if it sent a register message
					if payload == "REGISTER":
						print("Registering " + src)
						self.regNodes.append(src)
						print(src + " Registered")
					# Send an ACK back to the node
					msg = self.ip + " " + src + " " + "ACK"
					self.conn.send(msg.encode())
		self.closeConnection()

	def sendWorker(self, msg):
		print("Sending message: " + msg)
		#msg = " " + msg
		self.conn.send(msg.encode())
		# response = self.conn.recv(self.bufferSize).decode()
		print("Message sent")
		#self.responseQueue.put((response, msg), block=True)

	def responseWorker(self):
		while True:
			response = self.conn.recv(self.bufferSize).decode()
			print("Processing Response: " + response)
			# response, msg = self.responseQueue.get(block=True)
			# data = response.split(' ')
			# print("\n\nProcessing Response: " + response)
			# if msg == "REGISTER":
			# 	assert len(data) == 4
			# 	self.ip = data[3]
			# 	print("New IP address: " + self.ip)
			# else:
			# 	src = data[0]
			# 	dst = data[1]
			# 	payload = data[2]
			# 	msg = self.ip + " " + src + " ACK"
			# 	self.conn.send(msg.encode())

	def pktWorker(self):
		"""
		:Description:	Thread that processes received packets
		:Return: None
		"""
		pkt = self.pktQueue.get(block=True)
		print("Packet Worker Packet: " + pkt)


	def setConnection(self, newIP, newPort):
		"""
		:Description:	Sets up a new router connection
		:Param newIP: 	The IP address of the new router
		:Param newPort: The port of the new router
		:Return:		The new socket descriptor for the new router connection
		"""
		print("[+] Setting up new router connection")
		conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		conn.connect((newIP, newPort))
		self.routerIP = newIP
		self.routerPort = newPort
		print("[+] Now connected to router at IP: " + str(newIP) + ", Port: " + str(newPort))
		return conn

	def closeConnection(self):
		"""
		:Description:	Closes the current socket connection to the current router
		:Return:		void
		"""
		if self.conn:
			self.conn.close
			self.conn = None

	def isConnectionOpen(self):
		"""
		:Description:	Checks if router connection exists
		:Return: True if it exists, False if not
		"""
		if self.conn:
			return True
		else:
			return False

	def isData(self):
		return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

	def isIP(self, ip):
		"""
		Check if passed-in IP is a valid IP
		:param ip: string representation of IP address
		:return: boolean
		"""
		splitIP = ip.split('.')
		if (len(splitIP) != 4):
			return False
		for octet in splitIP:
			if (not octet.isdigit()):
				return False
			elif (int(octet) < 0 or int(octet) > 255):
				return False
			return True

	def register(self, msg):
		"""
		:Description:	Registers node with router
		:Param msg:		Registration msg
		:Return:		Response from router
		"""
		print("Registering with router")
		threading.Thread(target=self.sendWorker, args=(self.conn, msg)).start()
		# self.conn.send(msg.encode())
		# response = self.conn.recv(self.bufferSize).decode()
		# rdata = response.split(' ')
		# assert len(rdata) >= 4
		# self.ip = rdata[3]
		# print("New IP Address: " + self.ip)
		return response