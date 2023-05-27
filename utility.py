import os

def parse_ip_addr():
    fmsg = os.popen("ip -o addr | awk '/inet/ {print $2, $3, $4}'").read()
    ip_addr_list = fmsg.strip().split("\n")
    ip_list = []
    for line in ip_addr_list:
        cur = line.strip().split(" ")
        if cur[1]=="inet":
            ip_list.append({"interface": cur[0], "ip": cur[2].split("/")[0]})
    return ip_list
    
def build_id(ip: str, name: str) -> str:
    return f"{ip}-{name}"
