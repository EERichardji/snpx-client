from snpx_client.snpx_client import SnpxClient
from snpx_client.globals import VariableTypes, VariableInfo

client = SnpxClient(ip="127.0.0.1", connect_on_init=True)
print("Connected")
# time.sleep(5)

client.send_str("CLRALM")

# Read robot position
joints = client.j_pos.read()
# print(joints)

dos = client.do.read(64, 1)
# print(dos)

# Write to DIs
client.di.write([True, False] * 64, start_index=1)

# read a group of variables - mixed variables are allowed
mixed_asg = [
    (f"$DCSS_PSTAT.$STATUS_CPC[{i}]", VariableTypes.INT) for i in range(1, 33)]
mixed_asg.append(("$ANGTOL[1]", VariableTypes.REAL))
var_group = client.sys_vars.create_var_group(mixed_asg)
var_sts = var_group.read()
print(var_sts)

# Read a single system variable
# sys_var = client.sys_vars.read("$DCSS_PSTAT.$STATUS_CPC[1]", VariableTypes.INT)
sys_var2 = client.sys_vars.read("$ANGTOL[1]", VariableTypes.REAL)
print(sys_var2)

# Write system variable
client.sys_vars.write("$ANGTOL[1]", VariableTypes.REAL, 100.13)

# Set custom assignment for SNPX. Custom assignments are stored for the next time that variable is read or written.
# client.sys_vars.set_asg("$ANGTOL[1]", VariableTypes.REAL, asg_num=1)

client.disconnect()
