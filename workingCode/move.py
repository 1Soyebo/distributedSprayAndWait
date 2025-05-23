#!/usr/bin/python

# Advance a vehicle towards a target and then move in a circle
# pattern around it

import sys
import math
import time
import subprocess
import random
import datetime
import time


import threading

from core.api.grpc import client
from core.api.grpc import core_pb2

from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
from datetime import datetime, timedelta

import sys

filepath = "/tmp/"

targets = dict()
iconpath = "/data/uas-core/icons/sw/"

heading = random.uniform(0, 2 * math.pi)

class DTNPacket():
  def __init__(self, core, source_id, destination_id, session_ID):
      self.core = core
      self.sourceID = source_id
      self.destionationID = destination_id
      self.timeToLive = datetime.now() + timedelta(seconds=5)
      self.sessionID = session_ID

  def getDestination(self):
    return self.destionationID
    

#---------------
# Change icon of node based on the color
#---------------
def SetColor(core, session_id, node_id, color, nodetype):
  if nodetype == "uav":
    iconname = color + '_plane.png'
  if nodetype == "target":
    iconname = color + '_dot.png'
  iconfile = iconpath + iconname
  response = core.edit_node(session_id=session_id, node_id=node_id, icon=iconfile)  
  response = core.get_node(session_id, node_id)  
  print("SetColor for Node %d: %s" % (response.node.id, response.node.icon))


#---------------
# Calculate the distance between two points (on a map)
#---------------
def Distance(x1, y1, x2, y2):
  return math.sqrt(math.pow(y2-y1, 2) + math.pow(x2-x1, 2))


#---------------
# Define a CORE UAV node
#---------------
class CoreUav():
  def __init__(self, core, session_id, node_id, x, y, wypt_x, wypt_y, k):
      self.session_id = session_id
      self.node_id = node_id
      self.bufferCount = k
      self.position = (x,y)
      self.orig_wypt = (wypt_x,wypt_y)
      self.track_wypt = (wypt_x,wypt_y)
      self.packet = None

  def getPosition(self):
    return self.position
    
  def setPosition(self, x, y):
    self.position = (x, y)
    return True

  def getBufferCount(self):
    return self.bufferCount
    
  def setBufferCount(self, count):
    self.bufferCount = count
    return True
  
  def getPacket(self):
    return self.packet
    
  def setPacket(self, packetToSave):
    self.packet = packetToSave
    return True
  
  def hasPacket(self):
    return self.packet != None
  
  def getPacketDestination(self):
    destinationID = self.packet.getDestination()
    
  def getWypt(self):
    return self.track_wypt

  def setWypt(self, x, y):
    self.track_wypt = (x,y)
    return True

  def getOriginalWypt(self):
    return self.orig_wypt

  def setOriginalWypt(self, x, y):
    self.orig_wypt = (x,y)
    return True

#---------------
# Find the new position as a vehicle moves towards a waypoint
#---------------
def MoveToWaypoint(xold, yold, xwypt, ywypt, speed, duration):
  movedist = speed * duration
  totaldist = Distance(xold, yold, xwypt, ywypt)

  if totaldist == 0:
    return xold, yold  # Already at target, no move needed

  ratio = movedist / totaldist
  xnew = xold + (xwypt - xold) * ratio
  ynew = yold + (ywypt - yold) * ratio

  return xnew, ynew

#---------------
# Move a node clock-wise around a circle
#---------------
def MoveOnCircle(xnode, ynode, xcenter, ycenter, radius, distance):
  posangle = math.atan2(ynode-ycenter, xnode-xcenter)
  moveangle = -distance/radius # That's negative for counter-clockwise,
                               # but in CORE Y coordinates are reversed...
  xnew = xcenter + radius*math.cos(posangle-moveangle)
  ynew = ycenter + radius*math.sin(posangle-moveangle)
    
  return xnew, ynew
  

