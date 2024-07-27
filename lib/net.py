import socket
import struct

from .log import *


def is_connected(sock):
	try:
		# this will try to read bytes without blocking and also without removing them from buffer (peek only)
		data = sock.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
		if len(data) == 0:
			return False
	except BlockingIOError:
		return True  # socket is open and reading from it would block
	except ConnectionResetError:
		return False  # socket was closed for some other reason
	except Exception as e:
		printlog("NET WARNING: unexpected exception when checking if a socket is closed")
		return True
	return True


def send_msg(sock, msg):
	# Prefix each message with a 4-byte length (network byte order)
	msg = struct.pack('>I', len(msg)) + msg
	sock.sendall(msg)


def recv_msg(sock):
	def recvall(sock, n):
		# Helper function to recv n bytes or return None if EOF is hit
		data = bytearray()
		while len(data) < n:
			packet = sock.recv(n - len(data))
			if not packet:
				return None
			data.extend(packet)
		return data
	# Read message length and unpack it into an integer
	raw_msglen = recvall(sock, 4)
	if not raw_msglen:
		return None
	msglen = struct.unpack('>I', raw_msglen)[0]
	# Read the message data
	return recvall(sock, msglen)
