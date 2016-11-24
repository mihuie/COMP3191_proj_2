#!/usr/bin/python
# -*- coding: utf-8 -*-

import sim.api as api
import sim.basics as basics

# We define infinity as a cost of 16.
INFINITY = 16
# DEFAULT_TIMER_INTERVAL = 3

class DVRouter(basics.DVRouterBase):

    # NO_LOG = flood=True # Set to flood=True on an instance to disable its logging
    POISON_MODE = True  # Can override POISON_MODE here
    # DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

    def __init__(self):
        """
        Called when the instance is initialized.

        You probably want to do some additional initialization here.
        """
        self.start_timer()

        self.routing_tb = {}
        self.d_vectors = {}  
        self.known_hosts = {}
        self.Known_links = {}

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this Entity goes up.

        The port attached to the link and the link latency are passed in.
        """

        self.Known_links[port] = latency
        self.d_vectors[port] = {}
        for (host, cost) in self.routing_tb.items():
            self.send(basics.RoutePacket(host, cost[0]), port, flood=False)

    def handle_link_down(self, port):
        """#
        Called by the framework when a link attached to this Entity does down.

        The port number used by the link is passed in.
        """

        del self.Known_links[port]
        del self.d_vectors[port]
        for host in self.known_hosts.keys():
            if self.known_hosts[host] == port:
                del self.known_hosts[host]

        for host in self.routing_tb.keys():
            if self.routing_tb[host][1] == port:
                new_cost = INFINITY
                new_port = port
                self.calc_send(new_cost, new_port, host)

    def handle_rx(self, packet, port):
        """
        Called by the framework when this Entity receives a packet.

        packet is a Packet (or subclass).
        port is the port number it arrived on.

        You definitely want to fill this in.
        """

        if isinstance(packet, basics.RoutePacket):
            self.handle_RoutePacket(packet, port)
        elif isinstance(packet, basics.HostDiscoveryPacket):
            self.handle_HostDiscoveryPacket(packet, port)
        else:
            self.handle_DataPacket(packet, port)

    def handle_RoutePacket(self, packet, port):
        host = packet.destination
        self.d_vectors[port][host] = packet.latency
        cost = min(self.Known_links[port] + packet.latency, INFINITY)

        if host in self.routing_tb.keys():
            if self.routing_tb[host][1] == port:
                current_best = self.Known_links[port] + packet.latency
                current_port = port
                self.calc_send(current_best, current_port, host)

        elif host not in self.routing_tb or cost < self.routing_tb[host][0]:

            self.routing_tb[host] = [cost, port, api.current_time()]
            if cost == INFINITY:
                if self.POISON_MODE:
                    self.send(basics.RoutePacket(host, cost), flood=True)
            else:
                self.send(basics.RoutePacket(host, cost), port, flood=True)        

    def handle_HostDiscoveryPacket(self, packet, port):
        self.routing_tb[packet.src] = [self.Known_links[port], port, 
                api.current_time()]
        self.known_hosts[packet.src] = port
        self.send(basics.RoutePacket(packet.src,
                  self.routing_tb[packet.src][0]), port, flood=True)

    def handle_DataPacket(self, packet, port):
        if packet.dst in self.routing_tb.keys():
            if self.routing_tb[packet.dst][0] < INFINITY \
                and self.routing_tb[packet.dst][1] != port:
                self.send(packet,
                          self.routing_tb[packet.dst][1], flood=False)

    def handle_timer(self):
        """
        Called periodically.

        When called, your router should send tables to neighbours.  It also might
        not be a bad place to check for whether any entries have expired.
        """

        time = api.current_time()

        for host in self.routing_tb.keys():
            if host not in self.known_hosts:
                time = time - self.routing_tb[host][2]
                temp_cost = self.routing_tb[host][0]
                temp_port = self.routing_tb[host][1]

                if time >= 15 or temp_cost >= INFINITY:

                    if temp_port in self.d_vectors:
                        del self.d_vectors[temp_port][host]

                    cost = INFINITY
                    port = self.routing_tb[host][1]

                    cost, port, time = self.b_ford(cost, port, host)
                    self.routing_tb[host] = [cost, port, time]

                    if cost == INFINITY:
                        del self.routing_tb[host]
                        if self.POISON_MODE:
                            self.send(basics.RoutePacket(host, INFINITY), flood=True)
                    else:
                        self.send(basics.RoutePacket(host, cost), port, flood=True)

        for (host, values) in self.routing_tb.items():
            cost = values[0]
            port = values[1]
            if cost == INFINITY:
                if self.POISON_MODE:
                    self.send(basics.RoutePacket(host, cost), flood=True)
            else:
                self.send(basics.RoutePacket(host, cost), port, flood=True)

    def b_ford(self, cost, port, host):
        # bell ford
        for neighbour in self.d_vectors.keys():
            if host in self.d_vectors[neighbour]:
                if self.Known_links[neighbour] + self.d_vectors[neighbour][host] < cost:
                    cost = self.Known_links[neighbour] + self.d_vectors[neighbour][host]
                    port = neighbour
        return cost, port, api.current_time()
        
    def calc_send(self, cost, port, host):
        
        self.routing_tb[host] = self.b_ford(cost, port, host)

        if cost == INFINITY:
            if self.POISON_MODE:
                self.routing_tb[host] = [INFINITY, port, api.current_time()]
                self.send(basics.RoutePacket(host, cost), port, flood=True)
            elif host in self.routing_tb:
                del self.routing_tb[host]
        else:
            self.routing_tb[host] = [cost, port, api.current_time()]
            self.send(basics.RoutePacket(host, cost), port, flood=True)



            