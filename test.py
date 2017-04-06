import um31

um = um31.UM31()
um.connect("/dev/ttyUSB0")
data = um.read_current_values(1)

with open("data.txt", "wb") as f:
    f.write(data)

for i in um.export_json(data):
    print(i)


import um31
um = um31.UM31()
dat =open("data.txt", "rb").read()
dat2 = um.clean_data(dat)
dat2

