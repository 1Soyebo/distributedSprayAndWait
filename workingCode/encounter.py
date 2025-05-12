#!/usr/bin/python

# Set target (waypoint) positions for UAVs

import sys
import struct
import socket
import math
import time
import argparse
import glob
import subprocess
import threading
import datetime

from core.api.grpc import client
from core.api.grpc import core_pb2
import xmlrpc.client

uavs = []
mynodeseq = 0
nodecnt = 0
protocol = 'none'
port = 9100
ttl = 64
core = None
session_id = None 

filepath = '/tmp'
nodepath = ''

# Predefined waypoint paths per node
pseudorandom_paths = {
    1: [(600, 200), (1000, 200),
        (1200, 400), (1000, 700), (600, 700),
        (200, 700), (350, 500),
        (800, 600),  # Late encounter with Node 4
        (600, 400), (200, 200)],
    
    2: [(1000, 200),
        (600, 200), (400, 400), (600, 600),
        (1000, 600), (1350, 600), (1200, 400),
        (1000, 200), (1350, 200)],
    
    3: [(600, 800), (1000, 800),
        (1200, 600), (1000, 400), (600, 400),
        (200, 400), (350, 600), (600, 700), (200, 800)],
    
    4: [(1000, 800), (600, 800), (400, 600),
        (600, 400), (1000, 400), (1350, 400),
        (1200, 600), 
        (800, 600),  # Late encounter with Node 1
        (1000, 800), (1350, 800)],
}


# Index tracking per node
waypoint_indices = {1: 0, 2: 0, 3: 0, 4: 0}

thrdlock = threading.Lock()
# xmlproxy = xmlrpc.client.ServerProxy("http://localhost:8000", allow_none=True)

#---------------
# Define a CORE node
#---------------
class CORENode():
  def __init__(self, nodeid, bufferCount, packetDestionationID):
    self.nodeid = nodeid
    self.bufferCount = bufferCount
    self.packetDestionationID = packetDestionationID

  def __repr__(self):
    return str(self.nodeid)
    
    
#---------------
# Thread that receives UDP Advertisements
#---------------
class ReceiveUDPThread(threading.Thread):    
  def __init__(self):
    threading.Thread.__init__(self)
    
  def run(self):
    ReceiveUDP()
      

#---------------
# Calculate the distance between two modes (on a map)
#---------------
def Distance(node1, node2):
  return math.sqrt(math.pow(node2.y-node1.y, 2) + math.pow(node2.x-node1.x, 2))

#---------------
# Redeploy a UAV back to its original position
#---------------
def RedeployUAV(uavnode):
  print("Redeploy UAV")
  position = xmlproxy.getOriginalWypt()
  xmlproxy.setWypt(position[0], position[1])

#---------------
# Record target tracked to the proxy 
# Update UAV color depending if it is tracking a target
#---------------
def RecordBufferCount(uavnode):
  print("My new buffer count is " + str(uavnode.bufferCount))
  xmlproxy.setBufferCount(uavnode.bufferCount)


#---------------
# Advertise the target being tracked over UDP
#---------------
def AdvertiseUDP(uavnodeid, bufferCount, destinationID):
  print("AdvertiseUDP (broadcast)")
  sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sk.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  ttl_bin = struct.pack('@i', ttl)
  buf = f"{uavnodeid} {bufferCount} {destinationID}"
  sk.sendto(buf.encode(encoding='utf-8',errors='strict'), ('255.255.255.255', port))

#---------------
# Receive and parse UDP advertisments
#---------------
def ReceiveUDP():
  #print("Receive UDP")
  sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

  # Bind
  sk.bind(('', port))

  while 1:
    buf, sender = sk.recvfrom(1500)
    buf_str = buf.decode('utf-8')
    uavidstr, bfCount, globalDest = buf_str.split(" ")
    print("I receieved " + buf_str)        
    uavnodeid, bufferCount, globalDestination = int(uavidstr), int(bfCount), int(globalDest)
    HandleReceivedAdvertisement(uavnodeid, bufferCount, globalDestination)
    # # Update tracking info for other UAVs
    # uavnode = uavs[mynodeseq]
    # if uavnode.nodeid != uavnodeid:
    #   UpdateTracking(uavnodeid, trgtnodeid)

def HandleReceivedAdvertisement(thierUavNodeId, theirBufferCount, globalDestinationID):
  myuavnode = uavs[mynodeseq]
  if thierUavNodeId == myuavnode.nodeid:
        return  # Ignore own advertisement
  
  if globalDestinationID > 0 and myuavnode.packetDestionationID != globalDestinationID:
      myuavnode.packetDestionationID = globalDestinationID
    
  # Check if we have messages to spray and are not the destination
  if myuavnode.bufferCount > 1 and theirBufferCount == 0:
      myuavnode.bufferCount = int(myuavnode.bufferCount/2)
      print("I am decrementing my buffer to " + str(myuavnode.bufferCount))
      RecordBufferCount(myuavnode)
  elif myuavnode.bufferCount == 1 and thierUavNodeId == myuavnode.packetDestionationID and theirBufferCount == 0 :
    # Wait phase: only forward if this is the destination
      print("Packet delivered")
  elif myuavnode.bufferCount == 0 and theirBufferCount > 1:
      myuavnode.bufferCount = int(theirBufferCount/2)
      print("I am incrementing my buffer to " + str(myuavnode.bufferCount))
      RecordBufferCount(myuavnode)
  elif globalDestinationID == myuavnode.nodeid and theirBufferCount > 0 and myuavnode.bufferCount == 0:
      myuavnode.bufferCount = 1
      RecordBufferCount(myuavnode)

      
  
