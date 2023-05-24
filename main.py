import os
from communicator import Communicator
from initializer import Initializer

def parse_ip_addr():
    fmsg = os.popen("ip -o addr | awk '/inet/ {print $2, $3, $4}'").read()
    ip_addr_list = fmsg.strip().split("\n")
    ip_list = []
    for line in ip_addr_list:
        cur = line.strip().split(" ")
        if cur[1]=="inet":
            ip_list.append({"interface": cur[0], "ip": cur[2].split("/")[0]})
    return ip_list


if __name__ == "__main__":
    interfaces = parse_ip_addr()
    print("Please select one of the interfaces:")
    cur=0
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

    comm = Communicator(myip, myname)
    variables = Initializer(comm).information()

    # For referance
    """
    while True:
        curmsg = input().partition(":")
        tgt_ip=None
        with ips_lock:
            if curmsg[0].strip() in ips.keys():
                tgt_ip = ips[curmsg[0].strip()]
        if curmsg[1] != ':' and curmsg[0].strip()=="exit":
            exit(0)
        elif tgt_ip!=None:
            send_msg(tgt_ip, curmsg[2].strip())
        else:
            print("This person does not exists!")
    """