#---------------
# Move the vehicle towards the target if it's far away,
# or on a circle around the target if it's close enough
#---------------
def MoveVehicle(xold, yold, xtrgt, ytrgt, rad, speed, duration):
  # Check whether the vehicle is outside the circle around the target  
  trgtdist = Distance(xold, yold, xtrgt, ytrgt)
  movedist = speed * duration
  if trgtdist >= rad:
   # Check if the vehicle would still be outside the circle after moving
    if trgtdist - movedist >= rad:
      xnew, ynew = MoveToWaypoint(xold, yold, xtrgt, ytrgt, speed, duration)
      return xnew, ynew
    else:
      # Moving to the circle and then moving on the circle for the rest of
      # the distance
      if trgtdist == 0:      # Special case: vehicle is collocated with 
        return xold, yold    # the target and radius is zero
      
      tocircledist = trgtdist - rad
      circledist = movedist - tocircledist
      ratio = tocircledist/trgtdist
      xcircle = xold + (xtrgt-xold)*ratio
      ycircle = yold + (ytrgt-yold)*ratio

      xnew, ynew = MoveOnCircle(xcircle, ycircle, xtrgt, ytrgt, rad, circledist)
      return xnew, ynew
  else:
    # Vehicle is inside the circle; needs to move away from the target to
    # join the circle

    # Find the waypoint on the circle in straight move
    tocircledist = rad - trgtdist
    if trgtdist == 0:   #Special case: vehicle is collocated with target
      xcircle = xtrgt+rad
      ycircle = ytrgt
    else:
      ratio = rad/trgtdist
      xcircle = xtrgt + (xold-xtrgt)*ratio
      ycircle = ytrgt + (yold-ytrgt)*ratio

    # Check if the vehicle would still be outside the circle after moving 
    if movedist + trgtdist <= rad:
      # Moving in a straight line inside the circle
      xnew, ynew = MoveToWaypoint(xold, yold, xcircle, ycircle, speed, duration)
      return xnew, ynew
    else:
      # Moving straight to the circle until hitting the circle waypoint and then
      # moving on the circle from there for the rest of the distance 
      circledist = movedist - tocircledist
      xnew, ynew = MoveOnCircle(xcircle, ycircle, xtrgt, ytrgt, rad, circledist)
      return xnew, ynew


#---------------
# Initialize XML RPC Server for CORE scenario
#---------------
class StartXmlRpcServerThread(threading.Thread):
  def __init__(self, core_uav):
    threading.Thread.__init__(self)
    self.uav = core_uav

  def run(self):
    StartXmlRpcServer(self.uav)

def StartXmlRpcServer(core_uav):
  while 1: 
    # with SimpleXMLRPCServer(("localhost", 8000)) as server:
    with SimpleXMLRPCServer(("localhost", 8000 + core_uav.node_id)) as server:
      server.register_instance(core_uav, allow_dotted_names=True)
      server.register_multicall_functions()
      print('Serving XML-RPC on localhost port 8000')
      try:
          server.serve_forever()
      except:
          print("\nKeyboard interrupt received, exiting.")
          sys.exit(0)


#---------------
# main
#---------------
def main():
  global targets

  # Original waypoints
  original_wypts = {1: (600, 200), 2: (1000, 200), 3: (600, 800), 4: (1000, 800)} 
                    

  # Targets colors
  colors = ['blue', 'yellow', 'green', 'red', 'lime', 'orange', 'pink', 'purple', 'lavender', 'cyan']
  

  # Get command line inputs 
  if len(sys.argv) >= 7:
    node_id  = int(sys.argv[1])
    xuav  = int(sys.argv[2])
    yuav  = int(sys.argv[3])
    rad   = int(sys.argv[4])
    speed = float(sys.argv[5])
    msecduration  = float(sys.argv[6])	
    bufferCount = int(sys.argv[7])
    hasPacket = sys.argv[8].lower() == "true"
    duration = msecduration/1000
  else:
    print("move_node.py nodenum xuav yuav radius speed duration(msec)\n")
    sys.exit()

  # Create grpc client
  core = client.CoreGrpcClient("172.16.0.254:50051")
  core.connect()
  response = core.get_sessions()
  if not response.sessions:
    raise ValueError("no current core sessions")
  session_summary = response.sessions[0]
  session_id = int(session_summary.id)
  session = core.get_session(session_id).session

  # Set CORE UAV
  node_wypt = original_wypts[node_id]
  core_uav = CoreUav(core, session_id, node_id, xuav, yuav, node_wypt[0], node_wypt[1], bufferCount)

  if hasPacket:
    dtn_packet = DTNPacket(core=core, source_id=1, destination_id= 4, session_ID=session_id)
    core_uav.setPacket(dtn_packet)
    print()

  # Initialize targets
  SetColor(core, session_id, node_id, 'grey', "uav")


  print("Start XML RPC thread")

  # Initiate xmlrpc server
  xml_rpc_server_thread = StartXmlRpcServerThread(core_uav)
  xml_rpc_server_thread.start()

  print("Start MOVE UAV thread")

  # Move UAV node
  while 1:
    time.sleep(duration)
    position = core_uav.getWypt()
    xtrgt, ytrgt = position[0], position[1] 
    xuav, yuav = MoveToWaypoint(xuav, yuav, xtrgt, ytrgt, speed, duration)
    #print("xuav: %d, yuav: %d" % (xuav, yuav))


    color = "black"
    icon_file_path = iconpath + color + "_phone.png"

    # Set position and keep current UAV color
    pos = core_pb2.Position(x = xuav, y = yuav)
    response = core.edit_node(session_id=session_id, node_id=node_id, position=pos, icon=icon_file_path)
    core_uav.setPosition(xuav, yuav)


      
if __name__ == '__main__':
  main()