#---------------
# Update tracking info based on a received advertisement
#---------------
def UpdateTracking(uavnodeid, trgtnodeid):

  if protocol == "udp":
    thrdlock.acquire()
    
  # Update corresponding UAV node structure with tracking info
  # if UAV node is in the UAV list
  in_uavs = False
  for uavnode in uavs:
    if uavnode.nodeid == uavnodeid:
      in_uavs = True

  # Otherwise add UAV node to UAV list
  if not in_uavs:
    node = CORENode(uavnodeid, trgtnodeid)
    uavs[1] = node   
      
  if protocol == "udp":
    thrdlock.release()


def SprayAndWaitAdvert():
  uavnode = uavs[mynodeseq]
  destination = uavnode.packetDestionationID if uavnode.packetDestionationID is not None else -1
  AdvertiseUDP(uavnode.nodeid, uavnode.bufferCount, destination)

  
def update_uav_waypoint(uav_id):
    path = pseudorandom_paths[uav_id]
    idx = waypoint_indices[uav_id]
    current_wp = path[idx % len(path)]

    pos = xmlproxy.getPosition()
    xuav, yuav = pos[0], pos[1]

    def distance(x1, y1, x2, y2):
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    if distance(xuav, yuav, *current_wp) < 10:
        waypoint_indices[uav_id] += 1
        next_wp = path[waypoint_indices[uav_id] % len(path)]
        print(f"Node {uav_id}: reached {current_wp}, setting next waypoint {next_wp}")
        xmlproxy.setWypt(*next_wp)
    else:
        print(f"Node {uav_id}: distance to {current_wp} is {distance(xuav, yuav, *current_wp):.2f}, not updating")


  

#---------------
# main
#---------------
def main():
  global uavs
  global protocol
  global nodepath
  global mynodeseq
  global nodecnt
  global core
  global session_id

  # Get command line inputs 
  parser = argparse.ArgumentParser()
  parser.add_argument('-my','--my-id', dest = 'uav_id', metavar='my id',
                      type=int, default = '1', help='My Node ID')
  parser.add_argument('-c','--covered-zone', dest = 'covered_zone', metavar='covered zone',
                       type=int, default = '1200', help='UAV covered zone limit on X axis')
  parser.add_argument('-r','--track_range', dest = 'track_range', metavar='track range',
                       type=int, default = '600', help='UAV tracking range')
  parser.add_argument('-i','--update_interval', dest = 'interval', metavar='update interval',
                      type=int, default = '1', help='Update Inteval')
  parser.add_argument('-p','--protocol', dest = 'protocol', metavar='comms protocol',
                      type=str, default = 'none', help='Comms Protocol')

  
  # Parse command line options
  args = parser.parse_args()

  protocol = args.protocol
  global xmlproxy
  xmlproxy = xmlrpc.client.ServerProxy(f"http://localhost:{8000 + args.uav_id}", allow_none=True)


  # Create grpc client
  core = client.CoreGrpcClient("172.16.0.254:50051")
  core.connect()
  response = core.get_sessions()
  if not response.sessions:
    raise ValueError("no current core sessions")
  session_summary = response.sessions[0]
  session_id = int(session_summary.id)
  session = core.get_session(session_id).session

  haspacket = xmlproxy.hasPacket()
  packetDestination = xmlproxy.getPacketDestination() if haspacket else None

  # Populate the uavs list with current UAV node information
  mynodeseq = 0
  node = CORENode(args.uav_id, xmlproxy.getBufferCount(), packetDestination)
  uavs.append(node)
  RedeployUAV(node)
  # RecordTarget(node)
  nodecnt += 1
  
  if mynodeseq == -1:
    print("Error: my id needs to be in the list of UAV IDs")
    sys.exit()
    
  # Initialize values
  corepath = "/tmp/pycore.*/"
  nodepath = glob.glob(corepath)[0]
  msecinterval = float(args.interval)
  secinterval = msecinterval/1000

  if protocol == "udp":
    # Create UDP receiving thread
    recvthrd = ReceiveUDPThread()
    recvthrd.start()
        
  # Start tracking targets
  while 1:
    time.sleep(secinterval)
    update_uav_waypoint(args.uav_id)

    if haspacket:
      print("this node has the packet " + args.uav_id )
      print("the destination of this packet is " + xmlproxy.getPacketDestination())

    # if protocol == "udp":    
    #   thrdlock.acquire()
    
    # #TrackTargets(args.covered_zone, args.track_range)

    # if protocol == "udp":
    #   thrdlock.release()



if __name__ == '__main__':
  main()
