#!/usr/bin/env python
 
from __future__ import print_function
import RPi.GPIO as GPIO, time, os, requests, pigpio
 
DEBUG = True
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

SCALE_GPIO_INPUT = 17   #Set GPIO Input pin
SCALE_GPIO_SAMPLES_NUM = 100   #Loop for x times
#SCALE_GPIO_EMPTY_LEVEL = 1000 #Above this level its too light - BIG CAPACITOR
#SCALE_GPIO_EMPTY_LEVEL = 5000 #Above this level its too light - SMALL CAPACITOR

CONSECUTIVE_EMPTY_SAMPLES_NUM = 10
CONSECUTIVE_FULL_SAMPLES_NUM = 10

CONSECUTIVE_INIT_SAMPLES_NUM = 10
INIT_STABLE_DIFF = 5
INIT_EMPTY_SAFETY_LEVEL = 0.85
INIT_DEFAULT_EMPTY_LEVEL = 5000

firstTimeInit = True
bowlFull = False # True = send yo when empty, False = yo sent, waiting to get filled 
emptyConsecutive = 0
fullConsecutive = 0
emptyLevel = INIT_DEFAULT_EMPTY_LEVEL

# function to return the time taken the capacitor to fill up
def RCtime (RCpin, currEmptyLevel):
        reading = 1
        GPIO.setup(RCpin, GPIO.OUT)
        GPIO.output(RCpin, GPIO.LOW)
        time.sleep(0.001)
 
        GPIO.setup(RCpin, GPIO.IN)
        # This takes about 1 millisecond per loop cycle
        #while (GPIO.input(RCpin) == GPIO.LOW and reading < currEmptyLevel):
        while (GPIO.input(RCpin) == GPIO.LOW):
                reading += 1
        return reading

# yo when empty
def YoEmpty ():
        print ("empty bowl! YO!")
        payload = {'api_token': '5de17aec-e47b-4390-8e68-c4d28e5371aa'}
        #payload = {'api_token': ''} #not to really send yoes
        r = requests.post("https://api.justyo.co/yoall/", data=payload)
        if DEBUG:
            print ("status_code:", r.status_code, " response:", r.text)
        if (r.status_code != 201):
            print ("yo error ", r.status_code)

# MAIN

yoAvg = 0
lastyoAvg = 0

print ("starting init. make sure bowl is empty")

while True:
        yoCounter = 1
        reading = 0
        yoSum = 0

        while yoCounter <= SCALE_GPIO_SAMPLES_NUM:
                reading = int(RCtime(SCALE_GPIO_INPUT, emptyLevel))
                yoSum += reading
                yoCounter += 1

        lastyoAvg = yoAvg
        yoAvg = yoSum / SCALE_GPIO_SAMPLES_NUM

        if DEBUG:
            print ("avg is ", yoAvg, " for ", SCALE_GPIO_SAMPLES_NUM, " samples")

        if firstTimeInit:
            diff = abs(float(lastyoAvg - yoAvg) / yoAvg * 100)
            if DEBUG:
                print ("lastyoAvg=", lastyoAvg, "diff=", diff)

            if diff < INIT_STABLE_DIFF:
                emptyConsecutive += 1
                if emptyConsecutive == CONSECUTIVE_INIT_SAMPLES_NUM:
                    emptyLevel = (int) ((yoAvg + lastyoAvg) / 2 * INIT_EMPTY_SAFETY_LEVEL)
                    #emptyLevel = (int) (yoAvg * INIT_EMPTY_SAFETY_LEVEL)
                    #emptyLevel = yoAvg * 3
                    bowlFull = False
                    emptyConsecutive = 0
                    firstTimeInit = False
                    print ("init complete. now fill the bowl")
                    if DEBUG:
                        print ("empty level=", emptyLevel)
            else:
                emptyConsecutive = 0

            '''    
            if yoAvg == SCALE_GPIO_EMPTY_LEVEL:
                fullConsecutive = 0
                emptyConsecutive += 1
                if emptyConsecutive == CONSECUTIVE_INIT_SAMPLES_NUM: #init finished. bowl is empty
                    firstTimeInit = False
                    bowlFull = False
                    if DEBUG:
                        print ("init finished. bowl is empty")
            else:
                emptyConsecutive = 0
                fullConsecutive += 1
                if fullConsecutive == CONSECUTIVE_INIT_SAMPLES_NUM: #init finished. bowl is full
                    firstTimeInit = False
                    bowlFull = True
                    if DEBUG:
                        print ("init finished. bowl is full")
            '''
        elif bowlFull: 
            if yoAvg >= emptyLevel:
                emptyConsecutive += 1
                if DEBUG:
                    print ("bowl empty #", emptyConsecutive)
                if emptyConsecutive == CONSECUTIVE_EMPTY_SAMPLES_NUM: ##means that the bowl was empty for X consecutive samples
                    bowlFull = False
                    fullConsecutive = 0
                    emptyConsecutive = 0
                    YoEmpty()
            else:
                emptyConsecutive = 0
        else:
            if yoAvg >= emptyLevel:
                fullConsecutive = 0
            else:
                fullConsecutive += 1
                if DEBUG:
                    print ("bowl full #", fullConsecutive)
                if fullConsecutive == CONSECUTIVE_FULL_SAMPLES_NUM: ##means that the bowl was filled and now we need to protect it
                    if DEBUG:
                        print ("bowl full again. protect again")
                    bowlFull = True
                    fullConsecutive = 0
                    emptyConsecutive = 0


# clean before you leave
GPIO.cleanup()