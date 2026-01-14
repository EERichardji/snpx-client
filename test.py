from .snpx_client import SnpxClient, VariableTypes, VariableInfo

client = SnpxClient(ip="127.0.0.1", connect_on_init=True)
print("Connected")
#time.sleep(5)
client.send_str("CLRALM")