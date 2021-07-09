from smbus2 import SMBus
from mlx90614 import MLX90614
from time import sleep
from datetime import datetime
bus = SMBus(1)
sensor = MLX90614(bus,address=0x5A)
data = {}
try:
    while True:
        data =  { 'Time': datetime.now(),  
          'TP': 1,  
          'Temp': sensor.get_ambient(),
            'Temp2':sensor.get_object_1()
          } 
        sleep(1)
        print(data)
    
except KeyboardInterrupt:
    print("Ctrl-C to terminate")
    bus.close()
    pass


