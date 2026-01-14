from snpx_client import SnpxClient, VariableTypes, FanucVariable

client = SnpxClient(ip="127.0.0.1", connect_on_init=True)
print("Connected")
#time.sleep(5)

# Read robot position
joints = client.j_pos.read()
print(joints)

dos = client.do.read(64, 1)
#print(dos)

# Write to DIs
client.di.write([True, False] * 64, start_index=1)

#Read system variable
sys_var = client.read_sys_var(f"$DCSS_PSTAT.$STATUS_CPC[1]", VariableTypes.INT)
print(sys_var)

sys_var2 = client.read_sys_var("$ANGTOL[1]", VariableTypes.REAL)
print(sys_var2)

#Write system variable
#client.write_sys_var("$ANGTOL[1]", VariableTypes.REAL, 1200.13)

#Set custom assignment for SNPX. Custom assignments are stored for the next time that variable is read or written.
#client.set_asg(asg_num = 1, var_name = "$ANGTOL[1]")

client.disconnect()