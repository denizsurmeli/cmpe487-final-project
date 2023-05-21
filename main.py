import os
import threading

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

    myip = interfaces[choice]["ip"]
    print("Selected ip", myip)

    while True:
        myname = input("Name: ").strip()
        if myname.isalnum():
            break
        print("Please enter a valid name!")

    # Start listening to port
    read_thread = threading.Thread(target=recv_msg, daemon=True)
    read_thread.start()

    # Get greeting from other peers
    broadcast_thread = threading.Thread(target=recv_broadcast, daemon=True)
    broadcast_thread.start()

    # Discover other peers
    discover_thread = threading.Thread(target=discover_nodes, daemon=True)
    discover_thread.start()

    # Periodic cleanup service
    cleanup_thread = threading.Thread(target=cleanup_service, daemon=True)
    cleanup_thread.start()

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
