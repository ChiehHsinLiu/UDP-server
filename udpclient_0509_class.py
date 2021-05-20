import socket
import threading
import time

class ClientSocket():
    def __init__(self):
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)   # socket
        self.__wait_recv = False            # T after send a msg. F after recv a msg
        self.__quit_by_user = False         # T if user input '!quit'
        self.__t_send = 0                   # save the time after send a msg
        self.__t_timeout = 0                # save the time after recv timeout
        self.__user_name = ''               # user_name input in enter_user_name() method
        self.__string_bytes = ''            # previous sent msg in input_msg()
        self.__search = ''                  # name of setting that user what to get, in input_msg() method
        self.run()                          # run methods automatically

    def run(self):
        self.enter_user_name()              # handshake procedure

        receive_thread = threading.Thread(target=self.receive_msg_thread)
        receive_thread.daemon = True
        receive_thread.start()              # start the thread to recv msg

        self.setDefaults()                  # set BURST-LEN & DELAY-LEN to default value
        self.input_msg()                    # user input actions

        receive_thread.join()               # after input_msg() finish, wait the thread to finish
        print('thread is closed')
        self.sock.close()
        print('close socket')

    def enter_user_name(self):
        while True:
            self.__user_name = input("Enter Username: ")
            user_command = "HELLO-FROM " + self.__user_name + "\n"
            self.__string_bytes = user_command.encode("utf-8")
            bytes_len = len(self.__string_bytes)
            num_bytes_to_send = bytes_len
            while num_bytes_to_send > 0:
                num_bytes_to_send -= self.sock.sendto(self.__string_bytes[bytes_len - num_bytes_to_send:], serverAddress)
            message, address = self.sock.recvfrom(4096)
            message = message.decode("utf-8")
            print(message)
            # if it is not in use, break, otherwise create a new socket
            if (message != 'IN-USE\n' and message != 'BUSY\n' and message != 'BAD-RQST-HDR\n' and message != 'BAD-RQST-BODY\n'):
                break

    def receive_msg_thread(self):
        while True:
            if self.__quit_by_user:
                print('__quit_by_user is True, stop while loop in recv_msg_thread')
                break
            try:
                self.sock.settimeout(10.0)
                data, address = self.sock.recvfrom(4096)
                #print('recv msg: ',data, ' at : ', time.perf_counter())
                self.__wait_recv = False
                try:
                    data = data.decode("utf-8")
                    self.check_msg(data)     # call check_msg function from thread
                except Exception as e:
                    print('Error: cannot decode in recv_msg_thread')
                    self.send_msg()
                    continue
            except Exception as e:      # timeout
                self.__t_timeout = time.perf_counter()
                if self.__wait_recv and self.__t_timeout - self.__t_send > 10:
                    print('timeout in recv_msg_thread at: ', self.__t_timeout)
                    print('send msg again')
                    self.send_msg()
                    continue
                else:
                    # print('do noting\n')
                    continue

    def setDefaults(self):
        self.sock.sendto(("SET BURST-LEN 3 3\n").encode("utf-8"), serverAddress)
        self.sock.sendto(("SET DELAY-LEN 5 5\n").encode("utf-8"), serverAddress)
        print('set defaults done')

    def input_msg(self):
        while True:
            send_message = input()
            if send_message == '!quit':  # if quit close the chat
                print('enter !quit by user')
                self.__quit_by_user = True
                break
            elif send_message == '!drop':
                dropValue = input("Enter the drop probability (0-1): ")
                user_command = 'SET DROP ' + str(dropValue) + '\n'
            elif send_message == '!flip':
                flipValue = input("Enter the flip-bit probability (0-1): ")
                user_command = 'SET FLIP ' + str(flipValue) + '\n'
            elif send_message == '!burst':
                burstValue = input("Enter the burst error probability: ")
                user_command = 'SET BURST ' + str(burstValue) + '\n'
            elif send_message == '!burstlen':
                lowerLen, upperLen = input("Enter lower and upper bound of burst error length: ").split()
                user_command = 'SET BURST-LEN ' + str(lowerLen) + " " + str(upperLen) + '\n'
            elif send_message == '!delay':
                delayValue = input("Enter the delay probability: ")
                user_command = 'SET DELAY ' + str(delayValue) + '\n'
            elif send_message == '!delaylen':
                lowerDel, upperDel = input("Enter lower and upper bound of delay length (seconds): ").split()
                user_command = 'SET DELAY-LEN ' + str(lowerDel) + " " + str(upperDel) + '\n'
            elif send_message == '!get':
                while True:
                    value = input("Enter a setting value name: (drop, flip, burst, burst-len, delay or delay-len): ")
                    if value != "drop" and value != "flip" and value != "burst" and value != "burst-len" and value != "delay" and value != "delay-len":
                        print("Wrong setting value")
                    else:
                        value = value.upper()
                        self.__search = value
                        break
                user_command = "GET " + value + "\n"
            elif send_message == '!reset':
                user_command = 'RESET\n'
            elif send_message == '!who':
                user_command = "WHO\n"  # send who to check logged in users
            else:
                # cut the @ form input and append into command
                send_message = send_message[1:]
                user_command = "SEND " + send_message + "\n"
            self.__string_bytes = user_command.encode("utf-8")
            self.send_msg()

    def send_msg(self):
        bytes_len = len(self.__string_bytes)
        num_bytes_to_send = bytes_len
        while num_bytes_to_send > 0:
            num_bytes_to_send -= self.sock.sendto(self.__string_bytes[bytes_len - num_bytes_to_send:], serverAddress)
        self.__t_send = time.perf_counter()
        #print('Send_msg: ', self.__string_bytes, ' at: ', self.__t_send)
        self.__wait_recv = True

    def check_msg(self,data):
        if data[-1] != '\n':        # last char is '\n', wrong
            print('last char is not next line')
            self.send_msg()
        space = data.find(' ')     # find 1st space
        if space == -1:            # find no space, check header only msg
            if data == 'SEND-OK\n' or data == 'UNKNOWN\n' or data == 'BAD-RQST-HDR\n' or data == 'BAD-RQST-BODY\n' or data == 'SET-OK\n':
                print(data)
            else:
                print('Error: header only msg is wrong')
                self.send_msg()
        else:                 # 1st space is found, can be only 'WHO-OK' & 'DELIVERY' msg
            header = data[0:space]
            if header != 'WHO-OK' and header != 'DELIVERY' and header != 'VALUE':  # wrong header name
                print('Error: wrong header')
                self.send_msg()
            elif header == 'VALUE':
                name = self.__search
                space2 = data.find(' ', space+1)
                if name == 'DROP' or name == 'FLIP' or name == 'BURST' or name == 'DELAY':
                    if space2 != -1:
                        print('Error: VALUE, value is wrong')
                        self.send_msg()
                    else:
                        value = data[space+1:-1]
                        try:
                            value = float(value)        # try to convert value (a string) to float
                            if value < 0 or value > 1:
                                print('Error: VALUE, value out of range')
                                self.send_msg()
                            else:
                                print(data)             # correct
                        except Exception as e:
                            print('Error: VALUE, value is not a float')
                            self.send_msg()
                else: # name == 'BURST-LEN' or name == 'DELAY-LEN':
                    if space2 == -1:
                        print('Error: VALUE, lower is wrong')
                        self.send_msg()
                    else:
                        lower = data[space+1:space2]
                        try:
                            lower = int(lower)
                            space3 = data.find(' ', space2+1)
                            if space3 != -1:
                                print('Error: VALUE, upper is wrong')
                                self.send_msg()
                            else:
                                upper = data[space2+1:-1]
                                try:
                                    upper = int(upper)
                                    if lower < 0 or upper < 0 or lower > upper:
                                        print('Error: VALUE, lower or upper value is wrong')
                                        self.send_msg()
                                    else:
                                        print(data)     # correct
                                except Exception as e:
                                    print('Error: VALUE, upper is not a int')
                                    self.send_msg()
                        except Exception as e:
                            print('Error: VALUE, lower is not a int')
                            self.send_msg()
            elif header == 'WHO-OK':
                space2 = data.find(' ', space+1)        # find 2nd space
                if space2 != -1:                        # find the 2nd space in the case WHO-OK, wrong
                    # since correct form is 'WHO-OK <name>...\n'
                    print('Error: WHO-OK, body is wrong')
                    self.send_msg()
                elif data.find(self.__user_name, space+1) == -1:   # can't find user_name, wrong
                    print('Error: WHO-OK, cannot find user_name')
                    self.send_msg()
                else:               # 'WHO-OK <name1>,...,<namen>\n' is correct
                    print(data)
            else:                   # header == 'DELIVERY'
                space2 = data.find(' ', space+1)            # find 2nd space
                if space2 == -1:    # find no 2nd space in the case DELIVERY, wrong.
                    print('Error: DELIVERY, body is wrong')
                else:               # 'DELIVERY <user> <msg>\n' is correct
                    print(data)


# main program starts
serverAddress = ("3.121.226.198", 5382)
# creat a class ClientSocket() object client
client = ClientSocket()

print('client program closed')