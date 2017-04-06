import um31

um = um31.UM31()
um.connect("/dev/ttyUSB0")
data = um.read_month_values(1)

with open("data.txt", "wb") as f:
    f.write(data)

for i in um.export_json(data):
    print(i)
