import um31

um = um31.UM31()
um.connect("/dev/ttyUSB0")
# data = um.read_current_values()

data = um.read_month_values(2)

with open("data.txt", "wb") as f:
    f.write(data)

dat2 = um.export_json(data)
for i in dat2:
    print(i)