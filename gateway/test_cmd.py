#script 5 dòng gửi một lệnh thử vào fake_bridge.
import serial

s = serial.serial_for_url("socket://localhost:7000")
s.write(b'{"type":"cmd","seat":"Seat-01","cmd":"warn","on":1,"rid":5}\n')
for _ in range(8):
    print(s.readline().decode().strip())