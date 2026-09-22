import dns.resolver
from pymongo import MongoClient

# Termux ke liye DNS resolver fix (yeh /etc/resolv.conf ki error ko hata dega)
resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers = ['8.8.8.8', '1.1.1.1']
dns.resolver.default_resolver = resolver

uri = "mongodb+srv://Kanchanpal01:rajankaran84489@kanchanpal.dfvbsfz.mongodb.net/?retryWrites=true&w=majority&appName=kanchanpal"

try:
    client = MongoClient(uri)
    # Ping karke check karein ki connection bana ya nahi
    client.admin.command('ping')
    print("SUCCESS: MongoDB Atlas connection successful hai!")
except Exception as e:
    print("ERROR: Connection fail ho gaya:", e)
