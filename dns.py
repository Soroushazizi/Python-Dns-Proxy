import socket
import threading
from dnslib import DNSRecord, DNSHeader, RR, A
import matplotlib.pyplot as plt
import json

# Load the configuration from the JSON file
with open('config.json') as config_file:
    config = json.load(config_file)

# Access the configuration items
cache_expiration_time = config['cache-expiration-time']
external_dns_servers = config['external-dns-servers']



# DNS server configuration
dns_server = ('8.8.8.8', 53)  # Change this to the desired DNS server

# Proxy configuration
proxy_host = '127.0.0.1'  # The proxy's IP address
proxy_port = 1553  # The proxy's port number

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
            print('hit')
            # Use the cached IP address to construct the response
            ip_address = cache[cache_key]
            
            # Create a DNS response with the cached IP address and correct ID
            response = DNSRecord()
            response.header = DNSHeader(id=query_id, qr=1, aa=1, ra=1)
            response.add_question(request.q)
            
            # Create the answer RR with the cached IP address
            answer_rr = RR(request.q.qname, qtype, rdata=A(ip_address), ttl=100)
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

# Start the proxy server
proxy_server = ProxyServer()
proxy_server.start()



# # Sample benchmark data
# response_times = [10, 8, 6, 5, 4, 3, 2, 1]  # Response times in milliseconds
# cache_hit_rates = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]  # Cache hit rates

# # Plot response times
# plt.plot(response_times, label='Response Times (ms)')
# plt.xlabel('Request')
# plt.ylabel('Response Time (ms)')
# plt.title('DNS Proxy Benchmark - Response Times')
# plt.legend()
# plt.show()

# # Plot cache hit rates
# plt.plot(cache_hit_rates, label='Cache Hit Rates')
# plt.xlabel('Request')
# plt.ylabel('Cache Hit Rate')
# plt.title('DNS Proxy Benchmark - Cache Hit Rates')
# plt.legend()
# plt.show()



