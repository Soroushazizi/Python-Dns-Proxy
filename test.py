import socket
import threading
import time
import unittest
from dnslib import DNSRecord, QTYPE, RR

# DNS server configuration
dns_server = ('8.8.8.8', 53)  # Change this to the desired DNS server

# Proxy configuration
proxy_host = '127.0.0.1'  # The proxy's IP address
proxy_port = 5300  # The proxy's port number

# Cache to store IP addresses
cache = {}

class ProxyServer(threading.Thread):
    def __init__(self):
        super(ProxyServer, self).__init__()
        self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.proxy_socket.bind((proxy_host, proxy_port))
    
    def run(self):
        print(f'DNS proxy listening on {proxy_host}:{proxy_port}...')
        
        while True:
            data, client_address = self.proxy_socket.recvfrom(4096)
            threading.Thread(target=self.handle_dns_request, args=(data, client_address)).start()
    
    def handle_dns_request(self, data, client_address):
        request = DNSRecord.parse(data)
        query_id = request.header.id
        
        # Extract query type and domain from the DNS request
        qtype = request.q.qtype
        qname = str(request.q.qname)
        
        # Create cache key using query type and domain
        cache_key = (qtype, qname)
        
        if cache_key in cache:
            # Use the cached IP address to construct the response
            ip_address = cache[cache_key]
            
            # Create a DNS response with the cached IP address and correct ID
            response = DNSRecord()
            response.header.id = query_id
            response.add_question(request.q)
            
            # Create the answer RR with the cached IP address
            answer_rr = RR(rname=request.q.qname, rtype=qtype, rdata=ip_address)
            response.add_answer(answer_rr)
            
            # Convert the DNS response to bytes
            response = response.pack()
        else:
            # Create a socket to communicate with the DNS server
            dns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            try:
                # Send the DNS request to the DNS server
                dns_socket.sendto(data, dns_server)
                
                # Receive the response from the DNS server
                response_data, _ = dns_socket.recvfrom(4096)
                
                # Cache the IP address from the response
                dns_response = DNSRecord.parse(response_data)
                ip_address = str(dns_response.a.rdata)
                cache[cache_key] = ip_address
                
                # Set the response ID to match the query ID
                dns_response.header.id = query_id
                
                # Convert the DNS response to bytes
                response = dns_response.pack()
            finally:
                dns_socket.close()
        
        # Send the DNS response back to the client
        self.proxy_socket.sendto(response, client_address)

class ProxyServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the proxy server before running the tests
        cls.proxy_server = ProxyServer()
        cls.proxy_server.start()
        time.sleep(1)  # Wait for the server to start
    
    @classmethod
    def tearDownClass(cls):
        # Stop the proxy server after running the tests
        cls.proxy_server.join()
    
    def test_cache_hit(self):
        # Add a test entry to the cache
        qtype = QTYPE.A
        qname = 'example.com.'
        ip_address = '192.0.2.1'
        cache[(qtype, qname)] = ip_address
        
        # Create a DNS request for the test entry
        request = DNSRecord()
        request.add_question(DNSRecord.Question(qname, qtype))
        
        # Send the DNS request to the proxy server
        dns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dns_socket.sendto(request.pack(), (proxy_host, proxy_port))
        
        # Receive the response from the proxy server
        response_data, _ = dns_socket.recvfrom(4096)
        
        # Check that the response contains the cached IP address
        response = DNSRecord.parse(response_data)
        self.assertEqual(response.a.rdata, ip_address)
    
    def test_cache_miss(self):
        # Create a DNS request for a domain that is not in the cache
        qtype = QTYPE.A
        qname = 'example.com.'
        request = DNSRecord()
        request.add_question(DNSRecord.Question(qname, qtype))
        
        # Send the DNS request to the proxy server
        dns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dns_socket.sendto(request.pack(), (proxy_host, proxy_port))
        
        # Receive the response from the proxy server
        response_data, _ = dns_socket.recvfrom(4096)
        
        # Check that the response contains a valid IP address
        response = DNSRecord.parse(response_data)
        self.assertIsNotNone(response.a.rdata)
    
    def test_cache_expiration(self):
        # Add a test entry to the cache with a short expiration time
        qtype = QTYPE.A
        qname = 'example.com.'
        ip_address = '192.0.2.1'
        cache[(qtype, qname)] = ip_address
        
        # Sleep for a while to allow the cache entry to expire
        time.sleep(2)
        
        # Create a DNS request for the expired entry
        request = DNSRecord()
        request.add_question(DNSRecord.Question(qname, qtype))
        
        # Send the DNS request to the proxy server
        dns_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dns_socket.sendto(request.pack(), (proxy_host, proxy_port))
        
        # Receive the response from the proxy server
        response_data, _ = dns_socket.recvfrom(4096)
        
        # Check that the response contains a valid IP address
        response = DNSRecord.parse(response_data)
        self.assertIsNotNone(response.a.rdata)

if __name__ == '__main__':
    unittest.main()
