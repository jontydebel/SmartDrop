import network
import urequests
import ujson
from machine import Pin, ADC, Timer
import utime
import ntptime

trigger = Pin(12, Pin.OUT) #yellow
echo = Pin(13, Pin.IN) #White


# Initialize ADC for raindrop sensor
adc = ADC(Pin(35))  # Use pin 35 for analog input
adc.atten(ADC.ATTN_11DB)  # Set attenuation level to 11 dB for full range 0-3.3V

## Code for motor control ##
# Define motor pins
dir_pin = Pin(33, Pin.OUT)  # Direction pin
step_pin = Pin(32, Pin.OUT)  # Step pin 
en_pin = Pin(25, Pin.OUT)
steps_per_revolution = 200  # Number of steps per revolution

# Initialize timer
tim = Timer(0)

# Function to toggle the step pin
def step(t):
    step_pin.value(not step_pin.value())

# Function to rotate the motor with specified delay (in microseconds) per step
def rotate_motor(delay_us, num_steps, clockwise=True):
    # Set motor direction
    dir_pin.value(1 if clockwise else 0)

    # Set up timer for stepping
    tim.init(freq=1000000//delay_us, mode=Timer.PERIODIC, callback=step)

    # Wait for the specified number of steps
    utime.sleep_ms(int((delay_us / 1000) * num_steps))

    # Stop the timer
    tim.deinit()

#Get ultra-sonic sensor readings
def us_reading():
    # print("Starting get distance")
    trigger.value(0)
    utime.sleep_us(2)
    trigger.value(1)
    utime.sleep_us(5)
    trigger.value(0)

    # Measure duration of echo pulse
    timeout_start = utime.ticks_us()
    while echo.value() == 0:
        if utime.ticks_diff(utime.ticks_us(), timeout_start) > 5000000:
            print("Timeout: No echo received")
            return None

    pulse_start = utime.ticks_us()
    while echo.value() == 1:
        if utime.ticks_diff(utime.ticks_us(), pulse_start) > 5000000:
            print("Timeout: Echo duration too long")
            return None

    pulse_end = utime.ticks_us()

    # Calculate distance
    duration = utime.ticks_diff(pulse_end, pulse_start)
    print(f'Duration is: {duration}')
    distance_cm = (duration * 0.0343) / 2
    print(f'distance_cm is: {distance_cm}')
    return distance_cm

def get_distance(samples):
    total = 0
    count = 0
    average = 0
    while count < samples:
        count = count + 1
        #Volume = -0.2984 * Height + 7.425
        # print("start")
        distance = us_reading()
        if distance is not None:
            # print("Distance from object:", distance, "cm")
            total = total + distance
        else:
            # print("Distance measurement failed.")
            return -1
        average = total / count
        # print(f"Average is {average}")
        utime.sleep(0.01)
    volume = -0.2984 * average + 7.425
    if volume < 0:
        volume = 0
    print(f"Finished grabbing all data, volume is: {volume}")
    return volume

# Connect to Wi-Fi
def connect_to_wifi(ssid, password):
    print(f"Attempting connect to {ssid} with {password}")
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    notfound = True
    while notfound:
        for ssid,_,_,_,_,_ in sta_if.scan():
            print('SSID: ' + ssid.decode('utf-8'))
            if ssid.decode('utf-8') == 'fbgateway':
                notfound = False
                break
    print('MACC is: ' + sta_if.config('mac').hex())
    time_start = utime.ticks_us()
    sta_if.connect(ssid, password)
    while not sta_if.isconnected():
        if utime.ticks_diff(utime.ticks_us(), time_start) > 15000000: #15s to connect
            return -1
        pass
    
    print("Connected to Wi-Fi - printing MAC Address")
    print(sta_if.config('mac').hex())
    return sta_if

# Function to send data to server with retry mechanism
def send_data(data, ssid, password, url, endpoint):
    # Check Wi-Fi connection
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("Wi-Fi disconnected. Reconnecting...")
        connect_to_wifi(ssid, password)
        # sync_time()  # Synchronize time after reconnecting

    # Set headers
    headers = {"Content-Type": "application/json"}

    # Encode data to JSON
    encoded_data = ujson.dumps(data)
    print("Encoded data:")
    print(encoded_data)

    # Print request headers
    print("Request headers:")
    for key, value in headers.items():
        print(f"{key}: {value}")
    
    # Retry mechanism
    retry_count = 3
    while retry_count > 0:
        try:
            response = urequests.post((url+endpoint), json=data, headers=headers)
            # Check if the request was successful (status code 2xx)
            if 200 <= response.status_code < 300:
                print("Response is:")
                print(response.text)  # Print the response content
                response.close()  # Close the response connection
                return  # Exit the function if successful
            else:
                print(f"Failed to send data. Status code: {response.status_code}")
                response.close()
                retry_count -= 1  # Decrement retry count
                print(f"Retrying... {retry_count} attempts left")
        except Exception as e:
            print(f"An error occurred: {e}")
            retry_count -= 1  # Decrement retry count
            print(f"Retrying... {retry_count} attempts left")

    print("Failed to send data after retrying.")
    return

# Function to check rain sensor
def check_rain_sensor():
    # Read analog value from raindrop sensor
    analog_value = adc.read()
    print("Analog value from raindrop sensor:", analog_value)
    # Define a threshold value to determine rain detection
    threshold = 1900  # Adjust this value based on sensor and environment

    # Check if rain is detected based on the analog value and threshold
    if analog_value < threshold:
        print("Rain detected!")
        return True  # Rain detected
    else:
        
        # print("No rain detected.")
        return False  # No rain detected
    
def check_dashboard_lid_status():
    url = "https://smartdrop.uqcloud.net/api/LidUpdate"
    try:
        response = urequests.get(url)
        if response.status_code == 200:
            print('Got 200 response')
            data = response.json()
            print
            if 'lidStatus' in data:
                return data['lidStatus']
            return False #Call did not work
        else:
           return False
    except Exception as e:
        print(f"Error while fetching lid status: {e}")
    return False

# Custom time format tool
def strftime(current_time):
    formatted_time = "{:04d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
            current_time[0], current_time[1], current_time[2],
            current_time[3], current_time[4], current_time[5]
        )
    return formatted_time

