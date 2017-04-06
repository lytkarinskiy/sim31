import um31

um = um31.UM31()
um.connect("/dev/ttyUSB0")
data = um.read_current_values()

with open("data.txt", "wb") as f:
    f.write(data)

dat2 = um.clean_data(data)
