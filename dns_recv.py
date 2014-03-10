import socket
import optparse
from lib.FrameProcessor import ProcessFrame

def main(ip, port, out_file):	

	# setup the socket
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind((ip, port))

	print '[INFO] Fake DNS server listening on port', ip, 'on', port

	frameHandler = ProcessFrame()

	# if we have a file destination to write to, set it
	if out_file:
		frameHandler.setOutfile(out_file)

	# Start a never ending loop and receive the UDP frames in sock
	# From: http://code.activestate.com/recipes/491264-mini-fake-dns-server/
	while True:

		# read the socket
		data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes


		# Determine the OPCODE for the query.
		op_code = (ord(data[2]) >> 3) & 15

		# OPCODE 0 == Standard query http://www.networksorcery.com/enp/protocol/dns.htm#Opcode
		if op_code == 0:

			# the raw packet has the name we are querying starting at byte 12
			byte_name_start=12
			byte_name_length=ord(data[byte_name_start])
			domain = ''

			# set the frame to decode, as we are promarily interested in the
			# first part of the question
			frame_to_decode = data[byte_name_start + 1:byte_name_start + byte_name_length + 1]

			# Continue working with the rest of the request and process a response
			# we will also lookup the state in ProcessFrame to determine the IP
			# response we should be seeing
			while byte_name_length != 0:

				domain += data[byte_name_start + 1:byte_name_start + byte_name_length + 1] + '.'

				byte_name_start+= byte_name_length + 1
				byte_name_length=ord(data[byte_name_start])

			print '[INFO] Full resource record query was for:', domain

			# send the frame to the processor
			frameHandler.setData(frame_to_decode)
			frameHandler.process()

			# prepare the response packet
			response_packet = ''

			if domain:
				response_packet+=data[:2] + "\x81\x80"
				response_packet+=data[4:6] + data[4:6] + '\x00\x00\x00\x00'							# Questions and Answers Counts
				response_packet+=data[12:]															# Original Domain Name Question
				response_packet+='\xc0\x0c'															# Pointer to domain name
				response_packet+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'							# Response type, ttl and resource data length -> 4 bytes
				response_packet+=str.join('',map(lambda x: chr(int(x)), '127.0.0.1'.split('.')))	# 4bytes of IP

		sock.sendto(response_packet, addr)

if __name__ == '__main__':

	parser = optparse.OptionParser("usage: %prog -L <ip>")
	parser.add_option('-L', '--listen', dest='listen',
						type='string', help='specify hostname to listen on')
	parser.add_option('-p', '--port', dest='port', default=53,
						type='int', help='port number to listen on (Defaults: 53)')
	parser.add_option('-O', '--outfile', dest='out', default='',
						type='string', help='specify a message file destination')

	(options, args) = parser.parse_args()

	if not options.listen:
		parser.error('At least a listening IP must be provided.')

	listening_ip = options.listen
	listening_port = options.port
	out_file = options.out

	# kick off the main loop
	main(listening_ip, listening_port, out_file)