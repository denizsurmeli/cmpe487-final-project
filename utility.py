import os
import json

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

def client_setup():
    interfaces = parse_ip_addr()
    print("Please select one of the interfaces:")

    for it in range(len(interfaces)):
        print(it, "-", interfaces[it])

    choice = int(input("Choice: "))
    while not 0 <= choice < len(interfaces):
        choice = int(input("Please enter a valid range: "))

    myip = interfaces[choice]["ip"]
    print("Selected ip", myip)

    while True:
        myname = input("Name: ").strip()
        if myname.isalnum():
            break
        print("Please enter a valid name!")
    

    return myip, myname

# Group chat:
GROUP_CHAT_MESSAGE = {
    "type": "group_chat",
    "content": None
}

# Private chat:
PRIVATE_CHAT_MESSAGE = {
    "type": "private_chat",
    "content": None
}


# TODO: Discuss with the team about binding the function in this way.
# This parser for general communication, such as group and private chatting etc.
# and it must be attached by default.
def recv_parser(self, message:str, ip:str):
    try:
        message: dict = json.loads(message)
    except:
        print("ERROR: Could not parse the message:", message)
        return
    if message["type"] == "group_chat":
        _from = self.persons[ip]
        print(f"(group chat){_from.name}: {message['content']}")
    elif message["type"] == "private_chat":
        _from = self.persons[ip]
        print(f"(private chat){_from.name}: {message['content']}")