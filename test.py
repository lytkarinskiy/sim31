import um31

um = um31.UM31()
um.connect("/dev/ttyUSB0")
# data = um.read_current_values()

data = um.read_month_values(1)

with open("data.txt", "wb") as f:
    f.write(data)

dat2 = um.export_json(data)
for i in dat2:
    print(i)




import um31
um = um31.UM31()
dat = open("data.txt", "rb").read()
dat2 = um.export_json(dat)





dev_dict[md[3]] + " with ID" + md[0] + "/" + md[1] + " , S/N" + sn + " at " + bus_dict[md[2]]