# Check OpenWeather API for rain
def check_rain_api():
    url = "https://api.openweathermap.org/data/2.5/weather?lat=-27.50&lon=153.01&appid=c06a18d0397f921d93a701258a540cc4"
    try:
        response = urequests.get(url)
        if response.status_code == 200:
            print('Got 200 response')
            data = response.json()
            print
            if 'weather' in data:
                for condition in data['weather']:
                    if 'main' in condition and 'description' in condition:
                        # print('Made it this far')
                        # print(condition['main'].lower())
                        if condition['main'].lower() == 'rain' or 'rain' in condition['description'].lower():
                            return True
            return False
        else:
           return False
    except Exception as e:
        print(f"Error while fetching weather data: {e}")
    return False

def main():
    #MACC Address is 30aea49cdcec
    last_open_time = None  # Initialize daily open time
    num_sample = 20
    MAX_VOL = 6.8 #6.8 Litres
    url = 'https://smartdrop.uqcloud.net'
    
    # Wi-Fi credentials
    ssid = "fbgateway"
    password = "farmbotgateway!"
    
    # Connect to Wi-Fi
    connect_to_wifi(ssid, password)
    

    # Synchronize time with NTP server
    try:
        ntptime.settime() #Get real-time (UTC Format)
        print("Time synchronized with NTP server")
        # print(utime.localtime(utime.mktime(utime.localtime()) + 10 * 3600))  # 10 hours * 3600 seconds/hour for UTC+10
    except Exception as e:
        print("Failed to synchronize time with NTP server:", e)
    last_tank_data_sent = utime.time()  # Initialize last time tank data was sent

    
    #Get initial volume
    volume = get_distance(num_sample)
    print(f'Finished with {volume}, checking rain sensor')
    en_pin.value(1) #Set High when not in use.

    raining = False
    while True:
        current_time = utime.localtime(utime.mktime(utime.localtime()) + 10 * 3600)  # Get current time (UTC) and convert to UTC+10
        volume = get_distance(num_sample)
        
        if (check_rain_sensor() or check_rain_api()) and (volume < MAX_VOL):  # If it's raining #Check volume is correct
        # if check_rain_sensor():  # If it's raining - no API call (For when no wifi)
            print(f'It is raining and {volume} < {MAX_VOL}.')
            
            if not raining:  # If it has just started raining
                # Open the motor
                print('It is raining. Opening motor.')

                en_pin.value(0)
                utime.sleep(1)
                rotate_motor(13000, 155, clockwise=False)
                utime.sleep(0.5) #Wait for motor to close
                en_pin.value(1)

                # Send data messagse with time open
                time_open = strftime(current_time)
                send_data([{"timestamp": time_open, "lidStatus":"open"}], ssid, password, url, '/api/lidStatusData')
                
                # Record the time when the rain sensor opens
                last_open_time = utime.time()
                raining = True
        else:  # If it's not raining
            print('It is not raining')
            if raining:  # If it has just stopped raining
                # Close the motor
                print('It has stopped raining. Closing motor.')

                en_pin.value(0)
                utime.sleep(1)
                rotate_motor(13000, 160, clockwise=True)
                utime.sleep(0.5) #Wait for motor to close
                en_pin.value(1)

                time_close = strftime(current_time)
                   
                volume = get_distance(num_sample)
                if last_open_time is not None:  # If the rain sensor was open
                    # Calculate the duration the rain sensor stayed open
                    open_duration = utime.time() - last_open_time
                    # Send data message with time close and open duration
                    send_data([{"date": time_close, "hours": open_duration, "waterLevel":volume}], ssid, password, url, '/api/tankData')
                
                # Send data message with time close
                send_data([{"timestamp": time_close, "lidStatus":"close"}], ssid, password, url, '/api/lidStatusData')
                # Reset the rain status
                raining = False
                #Send volume on close  
                send_data([{"date": time_close, "currentLevel": volume}], ssid, password, url ,'/api/currentLevelData')
        # Check if 2 hours has passed since the last tank data sent
        if (utime.time() - last_tank_data_sent) >= (12 * 60 * 60):  # 12 hours in seconds
            # Send tank data
            print('Sending 12-hour update')
            send_data([{"date": strftime(current_time), "hours": -1, "waterLevel":volume}], ssid, password, url, '/api/tankData')
            last_tank_data_sent = utime.time()

        webLid = check_dashboard_lid_status()
        if (webLid == "open") and not raining: #raining flag is true if lid is open
            #Lid is open and web designated it to close
            en_pin.value(0)
            utime.sleep(1)
            rotate_motor(13000, 155, clockwise=False)
            utime.sleep(0.5) #Wait for motor to close
            en_pin.value(1)

            # Send data messagse with time open
            time_open = strftime(current_time)
            send_data([{"timestamp": time_open, "lidStatus":"open"}], ssid, password, url, '/api/lidStatusData')
            
            # Record the time when the rain sensor opens
            last_open_time = utime.time()
            raining = True
        
        if (webLid == "close") and raining: #raining flag is true if lid is open
            #Lid is open and web designated it to close
            en_pin.value(0)
            utime.sleep(1)
            rotate_motor(13000, 160, clockwise=True)
            utime.sleep(0.5) #Wait for motor to close
            en_pin.value(1)

            time_close = strftime(current_time)
                
            volume = get_distance(num_sample)
            if last_open_time is not None:  # If the rain sensor was open
                # Calculate the duration the rain sensor stayed open
                open_duration = utime.time() - last_open_time
                # Send data message with time close and open duration
                send_data([{"date": time_close, "hours": open_duration, "waterLevel":volume}], ssid, password, url, '/api/tankData')
            
            # Send data message with time close
            send_data([{"timestamp": time_close, "lidStatus":"close"}], ssid, password, url, '/api/lidStatusData')
            # Reset the rain status
            raining = False
            #Send volume on close  
            send_data([{"date": time_close, "currentLevel": volume}], ssid, password, url ,'/api/currentLevelData')

        utime.sleep(300) # Sleep for 5 minutes in seconds

        

# Execute main function
main()



