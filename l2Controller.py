from pox.core import core
from pox.lib.addresses import *
import pox.openflow.libopenflow_01 as of
import json
import binascii
import queue

log = core.getLogger()

def find_all_paths(graph, start, end, path=[]):
    path = path + [start]
    if start == end:
        return [path]
    if start not in graph:
        return []
    paths = []
    for node in graph[start]:
        if node not in path:
            newpaths = find_all_paths(graph, node, end, path)
            for newpath in newpaths:
                paths.append(newpath)
    return paths

class LearningSwitch (object):
    def __init__ (self, connection):
        
        self.connection = connection
        # create mapping dict
        self.mac_to_port = {}
        self.learnPaths('topo.mn')
        connection.addListeners(self)

    def learnPaths(self, topology):
        with open(topology) as fp:
            topology = json.load(fp)

        metricWeights = {
            'delay': 0.25,
            'cost' : 0.2,
            'bw': 0.2,
            'processing': 0.35
        }
        
        # Map of MAC to node name
        self.nodeMACMap = {}
        # Map of ip to node name
        self.nodeIPMap = {}
        # attributes of nodes
        self.nodeAttribs = {}
        # Node graph
        self.nodeGraph = {}
        # Link attributes
        self.linkAttribs = {}
        # Map of current best paths from hosts to the cloud app
        self.bestPaths = {}
        # Mapping of host port to connected hosts
        self.destHostMap = {}
        # Map of DPID to node
        self.nodeID = {}

        for node in topology['hosts']:
            self.nodeMACMap[node['opts']['hostname']] = node['opts']['attributes']['mac']
            if 'dpid' in node['opts']:
                self.nodeID[str(node['opts']['dpid'])] = node['opts']['hostname']      
            self.nodeAttribs[node['opts']['hostname']] = node['opts']
            if 'ip' in node['opts']:
                self.nodeIPMap[node['opts']['ip']] = node['opts']['hostname']

        for node in topology['switches']:
            self.nodeMACMap[node['opts']['hostname']] = node['opts']['attributes']['mac']
            if 'dpid' in node['opts']:
                self.nodeID[str(node['opts']['dpid'])] = node['opts']['hostname']            
        
        for link in topology['links']:
            if link['src'] not in self.nodeGraph:
                self.nodeGraph[link['src']] = []
                self.destHostMap[link['src']] = {}
            if link['dest'] not in self.nodeGraph:
                self.nodeGraph[link['dest']] = []
                self.destHostMap[link['dest']] = {}
            # print(link)
            if 'port1' in link['opts']:
                self.destHostMap[link['src']][link['dest']] = link['opts']['port1']
                self.destHostMap[link['dest']][link['src']] = link['opts']['port2']

            self.nodeGraph[link['src']].append(link['dest'])
            self.nodeGraph[link['dest']].append(link['src'])
            self.linkAttribs["".join([link['src'], link['dest']])] = link['opts']
            self.linkAttribs["".join([link['dest'], link['src']])] = link['opts']
        
        # print(self.nodeID, self.nodeMACMap, self.bestPaths)
        
        # TODO, make a new marker for the 'hidden' node behind the datacenters, using h2 for now

        for node in self.nodeAttribs:
            if node.startswith('h') and node != 'h2':
                paths = find_all_paths(self.nodeGraph, node, 'h2')
                # print(paths)
                calc = {}
                for path in paths:
                    overallWeight = 0
                    minbandwidth = 999999999999999999999999999
                    totalDelay = 0
                    totalCost = 0
                    for i in range(1, len(path)):
                        for elem in metricWeights:
                            link = "".join([path[i-1], path[i]])
                            if elem in self.linkAttribs[link]:
                                if elem == 'delay':
                                    totalDelay += float(self.linkAttribs[link][elem][:-2])
                                elif elem == 'cost':
                                    totalCost += int(self.linkAttribs[link][elem])
                                elif elem == 'bw':
                                    if int(self.linkAttribs[link][elem]) < minbandwidth:
                                        minbandwidth = int(self.linkAttribs[link][elem])
                                
                    if minbandwidth != 999999999999999999999999999:
                        print("Min bandwidth: " + str(minbandwidth))
                        overallWeight += metricWeights['bw'] * (1 / minbandwidth)
                    if totalDelay != 0:
                        print("Delay: " + str(totalDelay))
                        overallWeight += metricWeights[elem] * totalDelay
                    if totalCost != 0:
                        print("Cost: " + str(totalCost))
                        overallWeight += metricWeights[elem] * totalCost
                    print("Processing cost: " + str(len(path)))
                    overallWeight += metricWeights['processing'] * len(path)
                    print("Total cost: " + str(overallWeight))
                    print(str(path) + "\n\n")

                    calc[overallWeight] = path
                # print(calc)
                minWeight = min(list(calc.keys()))
                # print(node, self.nodeMACMap)
                if self.nodeMACMap[node] not in self.bestPaths:
                    self.bestPaths[self.nodeMACMap[node]] = {}
                if self.nodeMACMap[calc[minWeight][-1]] not in self.bestPaths:
                    self.bestPaths[self.nodeMACMap[calc[minWeight][-1]]] = {}    
                self.bestPaths[self.nodeMACMap[node]][self.nodeMACMap[calc[minWeight][-1]]] = calc[minWeight]
                self.bestPaths[self.nodeMACMap[calc[minWeight][-1]]][self.nodeMACMap[node]] = calc[minWeight][::-1]
                print("Best Path: " + str(self.bestPaths) + "\n\n\n\n")
        
        # print(self.bestPaths, self.nodemap, self.nodeAttribs)
        
    def _handle_PacketIn (self, event):
        packet = event.parsed
        dpid = str(hex(int(event.connection.dpid))[2:])
        curNode = self.nodeID[dpid]
        source = str(packet.src)
        dest = str(packet.dst)


        if dest == 'ff:ff:ff:ff:ff:ff':
            # packet.dst = EthAddr(self.nodeMACMap['h2'])
            # dest = str(packet.dst)
            if source != self.nodeMACMap['h2']:
                dest = self.nodeMACMap['h2']
            else:
                dest = self.nodeMACMap['h1']
        
        
        # print(packet.dst)

        if source in self.bestPaths and dest in self.bestPaths[source] and curNode in self.bestPaths[source][dest]:
            
            path = self.bestPaths[source][dest]
            # print(path)
            nextNode = path[path.index(curNode) + 1]

            # print(self.destHostMap)

            out_port = self.destHostMap[curNode][nextNode]

            print("On " + curNode + " Sending to " + nextNode + " Over Port " + str(out_port) + ", Full Path: " + str(path))
            
            # create the send packet action
            action = of.ofp_action_output(port=out_port)
            

            # Send the action to the switch
            # Create event message
            msg = of.ofp_packet_out()
            msg.data = event.ofp
            msg.actions.append(action)
            self.connection.send(msg)
            
            

                

        # print(packet.src, packet.dst)

        # print(event.connection.description, event.connection.ID)

        # print(packet, packet.payload.srcip, packet.payload.dstip)

        # TODO (figure out how to know where to send packet, now know where I am and where it came from, not sure which port to send) use the event port and src/dest info to know direction to send 

        # update mac to port mapping
        # elif dest == 'ff:ff:ff:ff:ff:ff':

        #     print("On " + curNode, packet.src, packet.dst)
        #     self.mac_to_port[packet.src] = event.port

        #     # If dest known, send packet to the mapped port
        #     # if packet.dst in self.mac_to_port:
        #     #     out_port = self.mac_to_port[packet.dst]
            
        #     # # Otherwise, flood the switch
        #     # else:
        #     out_port = of.OFPP_FLOOD

        #     # create the send packet action
        #     action = of.ofp_action_output(port=out_port)
            

        #     # Send the action to the switch
        #     # Create event message
        #     msg = of.ofp_packet_out()
        #     msg.data = event.ofp
        #     msg.actions.append(action)
        #     self.connection.send(msg)
        
        # print(out_port)
        
        

        

def launch ():
    # Setup the connections to the controller
    def start_switch (event):
        log.info("Controlling %s" % (event.connection,))
        LearningSwitch(event.connection)
    
    # Add mapping to start_switch function on new connection
    core.openflow.addListenerByName("ConnectionUp", start_switch)