
from platform import platform
import paho.mqtt.client as mqtt 
from random import randrange, uniform
import requests
import time, datetime
import xmltodict
import xml.etree.ElementTree as ET
from lxml import etree, objectify
from io import StringIO, BytesIO

mqttBroker ="192.168.0.101" 
apikey_bus= 'REMOVED_BUS_API_KEY'
apikey_rail= 'REMOVED_RAIL_API_KEY'




def on_connect(client, userdata, flags, rc):
    print("initial connection made")
    print(datetime.datetime.now())

    if rc==0:
        print("connected OK Returned code=",rc)
        print(client)
    else:
        print("Bad connection Returned code=",rc)

def on_disconnect(client, userdata, rc):
   print("Client Got Disconnected")
   print(datetime.datetime.now())
   if rc != 0:
       print('Unexpected MQTT disconnection. Will auto-reconnect')

   else:
       print('rc value:' + str(rc))

   try:
       print("Trying to Reconnect")
       client.connect(mqttBroker)

   except:
       print("Error in Retrying to Connect with Broker")

client = mqtt.Client()
client.username_pw_set("mqtt", password="REMOVED_MQTT_PASSWORD")
print("attempting mqtt connections")
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.connect(mqttBroker) 



def getRailStopPredictions(platformID):
    x=requests.get('http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx', params={'key':apikey_rail, 'stpid':platformID})
    predictionsObject=objectify.fromstring(x.text.encode('utf-8'))
    # print(x.text)
    return predictionsObject

def getBusStopPredictions(stopID, route=None):
    x=requests.get('http://www.ctabustracker.com/bustime/api/v2/getpredictions', params={'key':apikey_bus, 'stpid':stopID, 'rt':route})
    predictionsObject=objectify.fromstring(x.text)
    return predictionsObject


def getBusStopETAs(predictions):
    etaList=[]
    if not hasattr(predictions,'prd'):
        etaList.append(-1)
        return etaList

    for prediction in predictions.prd:
#        print(prediction)
        predictedArrival=datetime.datetime.strptime(prediction.prdtm.text,'%Y%m%d %H:%M')
        eta = predictedArrival - timenow
 #       print(eta)
        etaList.append(eta.seconds)
    return etaList
    
def getRailStopETAs(predictions):
    etaList=[]
    if not hasattr(predictions,'eta'):
        etaList.append(-1)
        return etaList

    for prediction in predictions.eta:
  #      print(prediction.arrT)
        predictedArrival=datetime.datetime.strptime(prediction.arrT.text,'%Y%m%d %H:%M:%S')
        eta = predictedArrival - timenow
   #     print(eta.seconds)
        etaList.append(eta.seconds)
 
    return etaList

# while True:
#     randNumber = uniform(20.0, 21.0)
#     client.publish("TEMPERATURE", randNumber)
#     print("Just published " + str(randNumber) + " to topic TEMPERATURE")
#     time.sleep(1)


#train api REMOVED_RAIL_API_KEY
# http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key=REMOVED_RAIL_API_KEY&mapid=40380
#bus api REMOVED_BUS_API_KEY

# x=requests.get('http://www.ctabustracker.com/bustime/api/v2/gettime?key=', params={'key':apikey_bus})
# x=requests.get('http://www.ctabustracker.com/bustime/api/v2/getpredictions?key=', params={'key':apikey_bus, 'stpid':'5676'})
# x=requests.get('http://www.ctabustracker.com/bustime/api/v2/getpredictions?key=', params={'key':apikey_bus, 'stpid':'5670'})


# print (x.text)

# predictions_dict=xmltodict.parse(x.text)
# print(predictions_dict)

#add a dummy entry to force a list, otherwise if there is only one arrival prediction things break
# print(predictions_dict['bustime-response']['prd'])

def updatePredictions():
    client.publish("CTApredictions/BUS/5670/80", getBusStopETAs(getBusStopPredictions('5670','80'))[0])
    # client.publish("CTApredictions/BUS/5676", getBusStopETAs(getBusStopPredictions('5676'))[0])
    client.publish("CTApredictions/BUS/5676/X9", getBusStopETAs(getBusStopPredictions('5676','X9'))[0])
    client.publish("CTApredictions/BUS/5676/80", getBusStopETAs(getBusStopPredictions('5676','80'))[0])
    # client.publish("CTApredictions/BUS/1056", getBusStopETAs(getBusStopPredictions('1056'))[0])
    client.publish("CTApredictions/BUS/1056/X9", getBusStopETAs(getBusStopPredictions('1056','X9'))[0])
    client.publish("CTApredictions/BUS/1056/151", getBusStopETAs(getBusStopPredictions('1056','151'))[0])
    client.publish("CTApredictions/BUS/1169/151", getBusStopETAs(getBusStopPredictions('1169','151'))[0])
    # client.publish("CTApredictions/BUS/14880/36", getBusStopETAs(getBusStopPredictions('14880','36'))[0])
    # client.publish("CTApredictions/BUS/5673/36", getBusStopETAs(getBusStopPredictions('5673','36'))[0])
    # client.publish("CTApredictions/BUS/5656/8", getBusStopETAs(getBusStopPredictions('5756','8'))[0])
    # client.publish("CTApredictions/BUS/17390/8", getBusStopETAs(getBusStopPredictions('17390','8'))[0])
    client.publish("CTApredictions/RAIL/300016", getRailStopETAs(getRailStopPredictions('30016'))[0])
    client.publish("CTApredictions/RAIL/300017", getRailStopETAs(getRailStopPredictions('30017'))[0])

print("starting CTA script")
print(datetime.datetime.now())







while True:
    timenow= datetime.datetime.now()
    try:
        updatePredictions()
    except Exception as e:
        print("exception")
        print(timenow)
        print(e)
#        pass
    # print("CTA MQTT values updated")
    # print(timenow)
    time.sleep(20)
